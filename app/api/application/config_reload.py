"""One definition of "the configuration was reloaded".

Two things now trigger a reload -- the admin endpoint and a push from the
configuration centre -- and they must do the same work. A watcher that dropped
its own subset of the caches would be a second, quieter definition, and the
difference would only ever show up as "the value took effect when I clicked the
button but not when I saved it in the console".

Living in the API layer rather than under `app/services/` is deliberate: the
sequence has to touch `api_dependencies`, and a service importing the API layer
would invert the dependency.
"""

from __future__ import annotations

import logging

from app.agents.shared.cache import clear_router_decision_cache
from app.agents.verifier.validation.public import clear_validation_caches
from app.api import dependencies as api_dependencies
from app.core.config import Settings, get_settings, reload_settings
from app.core.config_schema import environment_aliases, validate_values
from app.core.remote_config import RemoteDocuments, parse_properties, remote_config_enabled, render_properties
from app.graph.knowledge.client import Neo4jClient
from app.retrievers.hybrid.caching import clear_retrieval_cache
from app.retrievers.reranker import clear_reranker_cache
from app.retrievers.stores.vector import clear_vector_store_cache
from app.services.models.runtime import clear_model_caches
from app.services.runtime.bulkhead import reset_bulkheads
from app.services.runtime.invalidation import announce
from app.tools.web.factory import clear_provider_cache

logger = logging.getLogger(__name__)


def apply_config_reload() -> Settings:
    """Re-read `Settings` and drop everything built from the old ones.

    Every editable field's consumer is covered: read through `get_settings()` per
    use, or rebuilt here, or held by an object `RAGPipeline` constructs per
    request. That is what lets the admin schema report `requires_restart=False`
    across the board -- audited on 2026-09-01, and the retrieval cache was the one
    exception, which is why it is cleared here rather than marked.
    """

    new_settings = reload_settings()
    api_dependencies.reload_query_runtime(new_settings)
    clear_model_caches()
    clear_vector_store_cache()
    # The retrieval cache bakes its TTL and size in at construction and lives in
    # a module global, so a reload that left it alone would silently keep the old
    # TTL -- and the admin page would show the new one as though it had taken.
    clear_retrieval_cache()
    # Same shape as the retrieval cache above: the validation cascade bakes
    # every CASCADE_* value in at construction and lives in a module global,
    # and the NLI model is lru_cache'd on NLI_MODEL_NAME.
    clear_validation_caches()
    # clear_model_caches covers chat and embedding only; the reranker keeps
    # its own lru_cache keyed on RERANKER_MODEL_NAME.
    clear_reranker_cache()
    # `decide_route` is memoized for 30 minutes on a key of question and hints
    # only, and its result reads two editable settings: ENABLE_CALIBRATION,
    # through `_calibrated`, and ENABLE_WEB_ROUTE_DOWNGRADE, through `_llm_route`.
    # Toggling either from the console reported success and left every question
    # already in the cache routing the old way until the entry expired. Not caught
    # by test_the_reload_reaches_every_cache_that_holds_an_editable_setting, which
    # walks `@lru_cache` functions -- this one is a hand-rolled TTL store.
    clear_router_decision_cache()
    # Search providers are cached with the Settings object they were built from,
    # so WEB_SEARCH_PROVIDER / WEB_SEARCH_MAX_RETRIES edits need a fresh instance.
    clear_provider_cache()
    Neo4jClient.close_shared_driver()
    reset_bulkheads()
    return new_settings


def reload_from_remote_config() -> None:
    """Callback for the configuration centre; never raises into the SDK thread."""

    try:
        apply_config_reload()
        logger.info("remote config: change applied")
    except Exception:
        logger.exception("remote config: change could not be applied")


class ConfigWriteRefused(Exception):
    """The change was not written, and why. Nothing reached the centre."""


class ConfigWritePartiallyApplied(Exception):
    """Some documents were written and one was not, and which.

    A change that spans two documents is two `publish` calls against an external
    system, and they are not one transaction. The previous code raised
    `ConfigWriteRefused` for that, so the endpoint audited `result="failure"` and
    answered "refused" for a change that had partly landed -- and skipped
    `apply_config_reload()`, leaving the process on its old values while the
    centre already held new ones. The change then took effect anyway, silently,
    when the poller noticed up to `NACOS_POLL_INTERVAL_MS` later.

    **Rolling the written documents back is not the answer.** The rollback is one
    more publish against the system that just failed, so it can fail too and leave
    a third state nobody has described; and the centre owns version history and
    rollback, which is precisely why this layer does not merge. So the residue is
    named instead: the documents that were written stay written, the process is
    reloaded so it agrees with what the centre now holds, and the caller is told
    exactly which half landed.

    Shaped after `ConnectorMetadataRepository`'s deletion order, where which
    residue an interrupted operation leaves is the whole design.
    """

    def __init__(self, written: list[str], failed: str, reason: str) -> None:
        self.written = list(written)
        self.failed = failed
        self.reason = reason
        super().__init__(
            f"wrote {', '.join(self.written)} and then could not write {failed}: {reason}. "
            f"The configuration centre now holds part of this change and the process has been "
            f"reloaded to match it; re-apply the rest."
        )


def write_config_values(values: dict[str, str], data_id: str | None = None) -> list[str]:
    """Persist edited values through the configuration centre, then reload.

    The one way configuration is changed at runtime. Both the admin page and the
    replay autotuner go through here, because the alternative -- what the
    autotuner used to do -- is to assign onto the live `Settings` object, and
    that fails twice over: the change is lost at the next reload, and the admin
    page's "which layer did this come from" column starts lying, since the value
    came from none of the layers.

    Returns the data ids written. Raises `ConfigWriteRefused` when the change
    cannot be made honestly: no configuration centre to write to, a value the
    process environment pins (the environment outranks the centre, so the write
    would succeed and change nothing), an unknown data id, or a value that is not
    editable or does not type-check.
    """

    if not values:
        return []
    if not remote_config_enabled():
        raise ConfigWriteRefused("no configuration centre is configured; set NACOS_ENABLED and restart")

    # One snapshot for both checks below. `validate_values` merges the edit onto
    # it rather than onto the field defaults, so what is type-checked is the
    # configuration this change would actually produce.
    active = get_settings()
    try:
        accepted = validate_values(values, current=active)
    except ValueError as exc:
        raise ConfigWriteRefused(str(exc)) from exc

    # Only the environment layer can refuse a write, so this asks for exactly
    # that. It used to call `describe(...)`, which fetches every configuration
    # centre document in order to fill in a column nothing here reads -- a
    # network round trip per data id, on the way to reading those same documents
    # again a few lines below.
    pinned = sorted(set(accepted) & environment_aliases())
    if pinned:
        raise ConfigWriteRefused(
            f"pinned in the process environment, so the console cannot change them: {', '.join(pinned)}"
        )

    documents = RemoteDocuments()
    known = documents.config.data_ids
    if data_id is not None and data_id not in known:
        raise ConfigWriteRefused(f"unknown data id: {data_id}")

    current = {name: parse_properties(text) for name, text in documents.all().items()}
    fallback = data_id or known[-1]

    routed = _route_values_to_documents(accepted, data_id, known, current, fallback)
    try:
        written = _publish_routed_documents(documents, routed, current)
    except ConfigWritePartiallyApplied:
        # The centre holds part of the change, so the process has to as well --
        # otherwise the page shows one configuration and the running process uses
        # another until the poller happens to notice.
        apply_config_reload()
        announce("config")
        raise

    apply_config_reload()
    # Every process polls the configuration centre, so the others would get this
    # within NACOS_POLL_INTERVAL_MS anyway; announcing makes it the next request.
    announce("config")
    return sorted(written)


def _route_values_to_documents(
    accepted: dict[str, str],
    data_id: str | None,
    known: list[str],
    current: dict[str, dict[str, str]],
    fallback: str,
) -> dict[str, dict[str, str]]:
    """Each key goes back to the document that already defines it.

    Writing everything to one document instead puts the same key in two places,
    where the later id silently wins -- so the page would show a value from one
    document, the edit would land in another, and the two would drift apart.
    """
    routed: dict[str, dict[str, str]] = {}
    for alias, value in accepted.items():
        target = data_id
        if target is None:
            owning = [name for name in known if alias in current.get(name, {})]
            target = owning[-1] if owning else fallback
        routed.setdefault(target, {})[alias] = value
    return routed


def _publish_routed_documents(
    documents: RemoteDocuments, routed: dict[str, dict[str, str]], current: dict[str, dict[str, str]]
) -> list[str]:
    """Render every document before publishing any of them.

    Rendering is what refuses a value that would carry a configuration key of its
    own -- see `remote_config.render_properties`. Doing it up front rather than
    inside the publish loop is what keeps that refusal from landing halfway: a
    two-document change whose second document holds the injected value used to
    write the first one and only then refuse.
    """

    merged_documents: dict[str, dict[str, str]] = {
        name: {**current.get(name, {}), **changes} for name, changes in routed.items()
    }
    for merged in merged_documents.values():
        try:
            render_properties(merged)
        except ValueError as exc:
            raise ConfigWriteRefused(str(exc)) from exc

    written: list[str] = []
    # Sorted so the order documents are written in -- and therefore which half
    # survives an interrupted change -- is a property of the change rather than of
    # dictionary insertion order.
    for name in sorted(merged_documents):
        reason = _publish_one(documents, name, merged_documents[name])
        if reason is None:
            written.append(name)
            continue
        if written:
            raise ConfigWritePartiallyApplied(written, name, reason)
        raise ConfigWriteRefused(reason)
    return written


def _publish_one(documents: RemoteDocuments, name: str, merged: dict[str, str]) -> str | None:
    """Publish one document; return why it did not land, or None if it did."""

    try:
        published = documents.publish(name, merged)
    except Exception as exc:
        logger.exception("config write: publish failed for %s", name)
        return f"the configuration centre rejected the write: {exc}"
    return None if published else f"the configuration centre did not accept the write to {name}"


__all__ = [
    "ConfigWritePartiallyApplied",
    "ConfigWriteRefused",
    "apply_config_reload",
    "reload_from_remote_config",
    "write_config_values",
]
