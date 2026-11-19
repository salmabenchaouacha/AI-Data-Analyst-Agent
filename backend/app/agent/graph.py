"""LangGraph Text-to-SQL pipeline.

    START -> retrieve_context -> generate_sql -> validate_sql --ok--> execute_sql --ok--> answer -> END
                                     ^               | error             | error
                                     +---------------+-------------------+   (max_retries)

Every node appends an entry to state["trace"], so each failure can be attributed
to a precise step (generation, validation, execution, answer) during evaluation.
"""
from __future__ import annotations

import operator
import re
import time
from typing import Annotated, Any, TypedDict

import sqlglot
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from sqlglot import exp

from ..config import ALLOWED_TABLES, settings
from ..db import explain, run_query
from ..llm import agent_llm
from . import prompts
from .context import build_context


class AgentState(TypedDict, total=False):
    question: str
    context_mode: str
    context: str
    sql: str
    error: str | None
    attempts: int
    result: dict[str, Any] | None
    answer: str
    trace: Annotated[list[dict[str, Any]], operator.add]


# ---------- nodes ----------

def retrieve_context(state: AgentState) -> dict:
    t0 = time.perf_counter()
    ctx = build_context(state.get("context_mode", "schema_docs"))
    return {"context": ctx, "attempts": 0, "error": None,
            "trace": [_step("retrieve_context", t0, chars=len(ctx))]}


def generate_sql(state: AgentState) -> dict:
    t0 = time.perf_counter()
    feedback = ""
    if state.get("error"):
        feedback = prompts.FIX_FEEDBACK.format(sql=state.get("sql", ""), error=state["error"])
    msg = agent_llm().invoke([
        SystemMessage(prompts.SQL_SYSTEM.format(context=state["context"])),
        HumanMessage(prompts.SQL_USER.format(question=state["question"], feedback=feedback)),
    ])
    sql = _extract_sql(msg.content)
    attempt = state.get("attempts", 0) + 1
    return {"sql": sql, "attempts": attempt, "error": None,
            "trace": [_step("generate_sql", t0, attempt=attempt, sql=sql, is_fix=bool(feedback))]}


def validate_sql(state: AgentState) -> dict:
    """Static checks with sqlglot, then a DuckDB EXPLAIN (catches unknown columns)."""
    t0 = time.perf_counter()
    sql = state["sql"]
    try:
        tree = sqlglot.parse_one(sql, read="duckdb")
        if not isinstance(tree, (exp.Select, exp.Union, exp.With)) and tree.find(exp.Select) is None:
            raise ValueError("Only SELECT queries are allowed.")
        if any(isinstance(n, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create)) for n in tree.walk()):
            raise ValueError("Write operations are not allowed.")
        cte_names = {c.alias_or_name for c in tree.find_all(exp.CTE)}
        unknown = {t.name for t in tree.find_all(exp.Table)} - set(ALLOWED_TABLES) - cte_names
        if unknown:
            raise ValueError(f"Unknown table(s): {sorted(unknown)}. Allowed: {list(ALLOWED_TABLES)}")
        explain(sql)
        error = None
    except Exception as e:  # noqa: BLE001 - every error is fed back to the LLM
        error = f"{type(e).__name__}: {e}"
    return {"error": error, "trace": [_step("validate_sql", t0, ok=error is None, error=error)]}


def execute_sql(state: AgentState) -> dict:
    t0 = time.perf_counter()
    try:
        result = run_query(state["sql"])
        return {"result": result, "error": None,
                "trace": [_step("execute_sql", t0, ok=True, n_rows=len(result["rows"]))]}
    except Exception as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"
        return {"result": None, "error": error,
                "trace": [_step("execute_sql", t0, ok=False, error=error)]}


def answer(state: AgentState) -> dict:
    t0 = time.perf_counter()
    result = state.get("result")
    if result is None:
        text = f"I could not produce a valid query after {state.get('attempts', 0)} attempts. Last error: {state.get('error')}"
    else:
        rows = "\n".join(str(r) for r in result["rows"][:50]) or "(no rows)"
        if result.get("truncated"):
            rows += "\n... (truncated)"
        msg = agent_llm().invoke([
            SystemMessage(prompts.ANSWER_SYSTEM),
            HumanMessage(prompts.ANSWER_USER.format(
                question=state["question"], sql=state["sql"],
                columns=result["columns"], rows=rows)),
        ])
        text = msg.content.strip()
    return {"answer": text, "trace": [_step("answer", t0)]}


# ---------- routing ----------

def _route(state: AgentState) -> str:
    if state.get("error") is None:
        return "ok"
    return "retry" if state.get("attempts", 0) <= settings.max_retries else "give_up"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("retrieve_context", retrieve_context)
    g.add_node("generate_sql", generate_sql)
    g.add_node("validate_sql", validate_sql)
    g.add_node("execute_sql", execute_sql)
    g.add_node("answer", answer)

    g.add_edge(START, "retrieve_context")
    g.add_edge("retrieve_context", "generate_sql")
    g.add_edge("generate_sql", "validate_sql")
    g.add_conditional_edges("validate_sql", _route,
                            {"ok": "execute_sql", "retry": "generate_sql", "give_up": "answer"})
    g.add_conditional_edges("execute_sql", _route,
                            {"ok": "answer", "retry": "generate_sql", "give_up": "answer"})
    g.add_edge("answer", END)
    return g.compile()


graph = build_graph()


def run_agent(question: str, context_mode: str = "schema_docs") -> AgentState:
    return graph.invoke({"question": question, "context_mode": context_mode, "trace": []})


# ---------- helpers ----------

def _extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    sql = (m.group(1) if m else text).strip()
    return sql.rstrip(";").strip()


def _step(node: str, t0: float, **info) -> dict:
    return {"node": node, "ms": round((time.perf_counter() - t0) * 1000), **info}
