import re
import threading
from collections import OrderedDict

try:
    from rank_bm25 import BM25Okapi
except ImportError:  # pragma: no cover - optional dependency fallback
    BM25Okapi = None  # type: ignore[assignment]

from app.core.singleton import Cell
from app.retrievers.stores.corpus import corpus_snapshot, reset_corpus_snapshot

# English tokenization pattern (original)
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_\-]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    """
    Basic tokenization for English and Chinese text.

    English: splits on whitespace and punctuation
    Chinese: treats each character as a token (suboptimal for BM25)
    """
    return TOKEN_PATTERN.findall((text or "").lower())


def tokenize_chinese_aware(text: str) -> list[str]:
    """
    Chinese-aware tokenization using jieba for better BM25 performance.

    Falls back to basic tokenization if jieba is not available.

    Args:
        text: Input text (Chinese or English)

    Returns:
        List of tokens

    Examples:
        >>> tokenize_chinese_aware("\u673a\u5668\u5b66\u4e60\u7b97\u6cd5")
        ["\u673a\u5668", "\u5b66\u4e60", "\u7b97\u6cd5"]  # With jieba
        >>> tokenize_chinese_aware("machine learning")
        ["machine", "learning"]
    """
    if not text:
        return []

    text_lower = text.lower()

    # Any CJK at all takes the segmenting path. It used to require more than 20%
    # of the characters to be CJK, and below that the text was tokenized as
    # English -- every Chinese character a single token, which matches nothing an
    # index of words and bigrams holds. Measured: "Kubernetes \u7684 pod affinity
    # \u600e\u4e48\u914d\u7f6e" (19%) and "PostgreSQL connection pool \u8d85\u65f6\u600e\u4e48\u529e" (17%) produced
    # no Chinese word at all, and the verifier's retry, which appended an English
    # sentence to the question, pushed all ten Chinese evaluation questions under
    # the line and lost every one of their gold documents. A question naming a
    # product in English is how this application's users write.
    #
    # Text with no CJK is untouched, and so is text that already crossed the old
    # threshold; only mixed text below it changes.
    try:
        import jieba

        if any("\u4e00" <= c <= "\u9fff" for c in text):
            tokens = [t.strip() for t in jieba.cut_for_search(text_lower) if t.strip() and len(t.strip()) > 1]
            # Plus character bigrams over every CJK run. See _cjk_bigrams.
            return [token for token in dict.fromkeys(tokens + _cjk_bigrams(text_lower)) if token not in FUNCTION_WORDS]

    except ImportError:
        pass  # Fall back to basic tokenization

    # For English or when jieba is not available
    return [token for token in TOKEN_PATTERN.findall(text_lower) if token not in FUNCTION_WORDS]


FUNCTION_WORDS: frozenset[str] = frozenset(
    "a an the of to in on at by for from with as and or is are was were be been it its this that these those".split()
)
"""English words that carry no topic, dropped from queries and documents alike.

BM25 makes a document a candidate when it shares any term with the query, and
only then ranks. Sharing "for" was enough: measured on the evaluation corpus, an
English sentence appended to a Chinese question (the verifier's old retry
suffix) made two English compliance rows -- whose only link to the question was
"for" -- outrank the gold documents of q-13 and q-15 and push them out of the
top five. Function words match nearly every English document, so they make the
candidate set everything rather than anything. Kept short on purpose: a word
someone might search for ("no", "not", "all") is not on it.
"""


CJK_RUN = re.compile(r"[一-鿿]{2,}")


def _cjk_bigrams(text: str) -> list[str]:
    """Character bigrams over each run of CJK text.

    jieba's dictionary is the only vocabulary the tokenizer had, and dropping
    single characters (they carry almost no signal on their own) meant a word the
    dictionary does not know produced *nothing*. Two failures followed, and the
    second is the worse one:

    * A word jieba splits entirely into single characters disappears from the
      query and from the document alike, so it can never match. Measured on
      30 realistic domain terms only one behaved this way -- but it is a silent
      total failure, and which words fall in that set is unpredictable.

    * More common: jieba emits a *sub-word* and the sub-word is then used as if
      it were the word. `陪产假` (paternity leave) tokenizes to exactly `产假`
      (maternity leave) -- an identical token set, so BM25 could not tell the two
      apart at all, and a query about one ranked the other first. That is a wrong
      answer, not a missing one.

    Bigrams fix both without a dictionary: `年假` is recovered from the two
    characters jieba split it into, and `陪产` distinguishes `陪产假` from `产假`.
    They are added alongside jieba's tokens rather than replacing them, so known
    words keep their exact-match weight; BM25's IDF discounts the bigrams that
    turn out to be common.
    """

    out: list[str] = []
    for run in CJK_RUN.findall(text):
        out.extend(run[index : index + 2] for index in range(len(run) - 1))
    return out


# How many distinct access scopes keep a prebuilt index. Each entry holds only
# that scope's own records, so this is bounded by concurrent users, not corpus
# size.
SCOPED_INDEX_CACHE_SIZE = 32


def _build_index(records: list[dict], use_chinese_tokenizer: bool):
    """Tokenize records once and build the BM25 index over them.

    The per-document token sets are kept alongside the index because matching
    ("does this document contain a query term?") and ranking ("how well?") are
    separate questions -- see bm25_search. Retokenizing per query would undo the
    point of caching the index.
    """
    tokenizer_func = tokenize_chinese_aware if use_chinese_tokenizer else tokenize
    tokenized = [tokenizer_func(r.get("text", "")) for r in records]
    if not tokenized:
        return None, [], []
    token_sets = [frozenset(tokens) for tokens in tokenized]
    if BM25Okapi is None:
        return None, records, token_sets
    return BM25Okapi(tokenized), records, token_sets


_EMPTY_INDEX = (None, [], [])
# (scope, tokenizer flag) -> (digests of the scope's sources, built index).
#
# There is no global index any more (PERF-02). One used to be built over every
# tenant's corpus only to obtain the record list, which meant tokenizing the
# whole corpus with jieba -- measured at 55 s for 100k chunks -- and since
# every ingest cleared it, one user's upload made the next query of every
# other user pay that again. A scoped index is now reused for as long as the
# chunks of *its own* sources are byte-identical, which the corpus snapshot
# tells us without reading their text again.
_SCOPED_INDEXES: Cell[OrderedDict] = Cell(OrderedDict())
_SCOPED_LOCK = threading.Lock()


def _load_scoped_bm25(allowed: tuple[str, ...], use_chinese_tokenizer: bool = True):
    """The BM25 index for one access scope, rebuilt only when its sources changed."""

    snapshot = corpus_snapshot()
    digests = tuple(snapshot.source_digests.get(source, "") for source in allowed)
    key = (allowed, use_chinese_tokenizer)
    with _SCOPED_LOCK:
        cached = _SCOPED_INDEXES.value.get(key)
        if cached is not None and cached[0] == digests:
            _SCOPED_INDEXES.value.move_to_end(key)
            return cached[1]
    index = _build_scoped_index(snapshot.records, allowed, use_chinese_tokenizer)
    with _SCOPED_LOCK:
        indexes = _SCOPED_INDEXES.value
        indexes[key] = (digests, index)
        indexes.move_to_end(key)
        while len(indexes) > SCOPED_INDEX_CACHE_SIZE:
            indexes.popitem(last=False)
    return index


def _build_scoped_index(records, allowed: tuple[str, ...], use_chinese_tokenizer: bool):
    # Corpus order, not scope order: BM25 ties are broken by position, so the
    # records must stay in the order the old filter over the full list kept.
    permitted = set(allowed)
    scoped = [row for row in records if str((row.get("metadata", {}) or {}).get("source", "")) in permitted]
    if not scoped:
        return _EMPTY_INDEX
    return _build_index(scoped, use_chinese_tokenizer)


def bm25_search(
    query: str, k: int = 6, allowed_sources: list[str] | None = None, use_chinese_tokenizer: bool = True
) -> list[dict]:
    """
    Perform BM25 search with optional Chinese-aware tokenization.

    Args:
        query: Search query
        k: Number of results to return
        allowed_sources: Optional list of allowed source files
        use_chinese_tokenizer: Use jieba for Chinese text (default: True)

    Returns:
        List of ranked documents with BM25 scores
    """
    if allowed_sources is None:
        # Same contract as similarity_search: a missing scope is a caller that
        # skipped the resolver, not a licence to read every tenant's corpus.
        raise ValueError(
            "allowed_sources is required for user data isolation. "
            "Pass the caller's resolved scope; an empty list means 'no documents'."
        )
    bm25, records, token_sets = _load_scoped_bm25(tuple(sorted(allowed_sources)), use_chinese_tokenizer)
    if not records:
        return []

    # Tokenize query with the same tokenizer
    tokenizer_func = tokenize_chinese_aware if use_chinese_tokenizer else tokenize
    tokens = tokenizer_func(query)

    if not tokens:
        return []

    # Match on term overlap, rank by BM25 -- two separate questions.
    #
    # This used to keep whatever scored above zero, which is only a proxy for
    # "contains a query term" and a proxy that inverts on a small index: BM25 IDF
    # goes negative for a term present in most documents, so in a one-document
    # scope *every* term scores negative and a matching document was dropped. A
    # user whose whole corpus was one chunk got no BM25 hits at all -- and
    # per-scope indexes make small scopes the common case, not the exception.
    query_terms = set(tokens)
    matched = [index for index, terms in enumerate(token_sets) if query_terms & terms]
    if not matched:
        return []

    if bm25 is None:
        # Fallback ranking when rank_bm25 is unavailable: term overlap count.
        scores = {index: float(len(query_terms & token_sets[index])) for index in matched}
    else:
        raw = bm25.get_scores(tokens)
        scores = {index: float(raw[index]) for index in matched}

    ranked = sorted(matched, key=lambda index: scores[index], reverse=True)[:k]
    return [
        {
            "id": records[index]["id"],
            "text": records[index]["text"],
            "metadata": records[index].get("metadata", {}),
            "bm25_score": scores[index],
        }
        for index in ranked
    ]


def reset_bm25_cache() -> None:
    """The corpus changed: re-read it on the next query.

    Scoped indexes are deliberately kept. Each one is checked against its own
    sources' digests on use, so after an ingest only the scopes that can see
    the changed document are rebuilt -- clearing them all here is what made one
    user's upload cold-start every other user's index (PERF-02).
    """
    reset_corpus_snapshot()


def clear_bm25_indexes() -> None:
    """Drop every scoped index as well (tests, and memory pressure)."""
    reset_corpus_snapshot()
    with _SCOPED_LOCK:
        _SCOPED_INDEXES.value.clear()
