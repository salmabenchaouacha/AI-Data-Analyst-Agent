"""LLM-as-a-judge + a deterministic numeric grounding check.

Two complementary signals:
  1. numbers_grounded(): every number written in the answer must appear in the
     SQL result (deterministic, cheap, no LLM bias) -> detects hallucinated numbers.
  2. judge(): an LLM classifies the failure (wrong join, wrong filter, ...) by
     comparing predicted SQL/result to the gold SQL/result.
"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

ErrorCategory = Literal[
    "none",
    "wrong_filter",          # missing/extra WHERE condition (e.g. forgot status = 'completed')
    "wrong_join",            # missing, extra or incorrect join / join key
    "wrong_aggregation",     # SUM vs AVG vs COUNT, COUNT vs COUNT DISTINCT...
    "wrong_column",          # used the wrong measure/dimension (amount_paid instead of net_amount)
    "wrong_grouping_or_ordering",
    "wrong_time_range",
    "sql_error",             # never produced an executable query
    "hallucinated_number",   # SQL fine but the answer states numbers not in the result
    "no_answer",             # refused / said no data while data exists
    "other",
]


class Judgement(BaseModel):
    answer_correct: bool = Field(description="Does the final natural-language answer correctly answer the question, given the gold result?")
    error_category: ErrorCategory = Field(description="Main root cause if incorrect, 'none' otherwise.")
    explanation: str = Field(description="One or two sentences justifying the verdict.")


JUDGE_SYSTEM = """You evaluate a Text-to-SQL agent. You receive the business question, the GOLD
SQL and result (ground truth), and the agent's SQL, result and final answer.
Decide if the final answer is correct with respect to the gold result (small rounding
differences are fine; extra context is fine). If it is wrong, pick the single main root
cause by comparing the agent SQL with the gold SQL. For a question with no data
(gold result NULL/empty), the answer is correct only if it says there is no data."""

JUDGE_USER = """Question: {question}

GOLD SQL:
{gold_sql}
GOLD RESULT: {gold_result}

AGENT SQL:
{pred_sql}
AGENT RESULT: {pred_result}
EXECUTION MATCH (automatic): {exec_match}
NUMBERS IN ANSWER GROUNDED IN AGENT RESULT (automatic): {grounded}

AGENT ANSWER:
{answer}"""

_NUM = re.compile(r"(?<![\w.])-?\d[\d,\s]*(?:\.\d+)?%?")


def extract_numbers(text: str) -> list[float]:
    nums = []
    for m in _NUM.findall(text or ""):
        raw = m.replace(",", "").replace(" ", "").rstrip("%")
        try:
            nums.append(float(raw))
        except ValueError:
            continue
    return nums


def numbers_grounded(answer: str, result: dict[str, Any] | None, question: str = "") -> tuple[bool, list[float]]:
    """Return (ok, ungrounded_numbers). Years and numbers quoted from the question are ignored."""
    cells = []
    if result:
        for row in result["rows"]:
            for v in row:
                if isinstance(v, (int, float)):
                    cells.append(float(v))
                elif isinstance(v, str):
                    cells += extract_numbers(v)
    allowed_from_question = set(extract_numbers(question))
    bad = []
    for n in extract_numbers(answer):
        if n in allowed_from_question or (1900 <= n <= 2100 and n.is_integer()):
            continue
        if not any(abs(n - c) <= max(0.01, 0.005 * abs(c)) for c in cells):
            bad.append(n)
    return (not bad, bad)


def judge(llm, *, question, gold_sql, gold_result, pred_sql, pred_result, answer,
          exec_match, grounded) -> Judgement:
    def fmt(r):
        if r is None:
            return "(no result)"
        return f"columns={r['columns']} rows={r['rows'][:20]}"

    from langchain_core.messages import HumanMessage, SystemMessage

    structured = llm.with_structured_output(Judgement)
    return structured.invoke([
        SystemMessage(JUDGE_SYSTEM),
        HumanMessage(JUDGE_USER.format(
            question=question, gold_sql=gold_sql.strip(), gold_result=fmt(gold_result),
            pred_sql=pred_sql or "(none)", pred_result=fmt(pred_result),
            exec_match=exec_match, grounded=grounded, answer=answer)),
    ])
