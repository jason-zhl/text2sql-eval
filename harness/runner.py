import json
import uuid
from dataclasses import asdict
from pathlib import Path

from harness.llm import LLMClient
from harness.models import Case, Config, Result, Scorer


class Runner:
  def __init__(self, configs: list[Config], llm: LLMClient, scorer: Scorer):
    self.configs = configs
    self.llm = llm
    self.scorer = scorer
    self.run_id = uuid.uuid4().hex[:12]
    self.results_path = Path("results") / self.run_id / "results.jsonl"

  def run(self, cases: list[Case]) -> list[Result]:
    results = []
    for config in self.configs:
      for case in cases:
        result = self._run_case(config, case)
        self._write_row(result)
        results.append(result)
    return results

  def _run_case(self, config: Config, case: Case) -> Result:
    messages = [{"role": "user", "content": case.text}]
    input_tokens = 0
    output_tokens = 0
    cached_tokens = 0
    latency_s = 0.0
    generated_sql = ""
    model = ""
    score_passed = False
    score_error = None
    attempts = 0
    for attempt in range(1, config.max_attempts + 1):
      completion = self.llm.complete(config.system_prompt, messages)
      attempts = attempt
      input_tokens += completion.input_tokens
      output_tokens += completion.output_tokens
      cached_tokens += completion.cached_tokens
      latency_s += completion.latency_s
      generated_sql = completion.text
      model = completion.model
      score = self.scorer.score(completion.text, case.expected)
      score_passed = score.passed
      score_error = score.error
      if score.passed or score.error == "result mismatch" or attempt == config.max_attempts:
        break
      messages.append({"role": "assistant", "content": completion.text})
      messages.append({
        "role": "user",
        "content": f"SQLite error: {score.error}\nWrite a corrected SQLite query and nothing else.",
      })
    return Result(
      case_id=case.id,
      tier=case.tier,
      config=config.name,
      model=model,
      passed=score_passed,
      error=score_error,
      attempts=attempts,
      input_tokens=input_tokens,
      output_tokens=output_tokens,
      cached_tokens=cached_tokens,
      cost_usd=None,
      latency_s=latency_s,
      generated_sql=generated_sql,
    )

  def _write_row(self, result: Result) -> None:
    self.results_path.parent.mkdir(parents=True, exist_ok=True)
    with self.results_path.open("a") as handle:
      handle.write(json.dumps(asdict(result)) + "\n")
