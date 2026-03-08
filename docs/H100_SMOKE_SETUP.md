# H100 Smoke Setup

## Goal
Run a single manual Northflank H100 job that validates the full LedgerLab training path:
- optional remote baseline eval against the deployed environment
- tiny GRPO smoke training run on 2 tasks
- colocated environment inside the training container

## Current State
- GitHub repo: `https://github.com/vivek100/ledgerlab-openenv`
- Northflank project: `hackathon`
- Northflank region: `meta-openenv`
- GPU target: `1 x h100-80`
- Job spec: `northflank/h100_smoke_job.json`
- Smoke command: `scripts/run_h100_smoke.sh`

## Why This Shape
For the first smoke run, keep the environment and training code in one container. That removes HF Space and network uncertainty from the first RL validation pass.

## Required Inputs
- Linked repo in Northflank: `vivek100/ledgerlab-openenv`
- Optional project secret: `HF_TOKEN`

`HF_TOKEN` is only needed for the remote big-model baseline eval. If it is missing, the smoke script skips baseline eval and still runs GRPO startup validation.

## Job Behavior
The smoke script does two things:
1. If `HF_TOKEN` is set, run a 1-task validation baseline using the HF router model `Qwen/Qwen3-235B-A22B-Instruct-2507`
2. Run a tiny GRPO smoke job with:
   - `max_train_tasks=2`
   - `repeats_per_task=1`
   - `num_train_epochs=1`
   - `max_turns=8`

Outputs are written to `/workspace/outputs/ledgerlab-grpo-smoke`.

## Create The Job
From WSL:

```bash
cd /home/vivek/projects/openenvHack/ReactAgentEnv
~/.local/bin/northflank create job manual \
  --project hackathon \
  --file northflank/h100_smoke_job.json \
  -o json
```

## Add The Optional HF Token Secret
If you want the baseline eval step enabled:

```bash
~/.local/bin/northflank create secret \
  --project hackathon \
  --input '{"name":"HF_TOKEN","value":"YOUR_HF_TOKEN"}' \
  -o json
```

Then attach the secret to the job in the Northflank UI if needed.

## Run The Job
After the job exists:

```bash
~/.local/bin/northflank run job ledgerlab-h100-smoke --project hackathon -o json
```

## Inspect Logs
List jobs:

```bash
~/.local/bin/northflank list jobs --project hackathon -o json
```

Get job details:

```bash
~/.local/bin/northflank get job ledgerlab-h100-smoke --project hackathon -o json
```

## Definition Of Done
- job builds from `Dockerfile.train`
- container starts successfully on `1 x h100-80`
- smoke script completes without Python import or runtime crashes
- training writes outputs under `/workspace/outputs/ledgerlab-grpo-smoke`
- traces are emitted under `/app/traces`

## Next Step After Smoke Passes
- attach persistent volume
- increase train task count
- enable stronger baseline and eval runs
- start a longer GRPO training job
