import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from harness.models import Result

_TIERS = ("easy", "medium", "hard")


@dataclass
class ReportRow:
  easy: int = 0
  easy_passed: int = 0
  medium: int = 0
  medium_passed: int = 0
  hard: int = 0
  hard_passed: int = 0
  total_latency_s: float = 0.0
  total_cost_usd: float = 0.0
  priced: int = 0
  total_attempts: int = 0
  failed_ids: list[str] = field(default_factory=list)

  def add(self, result: Result) -> None:
    if result.tier in _TIERS:
      setattr(self, result.tier, getattr(self, result.tier) + 1)
      if result.passed:
        passed_field = f"{result.tier}_passed"
        setattr(self, passed_field, getattr(self, passed_field) + 1)
    if not result.passed:
      self.failed_ids.append(result.case_id)
    self.total_latency_s += result.latency_s
    self.total_attempts += result.attempts
    if result.cost_usd is not None:
      self.total_cost_usd += result.cost_usd
      self.priced += 1

  @property
  def total(self) -> int:
    return self.easy + self.medium + self.hard

  @property
  def passed(self) -> int:
    return self.easy_passed + self.medium_passed + self.hard_passed


def _ratio(passed: int, total: int) -> str:
  if total == 0:
    return ""
  return f"{passed}/{total}"


def _significant_figures(text: str) -> int:
  digits = text.lstrip("-").replace(".", "").lstrip("0")
  return len(digits)


def _average(total: float, count: int) -> str:
  if count == 0:
    return ""
  return f"{total / count:.3f}"


def _average_cost(total: float, count: int) -> str:
  if count == 0:
    return ""
  value = total / count
  fixed = f"{value:.3f}"
  if value != 0 and _significant_figures(fixed) < 3:
    return f"{value:.2e}"
  return fixed


def report(results_path: Path, output_path: Path) -> None:
  grouped: dict[tuple[str, str], ReportRow] = defaultdict(ReportRow)
  for line in Path(results_path).read_text().splitlines():
    if line.strip():
      result = Result(**json.loads(line))
      grouped[(result.config, result.model)].add(result)

  header = [
    "Config", "Model", "Accuracy", "Easy", "Med", "Hard",
    "Avg cost", "Avg latency", "Avg attempts",
  ]
  table = []
  failures = []
  for (config, model), row in grouped.items():
    table.append([
      config,
      model,
      _ratio(row.passed, row.total),
      _ratio(row.easy_passed, row.easy),
      _ratio(row.medium_passed, row.medium),
      _ratio(row.hard_passed, row.hard),
      _average_cost(row.total_cost_usd, row.priced),
      _average(row.total_latency_s, row.total),
      _average(row.total_attempts, row.total),
    ])
    if row.failed_ids:
      failures.append(f"{config} / {model}: {', '.join(row.failed_ids)}")

  markdown = [
    "| " + " | ".join(header) + " |",
    "| " + " | ".join("---" for _ in header) + " |",
  ]
  markdown.extend("| " + " | ".join(cells) + " |" for cells in table)
  if failures:
    markdown.extend(["", "Failed case ids:", *[f"- {item}" for item in failures]])
  text = "\n".join(markdown) + "\n"

  output_path = Path(output_path)
  output_path.parent.mkdir(parents=True, exist_ok=True)
  output_path.write_text(text)
  csv_path = output_path.with_suffix(".csv")
  with csv_path.open("w", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(header)
    writer.writerows(table)
