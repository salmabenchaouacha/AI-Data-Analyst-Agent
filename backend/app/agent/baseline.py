"""Baseline: LangChain's off-the-shelf ReAct SQL agent.

Used as a point of comparison for the LangGraph pipeline. It decides on its own
which tools to call (list tables, get schema, check query, run query), so it is
a black box: we only get the final answer and the last SQL it ran.
"""
from __future__ import annotations

from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase

from ..config import ALLOWED_TABLES, settings
from ..llm import agent_llm

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        db = SQLDatabase.from_uri(
            f"duckdb:///{settings.duckdb_path}",
            include_tables=list(ALLOWED_TABLES),
            sample_rows_in_table_info=3,
            engine_args={"connect_args": {"read_only": True}},
        )
        _agent = create_sql_agent(
            agent_llm(), db=db, agent_type="tool-calling",
            verbose=False, return_intermediate_steps=True, max_iterations=10,
        )
    return _agent


def run_baseline(question: str) -> dict:
    out = _get_agent().invoke({"input": question})
    # last SQL executed by the agent = last call to the sql_db_query tool
    sql = None
    trace = []
    for action, observation in out.get("intermediate_steps", []):
        trace.append({"node": action.tool, "input": str(action.tool_input)[:500],
                      "output": str(observation)[:300]})
        if action.tool == "sql_db_query":
            ti = action.tool_input
            sql = ti.get("query") if isinstance(ti, dict) else str(ti)
    return {"question": question, "sql": sql, "answer": out["output"], "trace": trace}
