# Data Organization Status

## Current State

The data layout is now stable enough for training and evaluation.

Current manifest layout:
- `data/tasks/task_manifest.json` ? master manifest with all `46` GDPval xlsx tasks
- `data/tasks/train_manifest.json` ? `34` training tasks
- `data/tasks/val_manifest.json` ? `12` validation tasks
- `data/tasks/test_manifest.json` ? `0` tasks currently

Current workspace layout:
- all GDPval workspaces live under `data/tasks/workspaces/{task_id}/`
- each workspace contains `reference/` and `gold/`

## What Was Cleaned Up

### 1. Manifest splitting

We now have explicit split manifests instead of relying on one flat manifest for everything.

### 2. Deterministic task verification

Every task in the master, train, and validation manifests has deterministic `submission_fields`.
This means reward verification is now aligned with the data organization.

### 3. Training-relevant structure

The current layout supports:
- local smoke testing against a chosen task
- batch evaluation over `train_manifest.json`
- held-out validation over `val_manifest.json`

## Actual Directory Layout

```
data/
??? tasks/
?   ??? task_manifest.json
?   ??? train_manifest.json
?   ??? val_manifest.json
?   ??? test_manifest.json
?   ??? workspaces/
?       ??? {task_id}/
?       ?   ??? reference/
?       ?   ??? gold/
?       ??? ...
??? _persistent_memory/
??? memory_seed/
```

## Notes

### `test_manifest.json`

This file exists, but it is currently empty.

That matters because some older docs assumed synthetic tasks would populate the test split.
Right now, the useful splits are:
- `train_manifest.json`
- `val_manifest.json`

### Master manifest remains important

`task_manifest.json` is still the source of truth. The split manifests are generated outputs.

## What Still Needs To Be Wired

The data organization itself is done. The remaining work is code wiring around it:
- training should load `train_manifest.json` explicitly
- validation evaluation should load `val_manifest.json` explicitly
- smoke tests can either target a specific task or use a small curated eval subset

## Recommended Next Step

Use the current data organization as fixed infrastructure and move to training-readiness work:
1. training script manifest selection
2. validation baseline evaluation
3. short end-to-end GRPO smoke run
