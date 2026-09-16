import logging
import re
import threading
import time

from neo4j import GraphDatabase
from neo4j.exceptions import ClientError, CypherSyntaxError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_NO_RETRY = object()

# Descriptions are stored per source and read per source. An entity node is
# shared by every document that names it (MERGE on name), and so is a RELATED
# edge, so a single `e.description` or `r.description` written from one tenant's
# document would be shown to every other tenant whose document mentions the same
# name. Entity descriptions live on the (entity)-[:MENTIONED_IN]->(source) edge;
# relationship descriptions in `r.source_descriptions` as "source<SEP>text",
# because a relationship property cannot hold a map.
_DESC_SEP = "\x1f"

_SCOPED_ENTITY_PROJECTION = """
WITH e, [d IN collect(m.description) WHERE d IS NOT NULL AND d <> ''] AS descs
OPTIONAL MATCH (e)-[r:RELATED]-(o:Entity)
WHERE any(src IN coalesce(r.sources, []) WHERE src IN $allowed_sources)
WITH e, descs, r, o,
     [d IN coalesce(r.source_descriptions, []) WHERE split(d, $sep)[0] IN $allowed_sources | split(d, $sep)[1]]
         AS rel_descs
RETURN e.name AS entity,
       coalesce(e.type, 'CONCEPT') AS type,
       coalesce(head(descs), '') AS description,
       collect(DISTINCT {relation: r.type, other: o.name, rel_desc: coalesce(head(rel_descs), '')})[..20] AS relations
LIMIT $limit
"""

_UNSCOPED_ENTITY_PROJECTION = """
OPTIONAL MATCH (e)-[m:MENTIONED_IN]->(:Source)
WITH e, [d IN collect(m.description) WHERE d IS NOT NULL AND d <> ''] AS descs
OPTIONAL MATCH (e)-[r:RELATED]-(o:Entity)
WITH e, descs, r, o, [d IN coalesce(r.source_descriptions, []) | split(d, $sep)[1]] AS rel_descs
RETURN e.name AS entity,
       coalesce(e.type, 'CONCEPT') AS type,
       coalesce(head(descs), '') AS description,
       collect(DISTINCT {relation: r.type, other: o.name, rel_desc: coalesce(head(rel_descs), '')})[..20] AS relations
LIMIT $limit
"""


def _validate_triplets(triplets: list[dict]) -> None:
    """Raise if any triplet is missing, or has a malformed, required field."""
    required_fields = ["head", "relation", "tail", "source"]
    for i, triplet in enumerate(triplets):
        if not isinstance(triplet, dict):
            raise TypeError(f"triplets[{i}] must be a dict, got {type(triplet).__name__}")
        for field in required_fields:
            if field not in triplet:
                raise ValueError(f"triplets[{i}] missing required field: {field}")
            if not isinstance(triplet[field], str):
                raise TypeError(f"triplets[{i}][{field}] must be a string, got {type(triplet[field]).__name__}")
            if not triplet[field].strip():
                raise ValueError(f"triplets[{i}][{field}] cannot be empty")


class Neo4jClient:
    _driver = None
    _schema_inited = False
    _schema_init_in_progress = False
    _lock = threading.Lock()
    _schema_cv = threading.Condition(_lock)

    def __init__(self):
        self.driver = self._shared_driver()
        self._ensure_schema()

    def close(self):
        # Shared driver lifecycle is managed at process level.
        return None

    @classmethod
    def close_shared_driver(cls) -> None:
        with cls._schema_cv:
            driver = cls._driver
            cls._driver = None
            cls._schema_inited = False
            cls._schema_init_in_progress = False
            cls._schema_cv.notify_all()
        if driver is not None:
            driver.close()

    @classmethod
    def _shared_driver(cls):
        with cls._lock:
            if cls._driver is None:
                settings = get_settings()
                cls._driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_username, settings.neo4j_password),
                    max_connection_lifetime=1800,
                )
            return cls._driver

    def _ensure_schema(self):
        with self.__class__._schema_cv:
            while True:
                if self.__class__._schema_inited:
                    return
                if not self.__class__._schema_init_in_progress:
                    self.__class__._schema_init_in_progress = True
                    break
                self.__class__._schema_cv.wait()
        ok = False
        try:
            with self.driver.session() as session:
                session.run("CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
                session.run("CREATE INDEX source_name IF NOT EXISTS FOR (s:Source) ON (s.name)")
                session.run("CREATE INDEX chunk_id IF NOT EXISTS FOR (c:Chunk) ON (c.id)")
                session.run("CREATE INDEX community_id IF NOT EXISTS FOR (cm:Community) ON (cm.id)")
                try:
                    session.run(
                        "CREATE FULLTEXT INDEX entity_fulltext_idx IF NOT EXISTS FOR (e:Entity) ON EACH [e.name]"
                    )
                except Exception as ft_err:
                    logger.debug("Fulltext index creation skipped or unsupported: %s", ft_err)
            ok = True
        finally:
            with self.__class__._schema_cv:
                self.__class__._schema_inited = bool(ok)
                self.__class__._schema_init_in_progress = False
                self.__class__._schema_cv.notify_all()

    def _retry_with_simpler_query(self, session, query_type: str | None, params: dict, retry_log_message: str):
        """Best-effort fallback to a simpler query for ``query_type``.

        Returns the sentinel ``_NO_RETRY`` when there is no query_type, no
        simpler query for it, or the retry itself fails -- distinct from any
        real (falsy-but-valid) query result.
        """
        if not query_type:
            return _NO_RETRY
        from app.graph.knowledge.cypher_validation import get_simpler_query

        allowed_sources = params.get("allowed_sources")
        simpler_query = get_simpler_query(query_type, allowed_sources)
        if not simpler_query:
            return _NO_RETRY
        logger.info(retry_log_message, query_type)
        try:
            return session.run(simpler_query, **params)
        except Exception as retry_error:
            logger.exception("Simpler query also failed: %s", retry_error)
            return _NO_RETRY

    def _execute_query_safe(self, session, cypher: str, query_type: str | None = None, **params):
        """
        Execute a Cypher query with validation, error handling, and retry logic.

        Args:
            session: Neo4j session
            cypher: Cypher query string
            query_type: Type of query for fallback (e.g., "entity_neighbors", "entity_paths_2hop")
            **params: Query parameters

        Returns:
            Query result

        Raises:
            Exception: If query fails and cannot be retried
        """
        from app.graph.knowledge.cypher_validation import validate_cypher_query

        # Validate query before execution
        validation = validate_cypher_query(cypher)
        if not validation.is_valid:
            logger.warning("Cypher query validation failed: %s (type: %s)", validation.error, validation.error_type)
            retried = self._retry_with_simpler_query(
                session, query_type, params, "Retrying with simpler query for type: %s"
            )
            if retried is not _NO_RETRY:
                return retried
            # Fall through to original execution attempt

        try:
            return session.run(cypher, **params)
        except (CypherSyntaxError, ClientError):
            logger.exception("Cypher query execution failed")
            logger.debug("Failed query: %s", cypher)

            retried = self._retry_with_simpler_query(
                session, query_type, params, "Retrying with simpler query after execution error for type: %s"
            )
            if retried is not _NO_RETRY:
                return retried
            raise

    def upsert_triplet(
        self,
        head: str,
        relation: str,
        tail: str,
        source: str,
        chunk_id: str = "",
        page: int | None = None,
        confidence: float = 0.7,
    ):
        cypher = """
        MERGE (h:Entity {name: $head})
        MERGE (t:Entity {name: $tail})
        MERGE (s:Source {name: $source})
        MERGE (h)-[r:RELATED {type: $relation}]->(t)
        SET r.sources = CASE
            WHEN r.sources IS NULL THEN [$source]
            WHEN $source IN r.sources THEN r.sources
            ELSE r.sources + $source
        END,
        r.chunk_ids = CASE
            WHEN $chunk_id = "" THEN coalesce(r.chunk_ids, [])
            WHEN r.chunk_ids IS NULL THEN [$chunk_id]
            WHEN $chunk_id IN r.chunk_ids THEN r.chunk_ids
            ELSE r.chunk_ids + $chunk_id
        END,
        r.pages = CASE
            WHEN $page IS NULL THEN coalesce(r.pages, [])
            WHEN r.pages IS NULL THEN [$page]
            WHEN $page IN r.pages THEN r.pages
            ELSE r.pages + $page
        END,
        r.confidence_max = CASE
            WHEN r.confidence_max IS NULL OR $confidence > r.confidence_max THEN $confidence
            ELSE r.confidence_max
        END,
        r.confidence_count = coalesce(r.confidence_count, 0) + 1,
        r.confidence_avg = CASE
            WHEN r.confidence_avg IS NULL THEN $confidence
            ELSE ((r.confidence_avg * (r.confidence_count - 1)) + $confidence) / r.confidence_count
        END
        MERGE (h)-[:MENTIONED_IN]->(s)
        MERGE (t)-[:MENTIONED_IN]->(s)
        RETURN h.name, r.type, t.name
        """
        with self.driver.session() as session:
            session.run(
                cypher,
                head=head,
                relation=relation,
                tail=tail,
                source=source,
                chunk_id=chunk_id,
                page=page,
                confidence=float(confidence),
            )

    def batch_upsert_triplets(
        self,
        triplets: list[dict],
        batch_size: int = 100,
    ) -> int:
        """
        Batch upsert multiple triplets for better performance (~10x faster than individual upserts).

        Args:
            triplets: List of triplet dicts with keys: head, relation, tail, source,
                     chunk_id (optional), page (optional), confidence
            batch_size: Number of triplets to process per transaction (default: 100)

        Returns:
            Total number of triplets processed

        Example:
            triplets = [
                {
                    "head": "Python", "relation": "is_a", "tail": "Language",
                    "source": "doc.txt", "chunk_id": "chunk_1", "page": 1, "confidence": 0.9
                },
                ...
            ]
            count = client.batch_upsert_triplets(triplets)
        """
        # Input validation
        if not isinstance(triplets, list):
            raise TypeError(f"triplets must be a list, got {type(triplets).__name__}")

        if not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError(f"batch_size must be a positive integer, got {batch_size}")

        if not triplets:
            return 0

        _validate_triplets(triplets)

        # Cypher query using UNWIND for batch processing with rich types and chunk
        # grounding. Descriptions are written per source -- see _DESC_SEP. A type
        # of CONCEPT is the default, not a claim, so it never overwrites a real one.
        cypher = """
        UNWIND $batch AS triplet
        MERGE (h:Entity {name: triplet.head})
        SET h.type = CASE
            WHEN triplet.head_type <> "CONCEPT" THEN triplet.head_type
            ELSE coalesce(h.type, "CONCEPT")
        END
        MERGE (t:Entity {name: triplet.tail})
        SET t.type = CASE
            WHEN triplet.tail_type <> "CONCEPT" THEN triplet.tail_type
            ELSE coalesce(t.type, "CONCEPT")
        END
        MERGE (s:Source {name: triplet.source})
        SET s.document_id = triplet.document_id,
            s.version = triplet.version,
            s.tenant_id = triplet.tenant_id,
            s.owner_user_id = triplet.owner_user_id,
            s.visibility = triplet.visibility,
            s.acl_tags = triplet.acl_tags
        MERGE (h)-[r:RELATED {type: triplet.relation}]->(t)
        SET r.source_descriptions = CASE
            WHEN triplet.relation_description = "" THEN coalesce(r.source_descriptions, [])
            ELSE [d IN coalesce(r.source_descriptions, []) WHERE split(d, $sep)[0] <> triplet.source]
                 + (triplet.source + $sep + triplet.relation_description)
        END,
        r.sources = CASE
            WHEN r.sources IS NULL THEN [triplet.source]
            WHEN triplet.source IN r.sources THEN r.sources
            ELSE r.sources + triplet.source
        END,
        r.chunk_ids = CASE
            WHEN triplet.chunk_id = "" THEN coalesce(r.chunk_ids, [])
            WHEN r.chunk_ids IS NULL THEN [triplet.chunk_id]
            WHEN triplet.chunk_id IN r.chunk_ids THEN r.chunk_ids
            ELSE r.chunk_ids + triplet.chunk_id
        END,
        r.pages = CASE
            WHEN triplet.page IS NULL THEN coalesce(r.pages, [])
            WHEN r.pages IS NULL THEN [triplet.page]
            WHEN triplet.page IN r.pages THEN r.pages
            ELSE r.pages + triplet.page
        END,
        r.confidence_max = CASE
            WHEN r.confidence_max IS NULL OR triplet.confidence > r.confidence_max THEN triplet.confidence
            ELSE r.confidence_max
        END,
        r.confidence_count = coalesce(r.confidence_count, 0) + 1,
        r.confidence_avg = CASE
            WHEN r.confidence_avg IS NULL THEN triplet.confidence
            ELSE ((r.confidence_avg * (r.confidence_count - 1)) + triplet.confidence) / r.confidence_count
        END
        MERGE (h)-[mh:MENTIONED_IN]->(s)
        SET mh.description = CASE
            WHEN triplet.head_description <> "" THEN triplet.head_description
            ELSE coalesce(mh.description, "")
        END
        MERGE (t)-[mt:MENTIONED_IN]->(s)
        SET mt.description = CASE
            WHEN triplet.tail_description <> "" THEN triplet.tail_description
            ELSE coalesce(mt.description, "")
        END
        FOREACH (_ IN CASE WHEN triplet.chunk_id <> "" THEN [1] ELSE [] END |
            MERGE (c:Chunk {id: triplet.chunk_id})
            SET c.source = triplet.source,
                c.page = triplet.page,
                c.document_id = triplet.document_id,
                c.tenant_id = triplet.tenant_id
            MERGE (c)-[:MENTIONS]->(h)
            MERGE (c)-[:MENTIONS]->(t)
        )
        """

        total_processed = 0
        start_time = time.time()

        with self.driver.session() as session:
            # Process in batches to avoid memory issues with large datasets
            num_batches = (len(triplets) + batch_size - 1) // batch_size
            logger.info(f"Processing {len(triplets)} triplets in {num_batches} batches of {batch_size}")

            for batch_idx, i in enumerate(range(0, len(triplets), batch_size), 1):
                batch_start = time.time()
                batch = triplets[i : i + batch_size]

                # Ensure all triplets have required fields with defaults
                normalized_batch = [
                    {
                        "head": t["head"],
                        "relation": t["relation"],
                        "tail": t["tail"],
                        "source": t["source"],
                        "head_type": str(t.get("head_type", "CONCEPT") or "CONCEPT"),
                        "tail_type": str(t.get("tail_type", "CONCEPT") or "CONCEPT"),
                        "head_description": str(t.get("head_description", "") or ""),
                        "tail_description": str(t.get("tail_description", "") or ""),
                        "relation_description": str(t.get("relation_description", "") or ""),
                        "chunk_id": t.get("chunk_id", ""),
                        "page": t.get("page"),
                        "document_id": t.get("document_id", ""),
                        "version": t.get("version"),
                        "tenant_id": t.get("tenant_id", ""),
                        "owner_user_id": t.get("owner_user_id", ""),
                        "visibility": t.get("visibility", "private"),
                        "acl_tags": t.get("acl_tags", ""),
                        "confidence": float(t.get("confidence", 0.7)),
                    }
                    for t in batch
                ]
                session.run(cypher, batch=normalized_batch, sep=_DESC_SEP)
                total_processed += len(batch)

                batch_time = time.time() - batch_start
                logger.debug(f"Batch {batch_idx}/{num_batches}: {len(batch)} triplets in {batch_time:.2f}s")

        total_time = time.time() - start_time
        triplets_per_sec = total_processed / total_time if total_time > 0 else 0
        logger.info(
            f"Batch upsert completed: {total_processed} triplets in {total_time:.2f}s "
            f"({triplets_per_sec:.1f} triplets/sec)"
        )

        return total_processed

    def _search_entities_fulltext(
        self, session, keywords: list[str], limit: int, allowed_sources: list[str] | None
    ) -> list[dict] | None:
        """Attempt fast indexed retrieval using Neo4j Full-Text index. Returns None on fallback."""
        clean_terms = [re.sub(r"[^\w\u4e00-\u9fff]", "", k) for k in keywords if k.strip()]
        clean_terms = [k for k in clean_terms if k]
        if not clean_terms:
            return None
        lucene_query = " OR ".join(f"{t}*" for t in clean_terms[:10])
        fulltext = 'CALL db.index.fulltext.queryNodes("entity_fulltext_idx", $query) YIELD node AS e, score\n'
        try:
            if allowed_sources is not None:
                cypher = (
                    fulltext
                    + "MATCH (e)-[m:MENTIONED_IN]->(s:Source)\nWHERE s.name IN $allowed_sources\n"
                    + _SCOPED_ENTITY_PROJECTION
                )
                params = {"query": lucene_query, "limit": limit, "allowed_sources": allowed_sources, "sep": _DESC_SEP}
            else:
                cypher = fulltext + _UNSCOPED_ENTITY_PROJECTION
                params = {"query": lucene_query, "limit": limit, "sep": _DESC_SEP}
            records = session.run(cypher, **params)
            results = [dict(r) for r in records]
            return results if results else None
        except Exception:
            return None

    def search_entities(
        self, keywords: list[str], limit: int = 10, allowed_sources: list[str] | None = None
    ) -> list[dict]:
        if allowed_sources is not None:
            if not allowed_sources:  # NOSONAR
                return []
        if not keywords:
            return []

        with self.driver.session() as session:
            # 1. Try modern Full-Text index first for O(1) keyword match
            ft_results = self._search_entities_fulltext(session, keywords, limit, allowed_sources)
            if ft_results is not None:
                return ft_results

            # 2. Resilient fallback to substring match
            substring = "WHERE any(k IN $keywords WHERE toLower(e.name) CONTAINS toLower(k))\n"
            if allowed_sources is not None:
                cypher = (
                    "MATCH (e:Entity)-[m:MENTIONED_IN]->(s:Source)\n"
                    + substring
                    + "  AND s.name IN $allowed_sources\n"
                    + _SCOPED_ENTITY_PROJECTION
                )
                params = {"keywords": keywords, "limit": limit, "allowed_sources": allowed_sources, "sep": _DESC_SEP}
            else:
                cypher = "MATCH (e:Entity)\n" + substring + _UNSCOPED_ENTITY_PROJECTION
                params = {"keywords": keywords, "limit": limit, "sep": _DESC_SEP}
            return [dict(r) for r in self._execute_query_safe(session, cypher, query_type="entity_search", **params)]

    def save_community_summaries(self, communities: list[dict]) -> int:
        """
        Replace the community summaries of the sources these communities came from.

        Each community dict: {"id", "title", "level", "summary", "findings",
        "entity_names", "sources"}. `sources` is what makes a summary readable at
        all: `get_community_summaries` shows one only to a reader who may read
        every source it was built from, so a community without attribution is
        dropped rather than stored unreadable-but-present.

        The sources' previous communities are deleted first. Ids are positional,
        so a rebuild that finds fewer clusters, or different members, would
        otherwise leave stale nodes and BELONGS_TO edges behind.
        """
        attributed = [comm for comm in communities if comm.get("sources")]
        if len(attributed) < len(communities):
            logger.warning("Dropped %d community summaries with no source", len(communities) - len(attributed))
        if not attributed:
            return 0
        sources = sorted({str(src) for comm in attributed for src in comm["sources"]})
        delete_cypher = """
        MATCH (c:Community)
        WHERE any(src IN coalesce(c.sources, []) WHERE src IN $sources)
        DETACH DELETE c
        """
        cypher = """
        UNWIND $communities AS comm
        MERGE (c:Community {id: comm.id})
        SET c.title = comm.title,
            c.level = coalesce(comm.level, 0),
            c.summary = comm.summary,
            c.findings = coalesce(comm.findings, []),
            c.sources = comm.sources,
            c.updated_at = timestamp()
        WITH c, comm
        UNWIND comm.entity_names AS ent_name
        MATCH (e:Entity {name: ent_name})
        MERGE (e)-[:BELONGS_TO]->(c)
        """
        with self.driver.session() as session:
            try:
                session.run(delete_cypher, sources=sources)
                session.run(cypher, communities=attributed)
                return len(attributed)
            except Exception as e:
                logger.warning("Failed to save community summaries to Neo4j: %s", e)
                return 0

    def get_community_summaries(
        self, limit: int = 5, level: int | None = None, allowed_sources: list[str] | None = None
    ) -> list[dict]:
        """
        Retrieve community summaries for Global Search.

        A summary is text built from its sources' triplets, so it is shown only
        when *every* source it was built from is in scope. Matching on "one
        member entity is mentioned somewhere in scope" -- entities are shared by
        name across tenants -- would hand over the rest of the summary too.
        Communities with no recorded source (written before attribution existed)
        are never returned on a scoped read.
        """
        if allowed_sources is not None:
            if not allowed_sources:  # NOSONAR
                return []

        with self.driver.session() as session:
            try:
                if allowed_sources is not None:
                    cypher = """
                    MATCH (c:Community)
                    WHERE size(coalesce(c.sources, [])) > 0
                      AND all(src IN c.sources WHERE src IN $allowed_sources)
                      AND ($level IS NULL OR c.level = $level)
                    OPTIONAL MATCH (c)<-[:BELONGS_TO]-(e:Entity)
                    RETURN c.id AS id, c.title AS title, c.level AS level, c.summary AS summary,
                           c.findings AS findings, collect(DISTINCT e.name)[..15] AS entities
                    LIMIT $limit
                    """
                    params = {"limit": limit, "level": level, "allowed_sources": allowed_sources}
                else:
                    cypher = """
                    MATCH (c:Community)
                    WHERE ($level IS NULL OR c.level = $level)
                    OPTIONAL MATCH (c)<-[:BELONGS_TO]-(e:Entity)
                    RETURN c.id AS id, c.title AS title, c.level AS level, c.summary AS summary,
                           c.findings AS findings, collect(DISTINCT e.name)[..15] AS entities
                    LIMIT $limit
                    """
                    params = {"limit": limit, "level": level}

                return [dict(r) for r in session.run(cypher, **params)]
            except Exception as exc:
                logger.debug("Community summary query failed or not initialized: %s", exc)
                return []

    def entity_neighbors(self, entity: str, limit: int = 10, allowed_sources: list[str] | None = None) -> list[dict]:
        if allowed_sources is not None:
            if not allowed_sources:
                return []
            cypher = """
            MATCH (e:Entity {name: $entity})-[r:RELATED]-(o:Entity)
            WHERE any(src IN coalesce(r.sources, []) WHERE src IN $allowed_sources)
            RETURN e.name AS entity, r.type AS relation, o.name AS other
            LIMIT $limit
            """
            params = {"entity": entity, "limit": limit, "allowed_sources": allowed_sources}
        else:
            cypher = """
            MATCH (e:Entity {name: $entity})-[r:RELATED]-(o:Entity)
            RETURN e.name AS entity, r.type AS relation, o.name AS other
            LIMIT $limit
            """
            params = {"entity": entity, "limit": limit}
        with self.driver.session() as session:
            return [dict(r) for r in self._execute_query_safe(session, cypher, query_type="entity_neighbors", **params)]

    def entity_paths_2hop(self, entity: str, limit: int = 8, allowed_sources: list[str] | None = None) -> list[dict]:
        if allowed_sources is not None:
            if not allowed_sources:
                return []
            cypher = """
            MATCH p=(e:Entity {name: $entity})-[r1:RELATED]-(m:Entity)-[r2:RELATED]-(o:Entity)
            WHERE o.name <> e.name
              AND any(src IN coalesce(r1.sources, []) WHERE src IN $allowed_sources)
              AND any(src IN coalesce(r2.sources, []) WHERE src IN $allowed_sources)
            RETURN e.name AS source, r1.type AS rel1, m.name AS middle, r2.type AS rel2, o.name AS target
            LIMIT $limit
            """
            params = {"entity": entity, "limit": limit, "allowed_sources": allowed_sources}
        else:
            cypher = """
            MATCH p=(e:Entity {name: $entity})-[r1:RELATED]-(m:Entity)-[r2:RELATED]-(o:Entity)
            WHERE o.name <> e.name
            RETURN e.name AS source, r1.type AS rel1, m.name AS middle, r2.type AS rel2, o.name AS target
            LIMIT $limit
            """
            params = {"entity": entity, "limit": limit}
        with self.driver.session() as session:
            return [
                dict(r) for r in self._execute_query_safe(session, cypher, query_type="entity_paths_2hop", **params)
            ]

    def delete_by_source(self, source: str) -> int:
        count_cypher = """
        MATCH ()-[r:RELATED]-()
        WHERE $source IN coalesce(r.sources, [])
        RETURN count(r) AS rel_count
        """
        trim_relation_cypher = """
        MATCH ()-[r:RELATED]-()
        WHERE $source IN coalesce(r.sources, [])
        WITH r, [x IN coalesce(r.sources, []) WHERE x <> $source] AS remain_sources
        FOREACH (_ IN CASE WHEN size(remain_sources) = 0 THEN [1] ELSE [] END | DELETE r)
        FOREACH (_ IN CASE WHEN size(remain_sources) > 0 THEN [1] ELSE [] END |
            SET r.sources = remain_sources,
                r.source_descriptions = [d IN coalesce(r.source_descriptions, []) WHERE split(d, $sep)[0] <> $source])
        """
        # Derived from the source's triplets, so they go with it. Both must be
        # removed before the orphan sweep below: a BELONGS_TO or MENTIONS edge
        # would otherwise keep a deleted document's entities alive.
        community_cypher = """
        MATCH (c:Community)
        WHERE $source IN coalesce(c.sources, [])
        DETACH DELETE c
        """
        chunk_cypher = """
        MATCH (k:Chunk {source: $source})
        DETACH DELETE k
        """
        delete_cypher = """
        MATCH (s:Source {name: $source})
        OPTIONAL MATCH (e:Entity)-[m:MENTIONED_IN]->(s)
        DELETE m
        WITH s
        DETACH DELETE s
        WITH 1 as _
        MATCH (e:Entity)
        WHERE NOT (e)--()
        DELETE e
        """

        def _tx_work(tx):
            rel_count = tx.run(count_cypher, source=source).single()
            count = int(rel_count["rel_count"]) if rel_count else 0
            tx.run(trim_relation_cypher, source=source, sep=_DESC_SEP)
            tx.run(community_cypher, source=source)
            tx.run(chunk_cypher, source=source)
            tx.run(delete_cypher, source=source)
            return count

        with self.driver.session() as session:
            if hasattr(session, "execute_write"):
                return int(session.execute_write(_tx_work))
            if hasattr(session, "write_transaction"):
                return int(session.write_transaction(_tx_work))
            return int(_tx_work(session))

    def batch_entity_neighbors(
        self, entities: list[str], limit_per_entity: int = 10, allowed_sources: list[str] | None = None
    ) -> dict[str, list[dict]]:
        """
        Batch fetch neighbors for multiple entities in a single query (eliminates N+1 problem).

        Args:
            entities: List of entity names to fetch neighbors for
            limit_per_entity: Max neighbors per entity
            allowed_sources: Optional source filtering

        Returns:
            Dict mapping entity name to list of neighbor dicts

        Performance: 3 entities with 10 neighbors each = 1 query instead of 3 queries
        """
        if not entities:
            return {}

        if allowed_sources is not None:
            if not allowed_sources:
                return {e: [] for e in entities}
            cypher = """
            UNWIND $entities AS entity_name
            MATCH (e:Entity {name: entity_name})-[r:RELATED]-(o:Entity)
            WHERE any(src IN coalesce(r.sources, []) WHERE src IN $allowed_sources)
            WITH e.name AS entity, r.type AS relation, o.name AS other
            ORDER BY entity, relation, other
            RETURN entity, collect({relation: relation, other: other})[..$limit] AS neighbors
            """
            params = {"entities": entities, "limit": limit_per_entity, "allowed_sources": allowed_sources}
        else:
            cypher = """
            UNWIND $entities AS entity_name
            MATCH (e:Entity {name: entity_name})-[r:RELATED]-(o:Entity)
            WITH e.name AS entity, r.type AS relation, o.name AS other
            ORDER BY entity, relation, other
            RETURN entity, collect({relation: relation, other: other})[..$limit] AS neighbors
            """
            params = {"entities": entities, "limit": limit_per_entity}

        result = {}
        with self.driver.session() as session:
            for record in self._execute_query_safe(session, cypher, query_type="entity_neighbors", **params):
                entity_name = record["entity"]
                neighbors = record["neighbors"]
                # Flatten the neighbor structure
                result[entity_name] = [
                    {"entity": entity_name, "relation": n["relation"], "other": n["other"]} for n in neighbors
                ]

        # Ensure all requested entities are in result (even if no neighbors found)
        for entity in entities:
            if entity not in result:
                result[entity] = []

        return result

    def batch_entity_paths_2hop(
        self, entities: list[str], limit_per_entity: int = 8, allowed_sources: list[str] | None = None
    ) -> dict[str, list[dict]]:
        """
        Batch fetch 2-hop paths for multiple entities in a single query (eliminates N+1 problem).

        Args:
            entities: List of entity names to fetch paths for
            limit_per_entity: Max paths per entity
            allowed_sources: Optional source filtering

        Returns:
            Dict mapping entity name to list of path dicts

        Performance: 3 entities with 8 paths each = 1 query instead of 3 queries
        """
        if not entities:
            return {}

        if allowed_sources is not None:
            if not allowed_sources:
                return {e: [] for e in entities}
            cypher = """
            UNWIND $entities AS entity_name
            MATCH p=(e:Entity {name: entity_name})-[r1:RELATED]-(m:Entity)-[r2:RELATED]-(o:Entity)
            WHERE any(src IN coalesce(r1.sources, []) WHERE src IN $allowed_sources)
              AND any(src IN coalesce(r2.sources, []) WHERE src IN $allowed_sources)
              AND o.name <> e.name
            WITH e.name AS source, r1.type AS rel1, m.name AS middle, r2.type AS rel2, o.name AS target
            ORDER BY source, middle, target
            RETURN source, collect({rel1: rel1, middle: middle, rel2: rel2, target: target})[..$limit] AS paths
            """
            params = {"entities": entities, "limit": limit_per_entity, "allowed_sources": allowed_sources}
        else:
            cypher = """
            UNWIND $entities AS entity_name
            MATCH p=(e:Entity {name: entity_name})-[r1:RELATED]-(m:Entity)-[r2:RELATED]-(o:Entity)
            WHERE o.name <> e.name
            WITH e.name AS source, r1.type AS rel1, m.name AS middle, r2.type AS rel2, o.name AS target
            ORDER BY source, middle, target
            RETURN source, collect({rel1: rel1, middle: middle, rel2: rel2, target: target})[..$limit] AS paths
            """
            params = {"entities": entities, "limit": limit_per_entity}

        result = {}
        with self.driver.session() as session:
            for record in self._execute_query_safe(session, cypher, query_type="entity_paths_2hop", **params):
                source_name = record["source"]
                paths = record["paths"]
                # Flatten the path structure
                result[source_name] = [
                    {
                        "source": source_name,
                        "rel1": p["rel1"],
                        "middle": p["middle"],
                        "rel2": p["rel2"],
                        "target": p["target"],
                    }
                    for p in paths
                ]

        # Ensure all requested entities are in result (even if no paths found)
        for entity in entities:
            if entity not in result:
                result[entity] = []

        return result
