from harness.models import Config
from text2sql.db import execute

_INSTRUCTIONS = "You write a single SQLite query and nothing else."


def _schema_ddl() -> str:
  rows, _columns, error = execute(
    "SELECT sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
  )
  if error:
    raise RuntimeError(error)
  return "\n\n".join(row[0] for row in rows)


def _with_schema(instructions: str) -> str:
  return f"{instructions}\n\nDatabase schema:\n{_schema_ddl()}"


bare = Config(name="bare", system_prompt=_INSTRUCTIONS)
schema = Config(name="schema", system_prompt=_with_schema(_INSTRUCTIONS))
retry = Config(name="retry", system_prompt=schema.system_prompt, max_attempts=3)

CONFIGS = {config.name: config for config in (bare, schema, retry)}
