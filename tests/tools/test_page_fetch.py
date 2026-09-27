"""Reading a web page named by a search engine: what may be fetched, and what is kept.

The search snippet (100-300 characters) was all the web source ever gave the
synthesizer, so answers built on it were either one sentence or filled from the
model's own knowledge. `app/tools/web/page_fetch.py` reads the page. The URL is
chosen by a third party, so most of this file is the refusals: a server-side
request forgery guard that is only tested on the happy path is not a guard.

No test here reaches the network. Name resolution is replaced, and HTTP goes to
an `httpx.MockTransport`.
"""

from __future__ import annotations

import functools
import socket
from urllib.parse import urlsplit

import httpx
import pytest

from app.tools.web import page_fetch
from app.tools.web.page_fetch import (
    PageFetchRefused,
    clear_page_cache,
    fetch_page_text,
    html_to_text,
    relevant_passages,
)

PUBLIC = "93.184.216.34"


def _allow_all(_url: str) -> bool:
    return True


def _only(host: str):
    """A source filter allowing exactly one host, compared as a parsed hostname.

    A substring test would let `docs.example.org.evil.com` through, which is the
    mistake the real filter must not make either.
    """

    return lambda url: urlsplit(url).hostname == host


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_page_cache()
    yield
    clear_page_cache()


@pytest.fixture
def resolve(monkeypatch: pytest.MonkeyPatch):
    """Make every name resolve to the addresses given, and record what was asked."""

    asked: list[str] = []

    def install(*addresses: str):
        def fake(host, port, *args, **kwargs):
            asked.append(host)
            family = socket.AF_INET6 if ":" in addresses[0] else socket.AF_INET
            return [(family, socket.SOCK_STREAM, 6, "", (address, port)) for address in addresses]

        monkeypatch.setattr(page_fetch.socket, "getaddrinfo", fake)
        return asked

    return install


@pytest.fixture
def serve(monkeypatch: pytest.MonkeyPatch):
    """Route every request this module makes to `handler`, and record the requests."""

    seen: list[httpx.Request] = []

    def install(handler):
        def recording(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        monkeypatch.setattr(
            page_fetch.httpx, "Client", functools.partial(httpx.Client, transport=httpx.MockTransport(recording))
        )
        return seen

    return install


def _html(body: str, **headers) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8", **headers}, text=body)


# ---------------------------------------------------------------------------
# What may be fetched
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "rule"),
    [
        ("http://example.org/a", "not https"),
        ("https://example.org:8443/a", "non-default port"),
        ("https://user:pw@example.org/a", "credentials in url"),
        ("https:///a", "no host"),
    ],
)
def test_a_url_of_the_wrong_shape_is_refused_before_anything_is_resolved(url, rule, resolve):
    asked = resolve(PUBLIC)

    with pytest.raises(PageFetchRefused, match=rule):
        page_fetch._checked_host(url, _allow_all)
    assert asked == []


def test_a_host_the_source_filter_rejects_is_refused(resolve):
    asked = resolve(PUBLIC)

    with pytest.raises(PageFetchRefused, match="not an allowed source"):
        page_fetch._checked_host("https://blog.example.com/a", _only("example.org"))
    assert asked == []


@pytest.mark.parametrize(
    "address", ["127.0.0.1", "10.0.0.5", "192.168.1.10", "169.254.169.254", "::1", "fd00::1", "100.64.0.1"]
)
def test_a_name_resolving_to_a_non_public_address_is_refused(address, resolve):
    """169.254.169.254 is the cloud metadata endpoint -- the classic SSRF prize."""

    resolve(address)

    with pytest.raises(PageFetchRefused, match="non-public address"):
        page_fetch._connect_address("intranet.example.org", proxied=False)


def test_one_private_address_among_public_ones_is_enough_to_refuse(resolve):
    """Checking only the first answer would let a name carry a second, internal one."""

    resolve(PUBLIC, "10.0.0.5")

    with pytest.raises(PageFetchRefused, match="non-public address"):
        page_fetch._connect_address("mixed.example.org", proxied=False)


@pytest.mark.parametrize("literal", ["127.0.0.1", "[::1]", "10.1.2.3"])
def test_an_address_literal_is_checked_too(literal):
    with pytest.raises(PageFetchRefused, match="non-public address"):
        page_fetch._connect_address(literal, proxied=False)


def test_a_name_that_does_not_resolve_is_an_error_without_a_proxy_and_left_to_the_proxy_with_one(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("no such name")

    monkeypatch.setattr(page_fetch.socket, "getaddrinfo", fail)

    with pytest.raises(socket.gaierror):
        page_fetch._connect_address("unresolvable.example.org", proxied=False)
    assert page_fetch._connect_address("unresolvable.example.org", proxied=True) is None


def test_behind_a_proxy_a_name_that_resolves_privately_is_still_refused(resolve):
    resolve("10.0.0.5")

    with pytest.raises(PageFetchRefused, match="non-public address"):
        page_fetch._connect_address("intranet.example.org", proxied=True)


def test_the_connection_goes_to_the_address_that_was_checked(resolve, serve):
    """Connecting by name would resolve it a second time, and the second answer
    is the one DNS rebinding controls. The name stays in the Host header and in
    TLS (`sni_hostname`), so the certificate is still checked against it."""

    resolve(PUBLIC)
    seen = serve(lambda request: _html("<p>A paragraph long enough to be kept as page text.</p>"))

    assert fetch_page_text("https://docs.example.org/page?q=1", host_allowed=_allow_all, timeout_seconds=2)

    request = seen[0]
    assert request.url.host == PUBLIC
    assert request.url.path == "/page" and request.url.query == b"q=1"
    assert request.headers["host"] == "docs.example.org"
    assert request.extensions["sni_hostname"] == "docs.example.org"


def test_nothing_about_the_user_is_sent(resolve, serve):
    resolve(PUBLIC)
    seen = serve(lambda request: _html("<p>text</p>"))

    fetch_page_text("https://docs.example.org/", host_allowed=_allow_all, timeout_seconds=2)

    headers = {name.lower() for name in seen[0].headers}
    assert not headers & {"cookie", "referer", "authorization"}


# ---------------------------------------------------------------------------
# Redirects: every hop is checked again
# ---------------------------------------------------------------------------


def _redirect(location: str) -> httpx.Response:
    return httpx.Response(302, headers={"location": location})


def test_a_redirect_to_a_host_the_filter_rejects_is_not_followed(resolve, serve):
    resolve(PUBLIC)
    seen = serve(
        lambda request: (
            _redirect("https://evil.example.com/")
            if request.headers["host"] == "docs.example.org"
            else _html("<p>should never be read</p>")
        )
    )

    text = fetch_page_text("https://docs.example.org/", host_allowed=_only("docs.example.org"), timeout_seconds=2)

    assert text is None
    assert [request.headers["host"] for request in seen] == ["docs.example.org"]


def test_a_redirect_to_plain_http_is_not_followed(resolve, serve):
    resolve(PUBLIC)
    seen = serve(lambda request: _redirect("http://docs.example.org/insecure"))

    assert fetch_page_text("https://docs.example.org/", host_allowed=_allow_all, timeout_seconds=2) is None
    assert len(seen) == 1


def test_a_redirect_into_a_private_address_is_not_followed(monkeypatch, serve):
    def fake(host, port, *args, **kwargs):
        address = "10.0.0.5" if host == "internal.example.org" else PUBLIC
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

    monkeypatch.setattr(page_fetch.socket, "getaddrinfo", fake)
    seen = serve(lambda request: _redirect("https://internal.example.org/admin"))

    assert fetch_page_text("https://docs.example.org/", host_allowed=_allow_all, timeout_seconds=2) is None
    assert len(seen) == 1


def test_an_allowed_relative_redirect_is_followed(resolve, serve):
    resolve(PUBLIC)
    serve(
        lambda request: (
            _redirect("/final")
            if request.url.path == "/start"
            else _html("<p>The page at the end of the redirect.</p>")
        )
    )

    text = fetch_page_text("https://docs.example.org/start", host_allowed=_allow_all, timeout_seconds=2)

    assert text == "The page at the end of the redirect."


def test_redirects_are_bounded(resolve, serve):
    resolve(PUBLIC)
    seen = serve(lambda request: _redirect(f"/hop{len(request.url.path)}"))

    assert fetch_page_text("https://docs.example.org/", host_allowed=_allow_all, timeout_seconds=2) is None
    assert len(seen) == page_fetch._MAX_REDIRECTS + 1


# ---------------------------------------------------------------------------
# What is read
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404, headers={"content-type": "text/html"}, text="<p>not found</p>"),
        httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-1.7"),
        httpx.Response(200, headers={"content-type": "application/octet-stream"}, content=b"\x00\x01"),
    ],
    ids=["not-200", "pdf", "binary"],
)
def test_only_a_successful_text_response_is_read(response, resolve, serve):
    resolve(PUBLIC)
    serve(lambda request: response)

    assert fetch_page_text("https://docs.example.org/", host_allowed=_allow_all, timeout_seconds=2) is None


def test_the_body_is_read_up_to_the_cap_and_no_further(monkeypatch, resolve, serve):
    monkeypatch.setattr(page_fetch, "_MAX_BYTES", 40)
    resolve(PUBLIC)
    serve(lambda request: httpx.Response(200, headers={"content-type": "text/plain"}, text="x" * 10_000))

    text = fetch_page_text("https://docs.example.org/", host_allowed=_allow_all, timeout_seconds=2)

    assert text == "x" * 40


def test_a_page_declaring_gbk_in_a_meta_tag_is_decoded_as_gbk(resolve, serve):
    """Decoded as UTF-8 this is replacement characters the model would paraphrase."""

    body = '<html><head><meta charset="gbk"></head><body><p>零信任架构的核心原则</p></body></html>'.encode("gbk")
    resolve(PUBLIC)
    serve(lambda request: httpx.Response(200, headers={"content-type": "text/html"}, content=body))

    text = fetch_page_text("https://docs.example.org/", host_allowed=_allow_all, timeout_seconds=2)

    assert text == "零信任架构的核心原则"


def test_a_page_is_fetched_once_for_several_queries(resolve, serve):
    """One question searches several rewrites of itself at once, and they return the same pages."""

    resolve(PUBLIC)
    seen = serve(lambda request: _html("<p>cached text</p>"))

    for _ in range(3):
        assert fetch_page_text("https://docs.example.org/", host_allowed=_allow_all, timeout_seconds=2)
    assert len(seen) == 1


def test_a_failure_is_cached_too(resolve, serve):
    resolve(PUBLIC)
    seen = serve(lambda request: httpx.Response(500))

    for _ in range(3):
        assert fetch_page_text("https://docs.example.org/", host_allowed=_allow_all, timeout_seconds=2) is None
    assert len(seen) == 1


def test_a_network_error_is_an_unreadable_page_not_an_exception(resolve, serve):
    def boom(request):
        raise httpx.ConnectTimeout("slow host")

    resolve(PUBLIC)
    serve(boom)

    assert fetch_page_text("https://docs.example.org/", host_allowed=_allow_all, timeout_seconds=2) is None


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def test_page_furniture_and_code_are_not_text():
    html = """
    <html><head><style>p { color: red }</style><script>var secret = 1;</script></head>
    <body><nav>Home | About</nav><header>Site header</header>
    <article><h1>Title</h1><p>The body of the article.</p></article>
    <footer>Copyright</footer></body></html>"""

    assert html_to_text(html) == "Title\nThe body of the article."


def test_a_table_row_is_one_line():
    """A cell is not a paragraph: split per cell, a mitigation table became
    lines like "M1048", too short to select, and the picker took the bibliography."""

    html = """<table><tr><th>ID</th><th>Mitigation</th></tr>
    <tr><td><a href="/m">M1048</a></td>
        <td><p>Application isolation will limit what the exploited target can access.</p></td></tr></table>"""

    assert html_to_text(html) == (
        "ID | Mitigation\nM1048 | Application isolation will limit what the exploited target can access."
    )


def test_the_space_beside_an_inline_tag_survives():
    assert html_to_text("<p>During <a href='/c'>Cutting Edge</a>, actors exploited it.</p>") == (
        "During Cutting Edge, actors exploited it."
    )


def test_a_newline_in_the_markup_does_not_break_a_line():
    assert html_to_text("<p>one\n   two\n\tthree</p>") == "one two three"


# ---------------------------------------------------------------------------
# Passage selection
# ---------------------------------------------------------------------------

_LONG = "x" * 60


def test_only_paragraphs_sharing_a_term_are_kept_in_page_order():
    text = "\n".join(
        [
            "Kubernetes schedules containers across a cluster of machines. " + _LONG,
            "An unrelated paragraph about the weather and nothing else at all.",
            "Kubernetes restarts containers that fail their health checks. " + _LONG,
        ]
    )

    passages = relevant_passages(text, "What does Kubernetes do?")

    assert passages.split("\n") == [text.split("\n")[0], text.split("\n")[2]]


def test_nothing_shared_means_nothing_kept():
    """So the caller keeps the snippet rather than evidence about something else."""

    assert relevant_passages("An unrelated paragraph about the weather and nothing else.", "Kubernetes?") == ""


def test_a_paragraph_inherits_the_terms_of_its_heading():
    text = "\n".join(
        [
            "Mitigations",
            "M1048 | Application isolation will limit what the exploited target can access.",
            "Other",
            "M9999 | A row in a section the question did not ask about, at similar length.",
        ]
    )

    assert relevant_passages(text, "How do I mitigate it?") == (
        "M1048 | Application isolation will limit what the exploited target can access."
    )


def test_a_term_on_every_line_counts_for_less_than_a_rare_one():
    common = [f"Detection note number {index} says something generic about detection. {_LONG}" for index in range(8)]
    rare = "Detection of T1190 relies on correlating web server errors with spawned shells. " + _LONG
    text = "\n".join([*common, rare])

    passages = relevant_passages(text, "How to detect T1190?", max_chars=len(rare) + 5)

    assert passages == rare


def test_bibliography_entries_are_not_passages():
    text = "\n".join(
        [
            "Bromiley, M. (2021, March 4). Detection and Response to Exploitation. Retrieved March 9, 2021.",
            '"What is Log4Shell?". Dynatrace news. Archived from the original on 12 December 2021',
            "Detection relies on correlating web server errors with processes spawned by the server.",
        ]
    )

    assert relevant_passages(text, "detection") == (
        "Detection relies on correlating web server errors with processes spawned by the server."
    )


def test_a_repeated_line_is_kept_once():
    line = "Log4Shell (CVE-2021-44228) is a vulnerability in Log4j, a Java logging framework."

    assert relevant_passages("\n".join([line, line, line]), "CVE-2021-44228") == line


def test_an_identifier_is_matched_whole_not_by_its_prefix():
    """Cut to six characters, CVE-2021-44228 became `cve-20` and matched every CVE."""

    text = "\n".join(
        [
            "CVE-2021-45046 is a different vulnerability, fixed in a later release of the library.",
            "CVE-2021-44228 was rated CVSS 10, the highest score available for a vulnerability.",
        ]
    )

    assert relevant_passages(text, "CVE-2021-44228") == text.split("\n")[1]


def test_a_word_is_matched_by_its_stem():
    text = "Mitigations include isolating the application and patching the exposed service quickly."

    assert relevant_passages(text, "how to mitigate") == text


def test_chinese_is_matched_by_character_pairs():
    text = "零信任架构的核心原则是永不信任、始终验证，并对每一次访问进行持续评估。这一段足够长。"

    assert relevant_passages(text, "零信任架构的核心原则有哪些？") == text
    assert relevant_passages(text, "有哪些？") == "", "question words alone are not a match"


def test_the_budget_is_respected():
    text = "\n".join(f"Kubernetes paragraph {index}: " + "k" * 300 for index in range(20))

    passages = relevant_passages(text, "kubernetes", max_chars=700)

    assert len(passages) <= 700 + 3
