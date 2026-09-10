"""When every web result is rejected, the log must say by what and from where.

`WEB_DOMAIN_ALLOWLIST` ships non-empty -- eleven entries -- and in allowlist
mode anything not on it scores 0.0 and is discarded. So on a default
installation with an empty corpus, most questions get five search results and
zero evidence, and the answer says "I could not find anything to answer from".

That answer is true and the reason is invisible. The warning said only
"No results passed quality filters (min_score=0.5)", which does not distinguish
a throttled search engine from an allowlist doing exactly its job -- and those
need opposite responses from an operator.

Measured on 2026-09-09: `veso.ai`, `thequery.in`, `blog.csdn.net` score 0.0;
`arxiv.org` and `en.wikipedia.org` score 1.0. Which is why some questions
answered with web citations that day and some found nothing.
"""

from __future__ import annotations

import logging

import pytest

from app.agents.rag.web import _parse_allowlist, _source_score


def test_the_shipped_allowlist_rejects_an_ordinary_domain():
    """The property that makes the warning worth having."""

    from app.core.config import get_settings

    allow = _parse_allowlist(get_settings().web_domain_allowlist)

    assert allow, "the allowlist ships non-empty; if it stops, this test is measuring nothing"
    assert _source_score("https://veso.ai/blog/x", allowlist=allow) == 0.0
    assert _source_score("https://blog.csdn.net/a", allowlist=allow) == 0.0
    # And the ones that do pass, so this cannot be satisfied by rejecting all.
    assert _source_score("https://arxiv.org/abs/1", allowlist=allow) == 1.0
    assert _source_score("https://en.wikipedia.org/wiki/X", allowlist=allow) == 1.0


def test_the_warning_names_the_rejected_hosts(monkeypatch: pytest.MonkeyPatch, caplog):
    import app.agents.rag.web as web

    monkeypatch.setattr(
        web,
        "search_web",
        lambda question, max_results=5: [
            {"title": "a", "href": "https://veso.ai/blog/x", "body": "b"},
            {"title": "c", "href": "https://blog.csdn.net/a", "body": "d"},
        ],
    )

    with caplog.at_level(logging.WARNING, logger=web.logger.name):
        result = web.run_web_research("what is reciprocal rank fusion")

    assert result["used"] is False
    warning = "\n".join(record.getMessage() for record in caplog.records)
    assert "veso.ai" in warning, warning
    assert "blog.csdn.net" in warning, warning
    assert "WEB_DOMAIN_ALLOWLIST" in warning, "the warning does not say what to change"


def test_the_warning_does_not_carry_the_question(monkeypatch: pytest.MonkeyPatch, caplog):
    """The repository rule: a user's question never reaches the logs."""

    import app.agents.rag.web as web

    monkeypatch.setattr(
        web,
        "search_web",
        lambda question, max_results=5: [{"title": "a", "href": "https://veso.ai/x", "body": "b"}],
    )
    question = "我的团队在深圳办公吗"

    with caplog.at_level(logging.DEBUG, logger=web.logger.name):
        web.run_web_research(question)

    assert question not in "\n".join(record.getMessage() for record in caplog.records)
