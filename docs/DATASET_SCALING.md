# Dataset Scaling Status

## Current Status

Dataset scaling is complete for the Excel-only GDPval subset.

Current dataset state:
- `46` GDPval tasks with xlsx deliverables are present in `data/tasks/task_manifest.json`
- `46/46` tasks have deterministic `submission_fields`
- `34` tasks are in `train_manifest.json`
- `12` tasks are in `val_manifest.json`
- `0` tasks are currently in `test_manifest.json`

Important detail:
- We did not use LLMs by default for the final field generation pass.
- The final `submission_fields` set is deterministic and verified against each gold workbook.
- `scripts/generate_fields_llm.py` now acts as the main deterministic field-generation script despite its filename.

## What Was Completed

### 1. Full xlsx task expansion

We expanded from the initial curated subset to the full GDPval xlsx-compatible set:
- Initial state: `12` tasks
- Final state: `46` tasks

### 2. Workspace population

For each task we now have:
- `reference/` input files
- `gold/` deliverable workbook
- manifest metadata: prompt, rubric, deliverable name, sector

### 3. Deterministic submission field generation

All tasks now have 2-4 programmatically verifiable `submission_fields`.

These fields are based on:
- final totals
- row counts
- scenario counts
- workbook-specific business metrics
- exact IDs or text values where appropriate

### 4. Split manifests

The manifest split pipeline has been run and verified:
- `data/tasks/task_manifest.json` ? master manifest
- `data/tasks/train_manifest.json` ? training split
- `data/tasks/val_manifest.json` ? validation split
- `data/tasks/test_manifest.json` ? currently empty

## What Changed in Practice

| Area | Status |
|------|--------|
| Download all xlsx GDPval tasks | Complete |
| Build workspace directories | Complete |
| Generate generic structural fields | Complete |
| Replace generic fields with deterministic task-specific fields | Complete |
| Train/val split manifests | Complete |
| Full dataset coverage for reward submission fields | Complete |

## Actual File State

```
data/tasks/
??? task_manifest.json      # 46 tasks, all with deterministic submission_fields
??? train_manifest.json     # 34 tasks
??? val_manifest.json       # 12 tasks
??? test_manifest.json      # 0 tasks currently
??? workspaces/
    ??? {task_id}/
        ??? reference/
        ??? gold/
```

## What Is No Longer Accurate

The older plan in this file assumed:
- only `12` tasks were in the manifest
- generic extraction would remain for some tasks
- LLM extraction would likely be needed to finish the set
- synthetic test tasks would remain in the split manifests

Those assumptions are now stale.

## Recommended Next Step

Dataset work is no longer the bottleneck.

The next step should be training readiness:
1. harden the reward scorer against rubric format variation and weak structural parsing
2. update training/eval scripts to explicitly use `train_manifest.json` and `val_manifest.json`
3. run baseline agent evaluations on a small batch of tasks
4. run a short GRPO smoke training job
