"""Table indexing for multi-modal RAG."""

from __future__ import annotations

import logging

from app.services.multimodal.models import TableContent

logger = logging.getLogger(__name__)


class TableExtractor:
    """Index a table that ingestion has already parsed.

    The pdfplumber and PyMuPDF extractors that used to live here had no callers:
    `_index_tables` reads the loader's rendered markdown through
    `_table_from_markdown`, which is what keeps a table's header attached to it.
    The pandas dependency went with them.
    """

    def format_table_as_text(self, table: TableContent, max_rows: int = 15) -> str:
        """Format table as plain text for indexing.

        Args:
            table: TableContent object
            max_rows: Maximum rows to include

        Returns:
            Text representation
        """
        try:
            lines = []

            sheet = str(table.metadata.get("sheet", "") or "")
            if sheet:
                lines.append(f"Sheet: {sheet}")
            lines.append(f"Columns ({len(table.headers)}): " + " | ".join(table.headers))
            lines.append(f"Total Rows: {len(table.rows)}")
            lines.append("-" * 50)

            # Add rows (limited)
            for _i, row in enumerate(table.rows[:max_rows]):
                row_str = " | ".join([str(cell) for cell in row])
                lines.append(row_str)

            # Add truncation notice
            if len(table.rows) > max_rows:
                lines.append(f"... ({len(table.rows) - max_rows} more rows)")

            return "\n".join(lines)

        except Exception:
            logger.exception("Error formatting table as text")
            return f"[Table {table.table_id}]"

    def index_entry(self, table: TableContent) -> tuple[str, dict]:
        """The text this table is embedded as, and the metadata stored beside it.

        Separate from `index_table` so ingestion can embed the text before taking
        the index lock and hand the vector back to `index_table` under it.
        """

        text_to_index = f"{table.summary}\n\n{self.format_table_as_text(table)}"
        return text_to_index, {
            "doc_id": table.doc_id,
            "document_id": table.metadata.get("document_id", table.doc_id),
            "tenant_id": table.metadata.get("tenant_id", "shared"),
            # Absent keys do not match `$eq`, so a table indexed
            # without these is invisible rather than public.
            "owner_user_id": table.metadata.get("owner_user_id", ""),
            "visibility": table.metadata.get("visibility", "private"),
            "version": table.metadata.get("version", 1),
            "page_number": table.page_number,
            "source": table.metadata.get("source", table.doc_id),
            "type": "table",
            "table_id": table.table_id,
            "sheet": str(table.metadata.get("sheet", "") or ""),
            "columns": ", ".join(table.headers)[:500],
            "num_rows": table.metadata.get("num_rows", len(table.rows)),
            "num_cols": table.metadata.get("num_cols", len(table.headers)),
            "extraction_method": table.metadata.get("extraction_method", "unknown"),
        }

    def index_table(
        self,
        table: TableContent,
        collection_name: str = "table_summaries",
        *,
        embedding: list[float] | None = None,
    ) -> None:
        """Index table content in the vector database; embeds it here unless `embedding` is given.

        Synchronous: it awaits nothing, and its caller is document ingestion,
        which runs in a worker thread where an event loop must not be driven.
        """
        try:
            from app.retrievers.stores.vector import upsert_texts

            text_to_index, metadata = self.index_entry(table)
            upsert_texts(
                collection_name,
                [table.table_id],
                [text_to_index],
                [metadata],
                None if embedding is None else [embedding],
            )
            logger.info(f"Indexed table {table.table_id} in collection {collection_name}")
        except Exception:
            logger.exception(f"Error indexing table {table.table_id}")
            raise
