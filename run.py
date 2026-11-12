from harness.llm import GeminiClient
from text2sql.db import execute
import text2sql.configs
from text2sql.scorer import SQLScorer
from harness.runner import Runner

from pathlib import Path
import yaml
from harness.models import Case

def load_cases(path: str) -> list[Case]:
  data = yaml.safe_load(Path(path).read_text())
  return [Case(**item) for item in data["cases"]]

if __name__ == "__main__":
  client = GeminiClient("gemini-3.5-flash-lite")
  runner = Runner(config=text2sql.configs.CONFIGS["schema"], llm=client, scorer=SQLScorer())
  cases = load_cases("text2sql/cases.yaml")
  print(runner.run(cases[0]))