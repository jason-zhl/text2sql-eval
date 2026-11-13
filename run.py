from pathlib import Path

import yaml

import text2sql.configs
from harness.llm import GeminiClient
from harness.models import Case
from harness.runner import Runner
from text2sql.scorer import SQLScorer


def load_cases(path: str) -> list[Case]:
  data = yaml.safe_load(Path(path).read_text())
  return [Case(**item) for item in data["cases"]]


if __name__ == "__main__":
  client = GeminiClient("gemini-3.5-flash-lite")
  runner = Runner(
    configs=list(text2sql.configs.CONFIGS.values()),
    llm=client,
    scorer=SQLScorer(),
  )
  cases = load_cases("text2sql/cases.yaml")
  for result in runner.run(cases):
    print(f"{result.config} {result.case_id}: {result.passed} {result.error}")
  print(runner.results_path)
