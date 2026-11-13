import os
from dotenv import load_dotenv
import time
from dataclasses import dataclass
from typing import Protocol
from google import genai
from google.genai import errors, types

_QUOTA_RETRIES = 5

@dataclass
class LLMResult:
  text: str
  input_tokens: int
  output_tokens: int
  cached_tokens: int
  cache_write_tokens: int
  latency_s: float
  model: str


# Paid standard tier, $ per million tokens: input, output (including thinking), cached input.
# https://ai.google.dev/gemini-api/docs/pricing
_PRICE_PER_MTOK = {
  "gemini-3.5-flash-lite": (0.30, 2.50, 0.03),
}


load_dotenv()
class LLMClient(Protocol):
  def complete(self, system: str, messages: list[dict]) -> LLMResult: ...
  def cost(self, result: LLMResult) -> float: ...

def _retry_delay_s(details) -> float:
  payloads = [details] if isinstance(details, dict) else []
  error = details.get("error") if isinstance(details, dict) else None
  if isinstance(error, dict):
    payloads.append(error)
  for payload in payloads:
    items = payload.get("details")
    if not isinstance(items, list):
      continue
    for item in items:
      if isinstance(item, dict) and str(item.get("@type", "")).endswith("RetryInfo"):
        return _parse_seconds(item.get("retryDelay")) + 1
  return 31


def _parse_seconds(delay) -> float:
  text = str(delay).strip()
  if text.endswith("s"):
    text = text[:-1]
  try:
    return float(text)
  except ValueError:
    return 30


_ROLES = {"user": "user", "assistant": "model", "model": "model"}
class GeminiClient:
  def __init__(self, model: str, max_tokens: int = 1024):
    try:
      input_price, output_price, cached_price = _PRICE_PER_MTOK[model]
    except KeyError:
      known = ", ".join(sorted(_PRICE_PER_MTOK))
      raise ValueError(f"No $/Mtok rates for {model}. Known models: {known}")
    self.model = model
    self.input_per_mtok = input_price
    self.output_per_mtok = output_price
    self.cached_per_mtok = cached_price
    self.max_tokens = max_tokens
    self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

  def cost(self, result: LLMResult) -> float:
    return (
      result.input_tokens * self.input_per_mtok
      + result.output_tokens * self.output_per_mtok
      + result.cached_tokens * self.cached_per_mtok
    ) / 1_000_000
  def complete(self, system: str, messages: list[dict]) -> LLMResult:
    contents = [
      {"role": _ROLES[message["role"]], "parts": [{"text": message["content"]}]}
      for message in messages
    ]
    response = None
    started = time.perf_counter()
    for attempt in range(1, _QUOTA_RETRIES + 1):
      started = time.perf_counter()
      try:
        response = self._client.models.generate_content(
          model=self.model,
          contents=contents,
          config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=self.max_tokens,
          ),
        )
        break
      except errors.ClientError as exc:
        if exc.code != 429 or attempt == _QUOTA_RETRIES:
          raise
        delay = _retry_delay_s(exc.details)
        print(f"Rate limited, waiting {delay:.0f}s", flush=True)
        time.sleep(delay)
    usage = response.usage_metadata
    cached = usage.cached_content_token_count or 0
    prompt = usage.prompt_token_count or 0
    return LLMResult(
      text=response.text or "",
      input_tokens=max(prompt - cached, 0),
      output_tokens=(usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0),
      cached_tokens=cached,
      cache_write_tokens=0,
      latency_s=time.perf_counter() - started,
      model=self.model,
    )
