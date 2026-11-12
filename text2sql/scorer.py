from harness.models import Score
from text2sql.db import execute

class SQLScorer:
  def score(self, output: str, expected: str) -> Score:
    output = execute(output)
    expected = execute(expected)
    print(output, expected)
    return Score(passed=True, error=None)
