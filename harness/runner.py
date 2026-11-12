from harness.llm import LLMClient
from harness.models import Config, Case, Output, Score, Scorer

class Runner:
  def __init__(self, config: Config, llm: LLMClient, scorer: Scorer):
    self.config = config
    self.llm = llm
    self.scorer = scorer

  def run(self, case: Case) -> Score:
    result = self.llm.complete(
      self.config.system_prompt,
      [{"role": "user", "content": case.text}],
    )
    return self.scorer.score(result.text, case.expected)
