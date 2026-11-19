"""FastAPI backend: `uvicorn app.main:app --reload` from the backend/ folder."""
from __future__ import annotations

import json
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import CONTEXT_MODES, ROOT, settings

app = FastAPI(title="AI Data Analyst Agent")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])

RESULTS_DIR = ROOT / "eval" / "results"


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    context_mode: Literal[CONTEXT_MODES] = "schema_docs"  # type: ignore[valid-type]
    agent: Literal["langgraph", "baseline"] = "langgraph"


@app.get("/api/health")
def health():
    return {"status": "ok", "warehouse": settings.duckdb_path.exists()}


@app.get("/api/config")
def config():
    return {"context_modes": list(CONTEXT_MODES), "agent_model": settings.agent_model,
            "agents": ["langgraph", "baseline"]}


@app.post("/api/ask")
def ask(req: AskRequest):
    if req.agent == "baseline":
        from .agent.baseline import run_baseline
        out = run_baseline(req.question)
        result = None
        if out["sql"]:
            from .db import run_query
            try:
                result = run_query(out["sql"])
            except Exception:  # noqa: BLE001
                result = None
        return {**out, "result": result, "context_mode": None, "attempts": None}

    from .agent.graph import run_agent
    state = run_agent(req.question, req.context_mode)
    return {
        "question": req.question,
        "context_mode": req.context_mode,
        "sql": state.get("sql"),
        "result": state.get("result"),
        "answer": state.get("answer"),
        "attempts": state.get("attempts"),
        "error": state.get("error"),
        "trace": state.get("trace", []),
    }


@app.get("/api/eval/runs")
def eval_runs():
    if not RESULTS_DIR.exists():
        return []
    return sorted((p.stem for p in RESULTS_DIR.glob("*.json")), reverse=True)


@app.get("/api/eval/runs/{run_id}")
def eval_run(run_id: str):
    path = RESULTS_DIR / f"{run_id}.json"
    if not path.exists() or path.parent != RESULTS_DIR:
        raise HTTPException(404, "run not found")
    return json.loads(path.read_text())
