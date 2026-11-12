import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "Chinook_Sqlite.sqlite"
TIMEOUT_S = 2.0

def execute(sql: str) -> tuple[list[tuple], list[str], str | None]:
  uri = f"{DB_PATH.as_uri()}?mode=ro"
  # Initialize connection
  try:
    conn = sqlite3.connect(uri, uri=True)
  except sqlite3.Error as exc:
    return [], [], str(exc)

  started = time.monotonic()
  def abort_if_slow() -> int:
    return 1 if time.monotonic() - started > TIMEOUT_S else 0
  conn.set_progress_handler(abort_if_slow, 10_000)

  try:
    cursor = conn.execute(sql)
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    rows = cursor.fetchall()
    return rows, columns, None
  except sqlite3.Error as exc:
    return [], [], str(exc)
  finally:
    conn.close()
