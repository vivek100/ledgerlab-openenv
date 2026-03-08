# Submission Field Generation Status

## Current Status

This work is complete for the current dataset.

Final state:
- `46/46` tasks have `submission_fields`
- all fields were verified against the gold workbooks
- the final pass was deterministic by default
- no LLM is required to regenerate the current field set

## What Changed

This document originally described an LLM-assisted plan.
That is no longer the main implementation path.

The current behavior is:
- `scripts/generate_fields_llm.py` supports optional LLM use
- by default, it runs deterministic extraction
- task-specific extractor functions were added for the tasks that generic extraction could not score well
- the remaining tasks use deterministic fallback logic

In other words, the filename stayed the same, but the operational model changed.

## Final Generation Strategy

### 1. Deterministic first

For each task:
- open the gold workbook with `openpyxl`
- extract workbook-specific final values from known rows/cells/tables
- normalize those values into `submission_fields`

### 2. Generic fallback only when needed

If a workbook has no custom extractor, the script can still derive structural checks from workbook contents.

### 3. Optional LLM path remains available

LLM extraction is still supported as an option, but it is not the default and it is not required for the current 46-task dataset.

## Why This Is Better

Compared with the earlier LLM-heavy plan, the current deterministic approach gives:
- reproducibility
- easier debugging
- lower operational complexity
- no dependency on external model calls for manifest regeneration

## Output Format

Each task now has 2-4 fields like:

```json
{
  "key": "descriptive_metric_name",
  "type": "number" | "integer" | "text",
  "description": "Question the agent must answer at submit time",
  "expected": "verified gold value",
  "tolerance": "present for numeric values where needed"
}
```

## Current Script Role

Primary script:
- `scripts/generate_fields_llm.py`

Current role of that script:
- deterministic task-specific field extraction
- optional LLM-assisted extraction only if explicitly enabled
- manifest update for missing or generic field sets

## Recommended Next Step

Do not spend more time on field generation unless the task set changes.

The next step is to use these fields in real evaluation and training:
1. run baseline agent episodes on train and validation tasks
2. inspect reward failures by component
3. refine scorer behavior only where it produces obvious false negatives
