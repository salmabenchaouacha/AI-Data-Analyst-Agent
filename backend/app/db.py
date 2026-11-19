"""Read-only access to the DuckDB warehouse built by dbt."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import duckdb

from .config import ALLOWED_TABLES, settings


@contextmanager
def connect():
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    try:
        yield con
    finally:
        con.close()


def run_query(sql: str, max_rows: int | None = None) -> dict[str, Any]:
    """Execute SQL and return {"columns": [...], "rows": [[...]], "truncated": bool}."""
    max_rows = max_rows or settings.max_rows
    with connect() as con:
        cur = con.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = cur.fetchmany(max_rows + 1)
    truncated = len(rows) > max_rows
    rows = [[_jsonable(v) for v in r] for r in rows[:max_rows]]
    return {"columns": columns, "rows": rows, "truncated": truncated}


def explain(sql: str) -> None:
    """Raise if DuckDB cannot plan the query (unknown column, type error...)."""
    with connect() as con:
        con.execute(f"EXPLAIN {sql}")


def table_columns() -> dict[str, list[tuple[str, str]]]:
    """{table: [(column, type), ...]} for the allowed marts."""
    placeholders = ", ".join("?" for _ in ALLOWED_TABLES)
    with connect() as con:
        rows = con.execute(
            f"""
            select table_name, column_name, data_type
            from information_schema.columns
            where table_schema = ? and table_name in ({placeholders})
            order by table_name, ordinal_position
            """,
            [settings.marts_schema, *ALLOWED_TABLES],
        ).fetchall()
    out: dict[str, list[tuple[str, str]]] = {}
    for t, c, typ in rows:
        out.setdefault(t, []).append((c, typ))
    return out


def _jsonable(v: Any) -> Any:
    if v is None or isinstance(v, (int, float, str, bool)):
        return v
    try:  # Decimal
        return float(v)
    except (TypeError, ValueError):
        return str(v)  # dates, timestamps
