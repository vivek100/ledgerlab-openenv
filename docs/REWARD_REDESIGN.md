# Reward Function Redesign

## Problem

The original reward function uses `_convert_legacy_rubric()` to turn GDPval
natural-language rubric items into naive `contains_text` checks.  This is
fundamentally broken:

- Many checks produce **empty text** (criterion has no extractable string).
- String-presence in a file is not correctness — the right number in the wrong
  cell still passes.
- 60% of GDPval rubric items are numeric checks that cannot be expressed as
  substring search.

## Design Goals

1. **Deterministic** — same output file always produces the same score.
2. **Correct** — score correlates with actual analytical quality, not formatting.
3. **Fair** — tolerant of different column names, sheet names, row order.
4. **Fast** — computable in < 1 second (needed for RL rollouts).
5. **Partial credit** — not all-or-nothing; agent improves gradually.

## Architecture: Three Signals

### Signal 1 — Structural Checks (from rubric NL, easy patterns only)

Binary checks auto-parsed from the rubric text for unambiguous patterns:

| Check | Example rubric text |
|-------|-------------------|
| `file_exists_xlsx` | "Output is a single Excel workbook file with .xlsx extension" |
| `sheet_has_headers` | "First row includes headers: Role, Module, User Action..." |
| `row_count_range` | "Test cases total between 80 and 100 inclusive" |
| `column_all_blank` | "For every counted row, Actual Result cell is blank" |
| `column_all_filled` | "For every counted row, the Role cell is non-empty" |

These patterns are simple to regex-match and unambiguously correct.

### Signal 2 — Submission Fields (core correctness)

Each task defines 3–5 **structured verification fields** in the task schema.
At submit time the agent provides values for these fields.  We compare against
expected values derived from the gold deliverable.

Example for the PO Log task:

```json
{
  "submission_fields": [
    {
      "key": "june_total_shipped_cost",
      "type": "number",
      "description": "Total shipped dollar value at cost for June 2025 orders",
      "expected": 140008.20,
      "tolerance": 5.0
    },
    {
      "key": "june_row_count",
      "type": "integer",
      "description": "Number of POs that shipped in June 2025",
      "expected": 48
    },
    {
      "key": "short_shipped_total",
      "type": "number",
      "description": "Total dollar amount short-shipped across all June POs",
      "expected": 5210.60,
      "tolerance": 5.0
    }
  ]
}
```

Why this works:
- Agent must actually compute the right numbers to report them.
- Deterministic comparison (exact match or within tolerance).
- Cannot be gamed — agent must understand the data.
- Task-specific — defined once per task from gold file values.

### Signal 3 — File-vs-Summary Consistency

Cross-check: do the agent's submitted values match what is actually in its
output file?  For numeric fields, we extract all numeric values from the
output Excel file and check if the submitted value appears.

This catches:
- Agent reports correct number but file is wrong.
- Agent's file has correct data but agent reports wrong number.

## Reward Formula

```
structural_score  = passed_structural_checks / total_structural_checks
submission_score  = matched_fields / total_fields
consistency_score = consistent_fields / total_fields

rubric_score = (
    0.25 * structural_score
  + 0.60 * submission_score
  + 0.15 * consistency_score
)

total_reward = (
    0.50 * rubric_score
  + 0.25 * execution_quality   # (unchanged — trace-based checks)
  + 0.25 * memory_process      # (unchanged — trace-based checks)
  + 0.10 * depth_bonus         # (unchanged — uncapped)
)
```

Submission fields carry the highest weight (0.60 of rubric) because they are
the most direct measure of analytical correctness.

## What Changes

### Task Schema (`task_manifest.json`)

Each task gains a `submission_fields` array:

```json
{
  "task_id": "f841ddcf-...",
  "prompt": "...",
  "expected_deliverables": ["PO Log June Ships.xlsx"],
  "submission_fields": [
    {"key": "...", "type": "number", "description": "...", "expected": ..., "tolerance": ...},
    ...
  ],
  "rubric": [...]
}
```

### Agent Prompt

The task message shown to the agent appends:

```
When you call submit, include values for these verification fields:
- june_total_shipped_cost: Total shipped dollar value at cost for June 2025 orders
- june_row_count: Number of POs that shipped in June 2025
- short_shipped_total: Total dollar amount short-shipped across all June POs
```

### submit() Tool

Updated signature:

```python
def submit(deliverable_paths: str = "", submission_values: str = "") -> str:
```

Where `submission_values` is a JSON string like:
```json
{"june_total_shipped_cost": 140008.20, "june_row_count": 48, "short_shipped_total": 5210.60}
```

### rewards.py

Rewritten with:
- `compute_structural_checks()` — auto-parses easy rubric NL patterns
- `compute_submission_field_score()` — compares submitted values to expected
- `compute_consistency_score()` — cross-checks submitted values against file
- `compute_total_reward()` — combines all signals

### Execution Quality and Memory/Process

These stay unchanged — they measure agent behavior (explored workspace, read
refs, created notebooks, etc.) via the trace, not deliverable quality.

## Implementation Steps

1. Write `submission_fields` for each of the 12 tasks (extract expected values
   from gold files).
2. Rewrite `rewards.py` with the three-signal architecture.
3. Update `submit()` in `finbench_environment.py` to accept `submission_values`.
4. Update `run_agent.py` to include submission field descriptions in the prompt.
5. Run a live agent test and compare reward accuracy.

## What We Intentionally Skip

- **Full NL rubric parsing** — too complex, too brittle.  We only parse the
  easy structural patterns.
- **Cell-by-cell gold comparison** — unfair to different formatting.
- **Task-family evaluator framework** — overengineering for 12 tasks.
- **LLM-as-judge** — non-deterministic, slow, expensive.
- **The "Overall formatting and style" rubric item** (score=5, subjective) —
  give flat 50% partial credit.
