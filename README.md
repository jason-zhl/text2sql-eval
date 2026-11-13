# text2sql-eval

An execution-based eval harness for a small text-to-SQL agent. Each question goes to an LLM, the generated SQL runs against the [Chinook](https://github.com/lerocha/chinook-database) SQLite database, and the result set is compared against the result of a hand-written gold query. The output is a table of accuracy, cost, and latency per prompt configuration and model.

The harness is meant to be reusable: `harness/` knows nothing about SQL, so the same runner and reporting can score a different task by swapping in new cases and a new scorer.

## Results

Latest run: 10 cases, `gemini-3.5-flash-lite`.

| Config | Model | Accuracy | Easy | Med | Hard | Avg cost ($) | Avg latency (s) | Avg attempts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bare | gemini-3.5-flash-lite | 1/10 | 1/3 | 0/3 | 0/4 | 1.15e-04 | 0.922 | 1.000 |
| schema | gemini-3.5-flash-lite | 9/10 | 3/3 | 3/3 | 3/4 | 5.05e-04 | 0.901 | 1.000 |
| retry | gemini-3.5-flash-lite | 9/10 | 3/3 | 3/3 | 3/4 | 5.08e-04 | 0.830 | 1.000 |

Findings so far:

- **The schema is what matters most.** Without it, the model guesses table and column names and gets 1 of 10 right. With the full DDL in the system prompt, it gets 9 of 10, at roughly 4x the cost per question.
- **Retry gave no benefit on this set.** Every query from the `schema` config executed on the first try, so the retry loop never fired (average attempts is 1.0). The only failure, `invoice_total_by_genre`, is a wrong answer rather than a SQL error, and retry deliberately skips wrong answers (see below).
- Ten cases is too few to separate configs with any confidence. These numbers are a smoke test, not a benchmark.

## Quick start

Requires Python 3.10+ and a Gemini API key.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "GEMINI_API_KEY=your-key" > .env
python run.py
```

`run.py` runs every config against every case in `text2sql/cases.yaml`, prints any failures as they happen, and writes:

- `results/<run_id>/results.jsonl`: one row per (config, case) with the generated SQL, pass/fail, error, attempts, tokens, cost, and latency.
- `report.md` and `report.csv`: the summary table above, plus the failed case IDs per config.

The model and config list are currently set in `run.py`; there are no command-line flags yet.

## Configurations

Defined in `text2sql/configs.py`. Every system prompt names SQLite as the dialect so the model avoids Postgres-only syntax such as `ILIKE` or `DATE_TRUNC`.

| Config | System prompt | Attempts |
| --- | --- | --- |
| `bare` | Instructions only, no schema | 1 |
| `schema` | Instructions plus the `CREATE TABLE` DDL for every table | 1 |
| `retry` | Same as `schema` | up to 3 |

In the `retry` config, if the generated SQL fails to execute, the SQLite error goes back to the model as a follow-up message and it gets another try. A query that runs but returns the wrong rows is not retried, because the model gets no useful signal from "wrong answer" without seeing the expected result.

## Scoring rules

Most false failures in text-to-SQL evals come from edge cases in how results are compared, so the rules are spelled out here. The implementation is in `text2sql/scorer.py`.

1. **SQL extraction.** If the model's reply contains a fenced code block, the first block is used. Otherwise the whole reply is treated as SQL.
2. **Execution.** Both the generated and gold SQL run through `text2sql/db.py`. The database is opened read-only, only one statement is allowed per query, and queries are aborted after 2 seconds. If the generated SQL errors, the case fails and the error is recorded.
3. **Column names are ignored.** Rows are compared by position, so aliases do not matter.
4. **Types are normalized.** SQLite is loosely typed, so values are normalized before comparison: floats are rounded to 4 decimal places, floats with integer values become integers (`1.0` matches `1`), and booleans become integers.
5. **Row order is ignored by default.** Results are compared as multisets, so duplicate rows still count. The scorer also supports an order-sensitive comparison, but cases cannot request it yet.

## Project layout

```
harness/                    # Reusable, task-agnostic
  models.py                 # Case, Config, Score, Result, and the Scorer protocol
  llm.py                    # LLMClient protocol, GeminiClient, $/Mtok pricing, 429 backoff
  runner.py                 # Runs configs x cases, handles retry, writes JSONL
  reporting.py              # Aggregates JSONL into the markdown and CSV report
text2sql/                   # Task-specific
  cases.yaml                # Questions with gold SQL and an easy/medium/hard tier
  configs.py                # bare / schema / retry
  db.py                     # Read-only SQLite execution with a timeout
  scorer.py                 # Result-set comparison
  Chinook_Sqlite.sqlite     # The Chinook sample database
run.py                      # Entry point
```

### Adding a case

Append an entry to `text2sql/cases.yaml`. Gold SQL must use SQLite syntax (`strftime`, `||`, `CAST(... AS REAL)` for decimal division).

```yaml
  - id: brazil_customer_count
    tier: easy
    text: "How many customers are from Brazil?"
    expected: "SELECT COUNT(*) FROM Customer WHERE Country = 'Brazil'"
```

### Reusing the harness for another task

The runner depends only on `Case`, `Config`, an `LLMClient`, and a `Scorer` with a `score(output, expected) -> Score` method. To evaluate a different task, write a new scorer and case file and pass them to `Runner`; nothing in `harness/` needs to change.

## Cost tracking

Cost is computed locally from the token counts the API returns and the per-model rates in `_PRICE_PER_MTOK` in `harness/llm.py`. Output tokens include thinking tokens. Check the rates against the [Gemini pricing page](https://ai.google.dev/gemini-api/docs/pricing) before relying on the cost numbers. To use a new model, add its rates there first; the client will not start without them.

## Limitations and next steps

- Only 10 cases and 1 model so far. The goal is 30 to 50 cases and at least 2 models.
- Cases run one at a time, with no concurrency and no cache of LLM responses, so every rerun pays the full cost again.
- There are no CLI flags for choosing configs, models, or the case file.
- The `order_matters` option is not yet read from `cases.yaml`.
- Tracing (planned: Langfuse) is not implemented.
- Prompt caching for the schema block is not enabled.
