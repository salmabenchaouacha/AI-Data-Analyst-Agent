"""Run the 30-question evaluation over several agent configurations.

Examples (from the repo root):
    python -m eval.run_eval                                   # all context modes + baseline
    python -m eval.run_eval --modes schema schema_docs --no-baseline
    python -m eval.run_eval --limit 5 --no-judge              # quick smoke test

Output: eval/results/<run_id>.json  (read by the frontend "Evaluation" page)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import CONTEXT_MODES, settings  # noqa: E402
from app.db import run_query  # noqa: E402
from app.llm import judge_llm  # noqa: E402

from eval.compare import results_match  # noqa: E402
from eval.judge import judge, numbers_grounded  # noqa: E402

RESULTS_DIR = ROOT / "eval" / "results"


def load_questions(limit: int | None):
    qs = yaml.safe_load((ROOT / "eval" / "questions.yaml").read_text())["questions"]
    return qs[:limit] if limit else qs


def run_one(config: str, q: dict, gold: dict, use_judge: bool) -> dict:
    t0 = time.perf_counter()
    try:
        if config == "baseline":
            from app.agent.baseline import run_baseline
            out = run_baseline(q["question"])
            pred_sql, answer, trace, attempts = out["sql"], out["answer"], out["trace"], None
            pred = None
            if pred_sql:
                try:
                    pred = run_query(pred_sql, max_rows=10_000)
                except Exception:  # noqa: BLE001
                    pred = None
        else:
            from app.agent.graph import run_agent
            st = run_agent(q["question"], context_mode=config)
            pred_sql, answer, trace, attempts = st.get("sql"), st.get("answer", ""), st.get("trace", []), st.get("attempts")
            pred = run_query(pred_sql, max_rows=10_000) if st.get("result") is not None else None
        crashed = None
    except Exception as e:  # noqa: BLE001
        pred_sql, answer, trace, attempts, pred, crashed = None, "", [], None, None, f"{type(e).__name__}: {e}"

    exec_match = pred is not None and results_match(gold["rows"], pred["rows"], ordered=q.get("ordered", False))
    grounded, ungrounded = numbers_grounded(answer, pred, q["question"])

    item = {
        "config": config, "id": q["id"], "question": q["question"], "tags": q["tags"],
        "gold_sql": q["gold_sql"].strip(), "pred_sql": pred_sql, "answer": answer,
        "attempts": attempts, "exec_match": exec_match,
        "numbers_grounded": grounded, "ungrounded_numbers": ungrounded,
        "crashed": crashed, "latency_s": round(time.perf_counter() - t0, 2), "trace": trace,
    }
    if use_judge:
        if pred_sql is None:
            item.update(answer_correct=False, error_category="sql_error", judge_explanation="No executable SQL.")
        else:
            j = judge(judge_llm(), question=q["question"], gold_sql=q["gold_sql"], gold_result=gold,
                      pred_sql=pred_sql, pred_result=pred, answer=answer,
                      exec_match=exec_match, grounded=grounded)
            category = j.error_category
            if exec_match and not grounded:
                category = "hallucinated_number"  # deterministic signal wins
            item.update(answer_correct=j.answer_correct, error_category=category,
                        judge_explanation=j.explanation)
    return item


def summarize(items: list[dict]) -> dict:
    by_config: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        by_config[it["config"]].append(it)

    summary = {}
    for config, its in by_config.items():
        n = len(its)
        tag_stats: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for it in its:
            for t in it["tags"]:
                tag_stats[t][0] += int(it["exec_match"])
                tag_stats[t][1] += 1
        summary[config] = {
            "n": n,
            "execution_accuracy": round(sum(i["exec_match"] for i in its) / n, 3),
            "answer_accuracy": (round(sum(i.get("answer_correct", False) for i in its) / n, 3)
                                if "answer_correct" in its[0] else None),
            "grounded_rate": round(sum(i["numbers_grounded"] for i in its) / n, 3),
            "avg_attempts": (round(sum(i["attempts"] or 0 for i in its) / n, 2)
                             if its[0]["attempts"] is not None else None),
            "avg_latency_s": round(sum(i["latency_s"] for i in its) / n, 2),
            "errors": dict(Counter(i.get("error_category", "n/a") for i in its
                                   if i.get("error_category") not in (None, "none"))),
            "accuracy_by_tag": {t: round(ok / tot, 3) for t, (ok, tot) in sorted(tag_stats.items())},
        }
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", nargs="+", default=list(CONTEXT_MODES), choices=CONTEXT_MODES)
    ap.add_argument("--no-baseline", action="store_true")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--run-name", default=None)
    args = ap.parse_args()

    questions = load_questions(args.limit)
    configs = list(args.modes) + ([] if args.no_baseline else ["baseline"])
    golds = {q["id"]: run_query(q["gold_sql"], max_rows=10_000) for q in questions}

    items = []
    for config in configs:
        for q in questions:
            it = run_one(config, q, golds[q["id"]], use_judge=not args.no_judge)
            items.append(it)
            mark = "OK " if it["exec_match"] else "KO "
            print(f"[{config:22}] {q['id']} {mark} {it.get('error_category', '')}")

    run_id = args.run_name or datetime.now().strftime("%Y%m%d-%H%M%S")
    payload = {
        "run_id": run_id, "created_at": datetime.now().isoformat(timespec="seconds"),
        "agent_model": settings.agent_model, "judge_model": None if args.no_judge else settings.judge_model,
        "configs": configs, "summary": summarize(items), "items": items,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"{run_id}.json").write_text(json.dumps(payload, indent=2, default=str))

    print("\nconfig                  exec_acc  answer_acc  grounded")
    for c, s in payload["summary"].items():
        ans = "-" if s["answer_accuracy"] is None else f"{s['answer_accuracy']:.0%}"
        print(f"{c:22}  {s['execution_accuracy']:>6.0%}    {ans:>8}    {s['grounded_rate']:>6.0%}")
    print(f"\nSaved -> eval/results/{run_id}.json")


if __name__ == "__main__":
    main()
