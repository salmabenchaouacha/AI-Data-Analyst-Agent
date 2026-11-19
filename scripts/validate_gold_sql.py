"""Sanity check: every gold query of the test set runs on the warehouse and returns rows."""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.db import run_query  # noqa: E402

qs = yaml.safe_load((ROOT / "eval" / "questions.yaml").read_text())["questions"]
failed = 0
for q in qs:
    try:
        r = run_query(q["gold_sql"], max_rows=5)
        print(f"{q['id']} OK  {r['rows'][:3]}")
    except Exception as e:  # noqa: BLE001
        failed += 1
        print(f"{q['id']} FAIL {e}")
print(f"\n{len(qs) - failed}/{len(qs)} gold queries OK")
sys.exit(1 if failed else 0)
