"""Embedded Table SQL execution engine supporting DuckDB with SQLite fallback."""

from __future__ import annotations

import logging
import re
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    import duckdb  # type: ignore

    _HAS_DUCKDB = True
except ImportError:
    duckdb = None  # type: ignore
    _HAS_DUCKDB = False

_SQL_KEYWORDS = frozenset(
    {
        "select",
        "from",
        "where",
        "order",
        "group",
        "by",
        "having",
        "limit",
        "join",
        "left",
        "right",
        "inner",
        "outer",
        "on",
        "as",
        "case",
        "when",
        "then",
        "else",
        "end",
        "table",
        "column",
        "view",
        "index",
        "distinct",
        "all",
        "and",
        "or",
        "not",
        "in",
        "is",
        "null",
        "like",
        "between",
        "union",
        "intersect",
        "except",
        "set",
        "reset",
        "call",
        "load",
        "use",
    }
)

_FORBIDDEN_KEYWORDS = frozenset(
    {
        "drop",
        "delete",
        "update",
        "insert",
        "alter",
        "create",
        "attach",
        "detach",
        "pragma",
        "exec",
        "execute",
        "vacuum",
        "reindex",
        "replace",
        "grant",
        "revoke",
        "load_extension",
        "install",
        "copy",
        "export",
        "import",
        "checkpoint",
        "set",
        "reset",
        "call",
        "load",
        "use",
    }
)

# Table functions and settings accessors that reach outside the one registered
# table: files on the server, other databases, environment variables, or a
# nested statement (`query('...')`). The DuckDB connection is also opened with
# external access disabled; this list is the second, engine-independent layer.
_FORBIDDEN_FUNCTIONS = frozenset(
    {
        "read_text",
        "read_blob",
        "read_csv",
        "read_csv_auto",
        "read_json",
        "read_json_auto",
        "read_json_objects",
        "read_ndjson",
        "read_ndjson_auto",
        "read_parquet",
        "parquet_scan",
        "parquet_metadata",
        "parquet_schema",
        "glob",
        "sqlite_scan",
        "sqlite_attach",
        "postgres_scan",
        "postgres_attach",
        "mysql_scan",
        "iceberg_scan",
        "delta_scan",
        "query",
        "query_table",
        "getenv",
        "current_setting",
        "duckdb_settings",
        "duckdb_extensions",
        "readfile",
        "writefile",
    }
)

# A single-quoted SQL string literal ('' escapes a quote). Blanked before the
# keyword scan so `WHERE status = 'deleted'` is not refused as a DELETE and a
# semicolon inside a literal is not taken for a second statement.
_STRING_LITERAL_RE = re.compile(r"'(?:[^']|'')*'")


@dataclass
class TableQueryResult:
    """Structured result of executing a SQL query on a table."""

    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: float
    markdown_table: str
    engine_used: str  # "duckdb" or "sqlite"
    error: str | None = None


@dataclass
class TableSchema:
    """Schema descriptor for a registered in-memory table."""

    table_name: str
    original_headers: list[str]
    sql_columns: list[str]
    column_types: dict[str, str]  # sql_col -> "INTEGER" | "REAL" | "TEXT"
    column_mapping: dict[str, str]  # original_header -> sql_col
    reverse_mapping: dict[str, str]  # sql_col -> original_header
    row_count: int
    created_at: float = field(default_factory=time.time)


def _sanitize_column_name(header: str, index: int, existing: set[str]) -> str:
    """Sanitize a raw table header into a valid, safe SQL column identifier."""
    cleaned = str(header or "").strip()
    if not cleaned:
        cleaned = f"col_{index + 1}"

    # Replace spaces, punctuation and special symbols with underscores
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "_", cleaned).strip("_").lower()
    if not slug:
        slug = f"col_{index + 1}"

    # If starts with a digit or matches a reserved SQL keyword, prefix with col_.
    # Forbidden words too: a column named "query" or "set" would otherwise make
    # every statement that mentions it fail validation.
    if slug[0].isdigit() or slug in _SQL_KEYWORDS or slug in _FORBIDDEN_KEYWORDS or slug in _FORBIDDEN_FUNCTIONS:
        slug = f"col_{slug}"

    candidate = slug
    counter = 1
    while candidate in existing:
        candidate = f"{slug}_{counter}"
        counter += 1

    existing.add(candidate)
    return candidate


_CURRENCY_PREFIX = frozenset("$￥€£¥")
_CURRENCY_SUFFIX = frozenset("$￥€£¥%")


def _strip_currency_affixes(text: str) -> str:
    """Leading currency symbols and trailing currency / percent signs, with whitespace.

    What `^[$￥€£¥\\s]+|[$￥€£¥\\s%]+$` did, as two scans: the trailing branch of the
    regex could start at every offset inside a run of spaces and fail at the end
    of it (python:S8786). Identical output over 30,000 generated values.
    """
    start, end = 0, len(text)
    while start < end and (text[start] in _CURRENCY_PREFIX or text[start].isspace()):
        start += 1
    while end > start and (text[end - 1] in _CURRENCY_SUFFIX or text[end - 1].isspace()):
        end -= 1
    return text[start:end]


def _clean_and_parse_value(val: Any) -> tuple[Any, str]:
    """Parse a single cell into a typed scalar and inferred type.

    Returns:
        (parsed_value, type_name) where type_name in ("INTEGER", "REAL", "TEXT", "NULL")
    """
    if val is None:
        return None, "NULL"

    s = str(val).strip()
    if not s or s.lower() in ("nan", "null", "none", "n/a", "-", "--"):
        return None, "NULL"

    # Accounting negative format: (1,234.56) -> -1234.56
    is_accounting_negative = s.startswith("(") and s.endswith(")")
    if is_accounting_negative:
        s = s[1:-1].strip()

    # Strip currency symbols and percent signs
    stripped_num = _strip_currency_affixes(s)
    # Remove thousand separators: 1,234,567.89 -> 1234567.89
    if re.match(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$", stripped_num):
        stripped_num = stripped_num.replace(",", "")

    # Try Integer
    try:
        parsed_int = int(stripped_num)
        if is_accounting_negative:
            parsed_int = -parsed_int
        return parsed_int, "INTEGER"
    except (ValueError, TypeError):
        pass

    # Try Float
    try:
        parsed_float = float(stripped_num)
        if is_accounting_negative:
            parsed_float = -parsed_float
        return parsed_float, "REAL"
    except (ValueError, TypeError):
        pass

    return s, "TEXT"


class TableEngine:
    """In-memory analytical SQL engine supporting DuckDB with SQLite fallback."""

    def __init__(self, prefer_duckdb: bool = True) -> None:
        self.prefer_duckdb = prefer_duckdb and _HAS_DUCKDB
        self.engine_name = "duckdb" if self.prefer_duckdb else "sqlite"
        self._duck_conn: Any = None
        self._sqlite_conn: sqlite3.Connection | None = None
        self._schemas: dict[str, TableSchema] = {}
        # Neither connection may be used from two threads at once, and queries
        # arrive through asyncio.to_thread.
        self._lock = threading.Lock()
        self._init_connection()

    def _init_connection(self) -> None:
        if self.prefer_duckdb:
            try:
                # No filesystem, network or extension access: a statement can
                # reach the registered table and nothing else on this machine.
                # DuckDB refuses to re-enable this while the database is open.
                self._duck_conn = duckdb.connect(":memory:", config={"enable_external_access": False})
                logger.debug("TableEngine initialized with in-memory DuckDB")
                return
            except Exception as e:
                logger.warning(f"DuckDB initialization failed, falling back to SQLite: {e}")
                self.prefer_duckdb = False
                self.engine_name = "sqlite"

        self._sqlite_conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._sqlite_conn.row_factory = sqlite3.Row
        logger.debug("TableEngine initialized with in-memory SQLite")

    def register_table(
        self,
        table_id: str,
        headers: list[str],
        rows: list[list[Any]],
        table_name: str | None = None,
    ) -> TableSchema:
        """Register tabular data as an in-memory SQL table.

        Args:
            table_id: Unique table ID
            headers: Raw column headers
            rows: Raw table rows
            table_name: Optional custom SQL table name (alphanumeric)

        Returns:
            TableSchema describing the registered table
        """
        # 1. Determine safe table name
        clean_id = re.sub(r"\W", "_", table_id)
        safe_name = table_name or f"tbl_{clean_id}"
        safe_name = safe_name.lower().strip("_")
        if not safe_name or safe_name[0].isdigit():
            safe_name = f"tbl_{safe_name}"

        # 2. Sanitize column names and track mappings
        used_cols: set[str] = set()
        sql_columns: list[str] = []
        col_mapping: dict[str, str] = {}
        rev_mapping: dict[str, str] = {}

        for idx, h in enumerate(headers):
            c_name = _sanitize_column_name(h, idx, used_cols)
            sql_columns.append(c_name)
            col_mapping[h] = c_name
            rev_mapping[c_name] = h

        num_cols = len(sql_columns)

        # 3. Clean rows and infer column types
        type_votes: list[dict[str, int]] = [{"INTEGER": 0, "REAL": 0, "TEXT": 0, "NULL": 0} for _ in range(num_cols)]
        cleaned_rows: list[list[Any]] = []

        for row in rows:
            c_row: list[Any] = []
            for col_i in range(num_cols):
                raw_cell = row[col_i] if col_i < len(row) else None
                c_val, val_type = _clean_and_parse_value(raw_cell)
                c_row.append(c_val)
                type_votes[col_i][val_type] += 1
            cleaned_rows.append(c_row)

        column_types: dict[str, str] = {}
        for col_i, col_name in enumerate(sql_columns):
            votes = type_votes[col_i]
            non_null = votes["INTEGER"] + votes["REAL"] + votes["TEXT"]
            if non_null == 0:
                column_types[col_name] = "TEXT"
            elif votes["INTEGER"] / non_null >= 0.8:
                column_types[col_name] = "INTEGER"
            elif (votes["INTEGER"] + votes["REAL"]) / non_null >= 0.8:
                column_types[col_name] = "REAL"
            else:
                column_types[col_name] = "TEXT"

        # 4. Create in-memory table
        col_defs = ", ".join(f'"{col}" {column_types[col]}' for col in sql_columns)
        create_sql = f'CREATE TABLE IF NOT EXISTS "{safe_name}" ({col_defs})'

        placeholders = ", ".join(["?"] * num_cols)
        insert_sql = f'INSERT INTO "{safe_name}" VALUES ({placeholders})'
        with self._lock:
            if self.prefer_duckdb and self._duck_conn is not None:
                self._duck_conn.execute(f'DROP TABLE IF EXISTS "{safe_name}"')
                self._duck_conn.execute(create_sql)
                self._duck_conn.executemany(insert_sql, cleaned_rows)
            else:
                assert self._sqlite_conn is not None
                with self._sqlite_conn:
                    self._sqlite_conn.execute(f'DROP TABLE IF EXISTS "{safe_name}"')
                    self._sqlite_conn.execute(create_sql)
                    self._sqlite_conn.executemany(insert_sql, cleaned_rows)

        schema = TableSchema(
            table_name=safe_name,
            original_headers=headers,
            sql_columns=sql_columns,
            column_types=column_types,
            column_mapping=col_mapping,
            reverse_mapping=rev_mapping,
            row_count=len(cleaned_rows),
        )
        self._schemas[safe_name] = schema
        self._schemas[table_id] = schema
        return schema

    def validate_sql(self, sql: str) -> tuple[bool, str | None]:
        """Validate that SQL is strictly a read-only SELECT or WITH statement."""
        # Strip comments
        cleaned = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL).strip()

        if not cleaned:
            return False, "Query cannot be empty"

        # Check for multiple statements separated by semicolon. Literals are
        # blanked first, so a semicolon or keyword inside a string is data.
        trimmed = _STRING_LITERAL_RE.sub("''", cleaned).rstrip(";").strip()
        if ";" in trimmed:
            return False, "Multiple SQL statements are not permitted"

        tokens = [t.lower() for t in re.findall(r"\b[a-zA-Z_]+\b", trimmed)]
        if not tokens:
            return False, "Invalid SQL query"

        # First keyword must be SELECT, WITH, or EXPLAIN
        if tokens[0] not in ("select", "with"):
            return False, f"Only SELECT or WITH queries are permitted, got: '{tokens[0]}'"

        # Check for forbidden DDL / DML / control keywords
        for tok in tokens:
            if tok in _FORBIDDEN_KEYWORDS:
                return False, f"Forbidden keyword in query: '{tok}'"
            if tok in _FORBIDDEN_FUNCTIONS:
                return False, f"Forbidden function in query: '{tok}'"

        return True, None

    def execute_query(
        self,
        sql: str,
        max_rows: int = 100,
    ) -> TableQueryResult:
        """Safely execute a SQL query against registered tables.

        Args:
            sql: SQL statement
            max_rows: Maximum rows to return (auto-injects LIMIT if absent)

        Returns:
            TableQueryResult with structured rows, columns, and markdown representation
        """
        start_time = time.perf_counter()
        is_valid, err = self.validate_sql(sql)
        if not is_valid:
            return TableQueryResult(
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=0.0,
                markdown_table="",
                engine_used=self.engine_name,
                error=err,
            )

        # Enforce LIMIT if not explicitly present
        run_sql = sql.rstrip(";").strip()
        if not re.search(r"\blimit\s+\d+", run_sql, re.IGNORECASE):
            run_sql = f"{run_sql} LIMIT {max_rows}"

        try:
            with self._lock:
                if self.prefer_duckdb and self._duck_conn is not None:
                    cursor = self._duck_conn.execute(run_sql)
                    raw_cols = [desc[0] for desc in cursor.description] if cursor.description else []
                    fetched_rows = cursor.fetchall()
                else:
                    # Not an assert: this sits inside `except Exception`, which
                    # would swallow an AssertionError (python:S5779), and asserts
                    # vanish under -O anyway.
                    if self._sqlite_conn is None:
                        raise RuntimeError("TableEngine has no open connection")
                    cursor = self._sqlite_conn.cursor()
                    cursor.execute(run_sql)
                    raw_cols = [desc[0] for desc in cursor.description] if cursor.description else []
                    fetched_rows = cursor.fetchall()

            rows = [list(r) for r in fetched_rows]
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Render markdown table representation
            md = self._render_markdown_table(raw_cols, rows)

            return TableQueryResult(
                columns=raw_cols,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=round(elapsed_ms, 2),
                markdown_table=md,
                engine_used=self.engine_name,
                error=None,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning(f"SQL execution error: {e}")
            return TableQueryResult(
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=round(elapsed_ms, 2),
                markdown_table="",
                engine_used=self.engine_name,
                error=str(e),
            )

    def _render_markdown_table(self, columns: list[str], rows: list[list[Any]]) -> str:
        if not columns:
            return ""
        header_line = "| " + " | ".join(columns) + " |"
        sep_line = "| " + " | ".join(["---"] * len(columns)) + " |"
        data_lines = []
        for r in rows:
            cells = [str(c if c is not None else "") for c in r]
            data_lines.append("| " + " | ".join(cells) + " |")
        return "\n".join([header_line, sep_line] + data_lines)

    def get_schema(self, table_id_or_name: str) -> TableSchema | None:
        return self._schemas.get(table_id_or_name)

    def list_tables(self) -> list[TableSchema]:
        seen = set()
        result = []
        for schema in self._schemas.values():
            if schema.table_name not in seen:
                seen.add(schema.table_name)
                result.append(schema)
        return result
