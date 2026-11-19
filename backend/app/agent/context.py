"""Builds the database context given to the LLM.

Four levels, compared in the ablation study:
  tables_only           table names only
  schema                + columns and types (information_schema)
  schema_docs           + dbt model/column descriptions (manifest.json)
  schema_docs_examples  + few-shot question/SQL pairs
"""
from __future__ import annotations

import json
from functools import lru_cache

import yaml

from ..config import ALLOWED_TABLES, CONTEXT_MODES, settings
from ..db import table_columns


@lru_cache
def _dbt_docs() -> dict[str, dict]:
    """{model: {"description": str, "columns": {col: description}}} from manifest.json."""
    if not settings.dbt_manifest.exists():
        raise FileNotFoundError(
            f"{settings.dbt_manifest} not found. Run `dbt docs generate` (or `dbt build`) first."
        )
    manifest = json.loads(settings.dbt_manifest.read_text())
    docs = {}
    for node in manifest["nodes"].values():
        if node["resource_type"] == "model" and node["name"] in ALLOWED_TABLES:
            docs[node["name"]] = {
                "description": " ".join(node.get("description", "").split()),
                "columns": {c: " ".join(v.get("description", "").split())
                            for c, v in node.get("columns", {}).items()},
            }
    return docs


@lru_cache
def _examples() -> str:
    data = yaml.safe_load(settings.examples_path.read_text())["examples"]
    return "\n\n".join(f"Question: {e['question']}\nSQL:\n{e['sql'].strip()}" for e in data)


@lru_cache
def build_context(mode: str) -> str:
    if mode not in CONTEXT_MODES:
        raise ValueError(f"unknown context mode {mode!r}, expected one of {CONTEXT_MODES}")

    if mode == "tables_only":
        return "Available tables: " + ", ".join(ALLOWED_TABLES)

    cols = table_columns()
    docs = _dbt_docs() if mode in ("schema_docs", "schema_docs_examples") else {}

    parts = []
    for table in ALLOWED_TABLES:
        lines = [f"TABLE {table}"]
        if table in docs and docs[table]["description"]:
            lines.append(f"  -- {docs[table]['description']}")
        for col, typ in cols.get(table, []):
            desc = docs.get(table, {}).get("columns", {}).get(col, "")
            lines.append(f"  {col} {typ}" + (f"  -- {desc}" if desc else ""))
        parts.append("\n".join(lines))
    context = "\n\n".join(parts)

    if mode == "schema_docs_examples":
        context += "\n\nEXAMPLE QUERIES\n" + _examples()
    return context
