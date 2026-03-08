# Rubric Calibration Plan

Calibrate the reward function before using it for training.
The measuring instrument must be accurate before we trust its signal.

---

## Problem

Current rubric checks parse natural language ("North total revenue is 555000")
and search for numbers in output files. This is brittle:

- **False positive:** number appears somewhere unrelated → pass
- **False negative:** formatting ($555,000 or 555000.0) → fail even if correct
- **Rounding:** 111666 vs 111666.67 → unclear

## Solution: Structured Deterministic Checks

Replace NL criterion strings with explicit unit-test specs:

```json
{
  "check": "cell_value",
  "file": "output/report.xlsx",
  "sheet": "Summary",
  "lookup": {"Region": "North"},
  "column": "Total Revenue",
  "expected": 555000,
  "tolerance": 1,
  "score": 2
}
```

Check types:
- `file_exists` — deliverable exists at path
- `sheet_exists` — Excel workbook has named sheet
- `cell_value` — specific cell value matches (with tolerance)
- `contains_text` — text file contains string
- `row_count` — table has expected row count
- `column_exists` — sheet/CSV has named column

---

## Calibration Loop

### Step 1: Build real dataset (8-10 tasks)

Diverse tasks covering:
- Excel multi-sheet analysis (sums, averages, groupby)
- CSV variance/comparison analysis
- Text report generation
- Multi-file cross-referencing
- Chart/summary deliverables

Each task has: reference files, prompt, structured checks, expected deliverables.

### Step 2: Run gold model on all tasks

```bash
python scripts/eval_rubric.py --model Qwen/Qwen2.5-72B-Instruct --max-steps 15
```

Gold model: `Qwen/Qwen2.5-72B-Instruct` (72B, strong function calling, on HF router).

For each task:
1. Run full episode (reset → tools → submit)
2. Save workspace snapshot (output files)
3. Save trace (all tool calls)
4. Record rubric results per criterion

### Step 3: Audit rubric accuracy

For each task, the eval script prints:
- Task prompt
- What the agent produced (output file contents)
- Each criterion: PASS/FAIL + what was expected vs found
- Human verdict column (you fill in: correct/incorrect)

Output: `traces/rubric_audit.json` with per-task, per-criterion results.

### Step 4: Fix and repeat

- Fix false positives/negatives in the check functions
- Re-run checks on saved workspaces (no API calls needed)
- Repeat until 0 disagreements on gold model runs

### Step 5: Validate with weak model

Run same tasks with `Qwen/Qwen3-8B`:
- Compare rubric scores (should be lower than gold model)
- Compare process scores (may be similar or worse)
- Decide reward weights based on actual score distributions

### Step 6: Lock rewards, train

Freeze reward function. Start GRPO training.

---

## Models

| Role | Model | Where |
|------|-------|-------|
| Gold (eval) | `Qwen/Qwen2.5-72B-Instruct` | HF router |
| Weak (training target) | `Qwen/Qwen3-8B` | HF router / local vLLM |
| Alternative gold | `Qwen/Qwen3-235B-A22B` | HF router |

---

## Files

| File | Purpose |
|------|---------|
| `data/tasks/task_manifest.json` | All tasks with structured checks |
| `scripts/create_test_data.py` | Generate tasks + reference files |
| `scripts/eval_rubric.py` | Run gold model + audit loop |
| `finbench_env/server/rewards.py` | Structured check executor |
| `traces/rubric_audit.json` | Audit results per run |
