import os
from dotenv import load_dotenv
import time
from dataclasses import dataclass
from typing import Protocol
from google import genai
from google.genai import types

@dataclass
class LLMResult:
  text: str
  input_tokens: int
  output_tokens: int
  cached_tokens: int
  cache_write_tokens: int
  latency_s: float
  model: str


load_dotenv()
class LLMClient(Protocol):
  def complete(self, system: str, messages: list[dict]) -> LLMResult: ...

_ROLES = {"user": "user", "assistant": "model", "model": "model"}
class GeminiClient:
  def __init__(self, model: str, max_tokens: int = 1024):
    self.model = model
    self.max_tokens = max_tokens
    self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
  def complete(self, system: str, messages: list[dict]) -> LLMResult:
    contents = [
      {"role": _ROLES[message["role"]], "parts": [{"text": message["content"]}]}
      for message in messages
    ]
    started = time.perf_counter()
    response = self._client.models.generate_content(
      model=self.model,
      contents=contents,
      config=types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=self.max_tokens,
      ),
    )
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
