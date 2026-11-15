# data/evals/ — Evaluation Benchmark & Harness

This folder contains the quantitative evaluation dataset and runner for EKIP.

## Components

- **`eval_set.json`**: 24 curated test cases across 4 question categories:
  - `answerable` (10 items) — fully documented in `sample_docs/`
  - `unanswerable` (6 items) — out-of-scope queries (safety tests)
  - `ambiguous` (4 items) — partially documented edge cases
  - `action` (4 items) — action requests dispatched to bounded agent
- **`run_eval.py`**: Automated offline evaluation runner that measures accuracy, safety rejection, citation matching, and latency. Results are saved as timestamped JSON files (`results_YYYYMMDD_HHMMSS.json`).

## Running the Benchmark

```bash
uv run python data/evals/run_eval.py
```
