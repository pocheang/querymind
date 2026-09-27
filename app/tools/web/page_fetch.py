"""Read the text of a web page a search returned, for use as evidence.

A search result carries a snippet of 100-300 characters, and until this module
existed the snippet was all the web source ever handed the synthesizer -- too
little to support even one paragraph, so an answer built on it either stayed a
sentence long or was filled from the model's own knowledge. This fetches the
page itself and keeps the passages that bear on the question.

Fetching a URL named by a third party (the search engine) is a server-side
request forgery surface, so every hop is checked the same way:

- HTTPS on the default port only.
- The host must pass the caller's source filter -- the same allowlist the search
  result already passed -- so a redirect cannot leave the trusted set.
- Every address the host resolves to must be globally routable, and the
  connection is made to the address that was checked rather than to the name,
  so a second DNS answer cannot swap in an internal address (DNS rebinding).
  Behind `WEB_PROXY_URL` the proxy connects, so the name is sent to it; a name
  that resolves locally must still resolve to public addresses.
- Redirects are followed by hand, at most `_MAX_REDIRECTS`, each re-checked.
- Only `text/html` / `text/plain` bodies, and at most `_MAX_BYTES` of them.

Nothing about the user travels with the request: no cookie, no referer, and the
URL is the search engine's, not built from the question.

The page text is untrusted third-party content. It reaches the model only as
evidence, which `ContextBuilder` screens for injected instructions and the
prompt fences inside the evidence sandbox -- the same path the snippet took.
"""

from __future__ import annotations

import codecs
import ipaddress
import logging
import math
import re
import socket
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

logger = logging.getLogger(__name__)

__all__ = ["PageFetchRefused", "fetch_page_text", "relevant_passages", "html_to_text"]

_MAX_BYTES = 1_000_000
_MAX_REDIRECTS = 3
_USER_AGENT = "Mozilla/5.0 (compatible; QueryMind/0.7; +https://github.com/pocheang/querymind)"
_ACCEPTED_TYPES = ("text/html", "application/xhtml+xml", "text/plain")

_CACHE_TTL_SECONDS = 600.0
_FAILURE_TTL_SECONDS = 120.0
_CACHE_SIZE = 128
_cache: OrderedDict[str, tuple[float, str | None]] = OrderedDict()
_cache_lock = threading.Lock()


class PageFetchRefused(Exception):
    """A URL this module will not fetch. The message names the rule, never the page."""


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


def fetch_page_text(
    url: str,
    *,
    host_allowed: Callable[[str], bool],
    timeout_seconds: float,
    proxy: str | None = None,
) -> str | None:
    """The readable text of `url`, or None when it cannot or may not be read.

    `host_allowed` receives each hop's full URL and decides whether its host is
    a trusted source. Results -- including failures -- are cached per URL for a
    few minutes: one question searches several rewrites of itself at once, and
    they routinely return the same pages.
    """

    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(url)
        if cached is not None and cached[0] > now:
            _cache.move_to_end(url)
            return cached[1]

    text: str | None
    try:
        text = _fetch(url, host_allowed=host_allowed, timeout_seconds=timeout_seconds, proxy=proxy)
    except PageFetchRefused as refused:
        logger.info("Page fetch refused (%s): %s", refused, urlsplit(url).hostname)
        text = None
    except (httpx.HTTPError, OSError, UnicodeError, ValueError) as error:
        logger.info("Page fetch failed (%s): %s", type(error).__name__, urlsplit(url).hostname)
        text = None

    ttl = _CACHE_TTL_SECONDS if text else _FAILURE_TTL_SECONDS
    with _cache_lock:
        _cache[url] = (time.monotonic() + ttl, text)
        _cache.move_to_end(url)
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)
    return text


def clear_page_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _fetch(url: str, *, host_allowed: Callable[[str], bool], timeout_seconds: float, proxy: str | None) -> str | None:
    with httpx.Client(timeout=timeout_seconds, follow_redirects=False, proxy=proxy, trust_env=False) as client:
        current = url
        for _ in range(_MAX_REDIRECTS + 1):
            host = _checked_host(current, host_allowed)
            request = _pinned_request(client, current, host, _connect_address(host, proxied=proxy is not None))
            response = client.send(request, stream=True)
            try:
                if response.is_redirect:
                    location = response.headers.get("location", "")
                    if not location:
                        return None
                    current = urljoin(current, location)
                    continue
                if response.status_code != 200:
                    return None
                content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if content_type not in _ACCEPTED_TYPES:
                    return None
                body = _read_capped(response)
                text = _decode(body, response.headers.get("content-type", ""))
                return text if content_type == "text/plain" else html_to_text(text)
            finally:
                response.close()
        raise PageFetchRefused("too many redirects")


def _checked_host(url: str, host_allowed: Callable[[str], bool]) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise PageFetchRefused("not https")
    if parts.port not in (None, 443):
        raise PageFetchRefused("non-default port")
    if parts.username or parts.password:
        raise PageFetchRefused("credentials in url")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise PageFetchRefused("no host")
    if not host_allowed(url):
        raise PageFetchRefused("host not an allowed source")
    return host


def _connect_address(host: str, *, proxied: bool) -> str | None:
    """The address to connect to, having checked every address the host has.

    Returns None when a proxy will connect instead and the name did not resolve
    here -- the proxy is the operator's egress point, and a deployment that
    reaches the internet only through it often has no public DNS of its own.
    """

    try:
        literal = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        literal = None
    if literal is not None:
        if not literal.is_global:
            raise PageFetchRefused("non-public address")
        return str(literal)

    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        if proxied:
            return None
        raise
    addresses = [ipaddress.ip_address(str(info[4][0]).split("%")[0]) for info in infos]
    if not addresses or not all(address.is_global for address in addresses):
        raise PageFetchRefused("non-public address")
    return None if proxied else str(addresses[0])


def _pinned_request(client: httpx.Client, url: str, host: str, address: str | None) -> httpx.Request:
    headers = {"User-Agent": _USER_AGENT, "Accept": "text/html,text/plain;q=0.9"}
    if address is None:
        return client.build_request("GET", url, headers=headers)
    # Connect to the checked address, and keep the name for the Host header and
    # for TLS: httpcore verifies the certificate against `sni_hostname`, so the
    # pinned connection is still authenticated as the host that was allowed.
    parts = urlsplit(url)
    ip_host = f"[{address}]" if ":" in address else address
    pinned = parts._replace(netloc=ip_host).geturl()
    headers["Host"] = host
    return client.build_request("GET", pinned, headers=headers, extensions={"sni_hostname": host})


def _read_capped(response: httpx.Response) -> bytes:
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_bytes():
        chunks.append(chunk)
        size += len(chunk)
        if size >= _MAX_BYTES:
            break
    return b"".join(chunks)[:_MAX_BYTES]


_META_CHARSET = re.compile(rb"""<meta[^>]{0,200}?charset=["']?([A-Za-z0-9_\-]{1,40})""", re.IGNORECASE)


def _decode(body: bytes, content_type: str) -> str:
    """Decode with the declared charset: a header first, then a `<meta>` tag.

    A GBK page decoded as UTF-8 is not an error the replacement character makes
    visible to anyone reading the evidence later -- it is garbage the model
    will paraphrase -- so the page's own declaration is looked for first.
    """

    charset = ""
    for part in content_type.split(";")[1:]:
        key, _, value = part.partition("=")
        if key.strip().lower() == "charset":
            charset = value.strip().strip("\"'")
    if not charset:
        match = _META_CHARSET.search(body[:4096])
        if match:
            charset = match.group(1).decode("ascii")
    try:
        codec = codecs.lookup(charset).name if charset else "utf-8"
    except LookupError:
        codec = "utf-8"
    return body.decode(codec, errors="replace")


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

_WHITESPACE = re.compile(r"\s+")

# Page furniture: repeated on every page of a site and never the answer.
_SKIPPED = frozenset(
    {"script", "style", "noscript", "template", "svg", "nav", "header", "footer", "aside", "form", "button", "iframe"}
)
_BLOCKS = frozenset(
    {
        "p", "div", "li", "ul", "ol", "br", "tr", "td", "th", "table", "section", "article", "main",
        "pre", "blockquote", "dd", "dt", "h1", "h2", "h3", "h4", "h5", "h6", "hr",
    }
)  # fmt: skip


class _TextExtractor(HTMLParser):
    """Visible text, one block per line -- and one table row per line.

    A cell is not a paragraph. Breaking at every `<td>` turned a mitigation
    table into lines like "M1048" and "Application Isolation", each too short to
    be selected, so the passage picker fell back to the bibliography. Inside a
    row, cells are joined with " | " and inner blocks with a space.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._row_depth = 0
        self._parts: list[str] = []

    def _break(self, tag: str, *, opening: bool) -> None:
        if tag == "tr" or not self._row_depth:
            self._parts.append("\n")
        else:
            self._parts.append(" | " if opening and tag in ("td", "th") else " ")

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001 -- HTMLParser's signature
        if tag in _SKIPPED:
            self._skip_depth += 1
        elif tag in _BLOCKS:
            self._break(tag, opening=True)
            if tag == "tr":
                self._row_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCKS:
            if tag == "tr":
                self._row_depth = max(0, self._row_depth - 1)
            self._break(tag, opening=False)

    def handle_data(self, data: str) -> None:
        # A newline in the markup is layout, not text: the tags decide where a
        # line ends. Kept as-is, the indentation between two cells broke a row.
        if not self._skip_depth:
            self._parts.append(_WHITESPACE.sub(" ", data))

    def text(self) -> str:
        lines = (" ".join(line.split()).strip(" |") for line in "".join(self._parts).split("\n"))
        return "\n".join(line for line in lines if line)


def html_to_text(html: str) -> str:
    """The visible text of a page, one block per line, furniture removed."""

    extractor = _TextExtractor()
    extractor.feed(html)
    extractor.close()
    return extractor.text()


# ---------------------------------------------------------------------------
# Passage selection
# ---------------------------------------------------------------------------

_MIN_PARAGRAPH_CHARS = 40
_LATIN_TOKEN = re.compile(r"[a-z0-9][a-z0-9.+#\-]{0,40}")
_CJK_RUN = re.compile(r"[㐀-鿿]+")
_STEM_CHARS = 6
# A bibliography entry names its subject in its title, so it matches the query
# as well as the section it supports -- and a reference page has dozens of them.
# They are never the answer. Anchored on the retrieval note that ends them.
_REFERENCE_LINE = re.compile(r"(?:Retrieved|Accessed|Archived from the original on)\s[\w ,.\-]{4,30}$")
_LATIN_STOPWORDS = frozenset(
    "and are can does for from how its the this what when where which who why with you your".split()
)
_CJK_STOP_BIGRAMS = frozenset(
    {"什么", "么是", "哪些", "有哪", "怎么", "如何", "是什", "一个", "可以", "需要", "我们", "帮我"}
)


def _latin_keys(text: str) -> set[str]:
    """Latin words, cut to a short prefix so "mitigate" meets "mitigations".

    Only words made of letters are cut. An identifier is matched whole: cut to
    six characters, `CVE-2021-44228` became `cve-20` and matched every CVE on
    the page.

    A two-letter word only counts when it carries a digit (`h2`, `v8`): the
    other two-letter tokens in a technical page are fragments -- `ATT&CK`
    tokenizes to `att` and `ck` -- and match everything.
    """

    keys = set()
    for raw in _LATIN_TOKEN.findall(text):
        token = raw.strip(".-")
        if len(token) < 3 and not any(char.isdigit() for char in token):
            continue
        if token in _LATIN_STOPWORDS:
            continue
        keys.add(token[:_STEM_CHARS] if token.isalpha() else token)
    return keys


def _cjk_bigrams(text: str) -> set[str]:
    return {
        run[index : index + 2]
        for run in _CJK_RUN.findall(text)
        for index in range(len(run) - 1)
        if run[index : index + 2] not in _CJK_STOP_BIGRAMS
    }


def relevant_passages(text: str, query: str, *, max_chars: int = 1500) -> str:
    """The paragraphs of `text` that bear most on `query`, in page order.

    Lexical on purpose: this runs per page per query inside the web source's
    time budget, and its job is only to pick which part of a long page to show
    the model -- the model and the verifier decide what the passage supports.
    Returns "" when no paragraph shares a term, so the caller keeps the snippet
    rather than evidence about something else.

    Three things make plain term overlap work on real pages, each found on one:

    - A paragraph inherits the terms its section heading matched. ATT&CK's
      mitigation rows never say "mitigate"; their heading does.
    - Terms are weighted by how rare they are *on this page*. Otherwise a
      bibliography of forty "Detection of ..." titles outranks the section.
    - Repeated lines (a title, a breadcrumb) are kept once; three copies of a
      title would take the budget the answer needed.
    """

    lowered_query = query.lower()
    query_latin = _latin_keys(lowered_query)
    query_cjk = _cjk_bigrams(lowered_query)
    if not query_latin and not query_cjk:
        return ""

    paragraphs = _sectioned_paragraphs(text, query_latin, query_cjk)
    weights = _rarity_weights(paragraphs)
    scored = [
        (sum(weights[term] for term in terms), position, paragraph)
        for position, (paragraph, terms) in enumerate(paragraphs)
        if terms
    ]
    if not scored:
        return ""
    return _fill(scored, max_chars)


def _matched_terms(line: str, query_latin: set[str], query_cjk: set[str]) -> frozenset[str]:
    lowered = line.lower()
    return frozenset(query_latin & _latin_keys(lowered)) | frozenset(query_cjk & _cjk_bigrams(lowered))


def _sectioned_paragraphs(text: str, query_latin: set[str], query_cjk: set[str]) -> list[tuple[str, frozenset[str]]]:
    """Each paragraph with the query terms it matches, plus those of its heading.

    A line too short to be a paragraph is treated as a heading: it opens a
    section, and the terms it matched apply to what follows until the next one.
    """

    paragraphs: list[tuple[str, frozenset[str]]] = []
    heading_terms: frozenset[str] = frozenset()
    seen: set[str] = set()
    for line in text.split("\n"):
        terms = _matched_terms(line, query_latin, query_cjk)
        if len(line) < _MIN_PARAGRAPH_CHARS:
            heading_terms = terms
            continue
        if line in seen or _REFERENCE_LINE.search(line):
            continue
        seen.add(line)
        paragraphs.append((line, terms | heading_terms))
    return paragraphs


def _rarity_weights(paragraphs: list[tuple[str, frozenset[str]]]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for _, terms in paragraphs:
        for term in terms:
            counts[term] = counts.get(term, 0) + 1
    total = max(1, len(paragraphs))
    return {term: math.log(1.0 + total / count) for term, count in counts.items()}


def _fill(scored: list[tuple[float, int, str]], max_chars: int) -> str:
    chosen: list[tuple[int, str]] = []
    used = 0
    for _, position, paragraph in sorted(scored, key=lambda row: (-row[0], row[1])):
        remaining = max_chars - used
        # A tail shorter than a paragraph is a fragment ("Dete…"), not evidence.
        if remaining < _MIN_PARAGRAPH_CHARS:
            break
        piece = paragraph if len(paragraph) <= remaining else paragraph[:remaining].rstrip() + "…"
        chosen.append((position, piece))
        used += len(piece) + 1
    return "\n".join(piece for _, piece in sorted(chosen))
