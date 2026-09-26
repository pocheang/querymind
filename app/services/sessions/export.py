"""Session export: the document a session is written out as.

Only the export half lives here. Import is parsed and validated by the route
(`app/api/routes/sessions/export.py`), which writes through the caller's own
history store and metadata service. This module used to carry a second, parallel
import path (`import_from_json` / `_file` / `_zip`) plus file and multi-session
ZIP writers; none had a caller, and `import_from_json` wrote to a
`_metadata_store` attribute neither metadata backend has, so it would have
raised the first time anything reached it. Deleted 2026-09-26.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.services.sessions.metadata import (
    SessionMetadata,
    SessionMetadataService,
    utc_now,
)

__all__ = [
    "ExportFormat",
    "ConflictStrategy",
    "EXPORT_VERSION",
    "ExportedSession",
    "SessionExportService",
]


# ============================================================================
# Constants
# ============================================================================

EXPORT_VERSION = "1.0"


# ============================================================================
# Type Definitions
# ============================================================================

ExportFormat = Literal["json", "zip"]
ConflictStrategy = Literal["skip", "overwrite", "rename"]


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class ExportedSession:
    """Exported session data."""

    session_id: str
    metadata: dict[str, Any]
    messages: list[dict[str, Any]]
    export_version: str = EXPORT_VERSION
    exported_at: str = ""

    def __post_init__(self):
        if not self.exported_at:
            self.exported_at = utc_now().isoformat()


# ============================================================================
# Session Export Service
# ============================================================================


class SessionExportService:
    """Builds the export document for one session."""

    def __init__(self, metadata_service: SessionMetadataService):
        # Required: the fallback was a process-wide in-memory metadata service,
        # which no route ever reached and which a second worker would not share.
        self.metadata_service = metadata_service

    def export_session(
        self,
        session_id: str,
        messages: list[dict[str, Any]] | None = None,
    ) -> ExportedSession:
        """
        Export a single session.

        Args:
            session_id: Session identifier
            messages: Optional message history

        Returns:
            ExportedSession

        Metadata is optional. A session created by asking a question has none --
        `POST /sessions` writes to the history store and the only writers of
        `SessionMetadata` are the edit-metadata endpoint and import -- so
        requiring it here meant **exporting an ordinary session answered
        500 "Export failed"**, which is every session a user has not tagged by
        hand. The messages are the substance; tags and a category are decoration
        the user may never have added.
        """
        metadata = self.metadata_service.get_metadata(session_id)
        metadata_dict = self._metadata_to_dict(metadata) if metadata is not None else self._absent_metadata(session_id)

        # Create exported session
        return ExportedSession(
            session_id=session_id,
            metadata=metadata_dict,
            messages=messages or [],
        )

    def _absent_metadata(self, session_id: str) -> dict[str, Any]:
        """The metadata block for a session that has none.

        Same keys as `_metadata_to_dict`, so an importer reads one shape whether
        or not the exporter had anything to put in it. Empty rather than
        invented: `created_at` is not guessed from the export time, because a
        re-import would then carry a date the session never had.
        """

        return {
            "session_id": session_id,
            "tags": [],
            "category": None,
            "description": None,
            "auto_tags": [],
            "created_at": None,
            "updated_at": None,
            "query_count": 0,
            "last_query_at": None,
        }

    def _metadata_to_dict(self, metadata: SessionMetadata) -> dict[str, Any]:
        """Convert SessionMetadata to dict."""
        return {
            "session_id": metadata.session_id,
            "tags": metadata.tags,
            "category": metadata.category,
            "description": metadata.description,
            "auto_tags": metadata.auto_tags,
            "created_at": metadata.created_at.isoformat(),
            "updated_at": metadata.updated_at.isoformat(),
            "query_count": metadata.query_count,
            "last_query_at": metadata.last_query_at.isoformat() if metadata.last_query_at else None,
        }
