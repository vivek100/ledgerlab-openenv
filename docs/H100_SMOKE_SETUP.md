# H100 Smoke Setup

## Goal

Run the first training smoke test with the environment colocated inside the same runtime as the trainer.

This avoids Hugging Face Space runtime issues blocking training validation.

## Current Status

Ready:
- manifest-aware GRPO trainer: `training/train_finbench_grpo.py`
- baseline eval runner: `training/eval_finbench_baseline.py`
- training image: `Dockerfile.train`
- smoke command wrapper: `scripts/run_h100_smoke.sh`

Known infra gap:
- Northflank CLI auth works
- project `hackathon` exists
- no jobs exist yet
- no linked repository is currently visible in Northflank CLI

## Recommended Resource Target

Use:
- project: `hackathon`
- region: `meta-openenv` if available, otherwise `us-central` or `us-east1`
- GPU: `h100-80`
- count: `1`
- persistent disk: `50 GB` minimum, `100 GB` preferred

## What The Smoke Run Should Do

1. baseline eval on one validation task
2. tiny GRPO run on two training tasks
3. save traces and model outputs
4. inspect rewards before scaling up

## Smoke Command

Inside the training container:

```bash
bash scripts/run_h100_smoke.sh
```

This runs:
- `training/eval_finbench_baseline.py --split val --num-tasks 1`
- `training/train_finbench_grpo.py --max-train-tasks 2 --repeats-per-task 1 --num-train-epochs 1 --max-turns 8 --no-vllm`

## Blocking Decision

To create the Northflank job, we still need one deployment source:
- a linked Git repository, or
- a pushed container image in a registry Northflank can pull from

Without one of those, the CLI can authenticate and inspect the project, but cannot build or run this repo on Northflank yet.
