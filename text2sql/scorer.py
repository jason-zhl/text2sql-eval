from collections import Counter

from harness.models import Score
from text2sql.db import execute


def _normalize_cell(value):
  if isinstance(value, bool):
    return int(value)
  if isinstance(value, float):
    rounded = round(value, 4)
    if rounded.is_integer():
      return int(rounded)
    return rounded
  return value


def _normalize_rows(rows: list[tuple]) -> list[tuple]:
  return [tuple(_normalize_cell(cell) for cell in row) for row in rows]


class SQLScorer:
  def score(self, output: str, expected: str, order_matters: bool = False) -> Score:
    got_rows, _got_columns, got_error = execute(output)
    if got_error:
      return Score(passed=False, error=got_error)

    expected_rows, _expected_columns, expected_error = execute(expected)
    if expected_error:
      return Score(passed=False, error=expected_error)

    got = _normalize_rows(got_rows)
    expected_norm = _normalize_rows(expected_rows)
    if order_matters:
      matched = got == expected_norm
    else:
      matched = Counter(got) == Counter(expected_norm)
    return Score(passed=matched, error=None if matched else "result mismatch")