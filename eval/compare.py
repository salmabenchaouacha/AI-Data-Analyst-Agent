"""Execution accuracy: does the predicted query return the same data as the gold query?

Comparison is deliberately tolerant to things that don't change the business answer:
  - column names / aliases are ignored
  - row order is ignored unless the question is marked `ordered: true`
  - floats are compared after rounding (2 decimals by default)
  - extra columns in the prediction are allowed (e.g. an id next to the name),
    as long as every gold column can be matched to a predicted column.
"""
from __future__ import annotations

from collections import Counter
from itertools import permutations
from typing import Any, Sequence

Row = Sequence[Any]


def _norm(v: Any, ndigits: int) -> Any:
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        f = round(float(v), ndigits)
        return 0.0 if f == 0 else f
    try:
        return round(float(v), ndigits)  # Decimal or numeric string
    except (TypeError, ValueError):
        return str(v).strip().lower()


def _norm_rows(rows: list[Row], ndigits: int) -> list[tuple]:
    return [tuple(_norm(v, ndigits) for v in r) for r in rows]


def _columns(rows: list[tuple], n: int) -> list[tuple]:
    return [tuple(r[i] for r in rows) for i in range(n)]


def results_match(gold: list[Row], pred: list[Row], ordered: bool = False, ndigits: int = 2) -> bool:
    g, p = _norm_rows(gold, ndigits), _norm_rows(pred, ndigits)
    if len(g) != len(p):
        return False
    if not g:
        return True
    gw, pw = len(g[0]), len(p[0])
    if pw < gw:
        return False

    if not ordered:  # sort rows with a type-safe key so column matching is order-independent
        key = lambda r: tuple((x is None, str(type(x)), x if x is not None else 0) for x in r)  # noqa: E731
        g, p = sorted(g, key=key), sorted(p, key=key)

    if gw == pw and (g == p if ordered else Counter(g) == Counter(p)):
        return True

    # try to map each gold column onto a distinct predicted column
    gcols, pcols = _columns(g, gw), _columns(p, pw)
    if gw > 6:  # avoid combinatorial blow-up
        return False
    for perm in permutations(range(pw), gw):
        chosen = [pcols[i] for i in perm]
        if ordered:
            if chosen == gcols:
                return True
        else:
            if Counter(zip(*chosen)) == Counter(zip(*gcols)):
                return True
    return False
