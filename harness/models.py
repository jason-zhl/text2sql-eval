from dataclasses import dataclass
from typing import Protocol


@dataclass
class Case:
  id: str
  tier: str
  text: str
  expected: str

@dataclass(frozen=True)
class Config:
  name: str
  system_prompt: str
  max_attempts: int = 1

@dataclass
class Output:
  rows: int
  columns: int
  error: str | None

@dataclass
class Score:
  passed: bool
  error: str | None

@dataclass
class Result:
  case_id: str
  tier: str
  config: str
  model: str
  passed: bool
  error: str | None
  attempts: int
  input_tokens: int
  output_tokens: int
  cached_tokens: int
  cost_usd: float | None
  latency_s: float
  generated_sql: str

class Scorer(Protocol):
  def score(self, output: str, expected: str) -> Score: ...
