# Training Runbook

## Current Truth
- Real training is happening on the H100.
- The training path loads `Qwen/Qwen3-1.7B` inside `GRPOTrainer`, updates those weights, and writes a saved model at the end.
- The current Northflank job used for H100 runs is `envbuildersmoke-test` in project `hackathon`.

## What Worked In The Smoke Run
- Runtime bootstrap on the H100 node works.
- GPU-attached manual job works when the job has `1 x h100-80` configured.
- W&B logging works once `WANDB_API_KEY`, `WANDB_PROJECT`, and `WANDB_ENTITY` are set on the job.
- The smoke pipeline completed successfully on March 8, 2026.

## Issues We Hit And Fixes
1. GPU was not attached
- Symptom: `The NVIDIA Driver was not detected.`
- Fix: patch the Northflank job so the deployment has `gpu.enabled=true` and `gpuType=h100-80`.

2. TRL version mismatch
- Symptom: `GRPOConfig.__init__() got an unexpected keyword argument 'max_prompt_length'`
- Fix: filter `GRPOConfig` kwargs dynamically against the installed TRL signature.

3. Trainer required positive `max_steps`
- Symptom: `args.max_steps must be set to a positive value if dataloader does not have a length`
- Fix: compute `trainer_max_steps = max(1, len(dataset_records))` and pass it to `GRPOConfig` when supported.

4. W&B hard-failed without credentials
- Symptom: `wandb.errors.errors.UsageError: No API key configured`
- Fix: configure `WANDB_API_KEY`, `WANDB_PROJECT`, and `WANDB_ENTITY` on the Northflank job runtime environment.

## Fair Baseline Rule
- Compare the trained model against the same base model family.
- Good comparison:
  - baseline: base `Qwen/Qwen3-1.7B`
  - trained: fine-tuned `Qwen/Qwen3-1.7B`
- Bad comparison:
  - baseline: `Qwen3-235B`
  - trained: `Qwen3-1.7B`

## Commands
### Start A Job Run
```bash
~/.local/bin/northflank start job run --job envbuildersmoke-test --project hackathon -i '{}' -o json
```

### Check Run State
```bash
~/.local/bin/northflank get job run --job envbuildersmoke-test --project hackathon --run RUN_ID -o json
```

### Filter Error Lines
```bash
~/.local/bin/northflank get job log --job envbuildersmoke-test --project hackathon --run RUN_ID \
  | grep -E 'Traceback|Error:|TypeError|ValueError|RuntimeError|ModuleNotFoundError|Process terminated|Killed|exit code|Exception'
```

## Current Medium-Run Script
- Script: `scripts/run_h100_training_medium.sh`
- Behavior:
  1. install runtime deps on the H100 node
  2. optionally run a 12-task validation baseline with base `Qwen/Qwen3-1.7B`
  3. log baseline summary to W&B
  4. train on all 34 train tasks with a medium configuration
  5. save outputs under `/workspace/outputs/ledgerlab-medium-TIMESTAMP`

## Medium Training Defaults
- `max_train_tasks=34`
- `repeats_per_task=2`
- `num_train_epochs=2`
- `max_turns=12`
- `save_steps=20`
- `no_vllm=true`

## Runtime Environment Needed On Northflank
- `WANDB_API_KEY`
- `WANDB_PROJECT=ledgerlab`
- `WANDB_ENTITY=shukla-vivek1993-startup`
- optional: `HF_TOKEN`

## What We Still Need After The Medium Run
1. persistent storage for checkpoints
2. post-train validation eval against the saved checkpoint
3. optional local vLLM serving for post-train evaluation through the existing OpenAI-compatible runner

## Recorded Runs
### Baseline Eval Success
- Job: `ledgerlab-baseline-eval`
- Run ID: `2e32c1da-f4a3-47eb-a32c-c802da2e3e5f`
- Status: `SUCCESS`
- Time: `2026-03-08 17:12 UTC` to `2026-03-08 17:24 UTC`
- W&B run: `https://wandb.ai/shukla-vivek1993-startup/ledgerlab/runs/cx1mhzzr`
- Summary file: `/workspace/outputs/ledgerlab-baseline-20260308-171452.json`
- Metrics:
  - `num_tasks = 12`
  - `mean_reward = 0.005933333333333329`
  - `done_rate = 1.0`
- Caveat: this baseline used `Qwen/Qwen3-235B-A22B-Instruct-2507`, so it is useful as an operational reference but not the final fair comparison to the fine-tuned `1.7B` model.

### Conservative Training Success
- Job: `ledgerlab-medium-train`
- Run ID: `10032551-a954-4330-b09a-1a8f365e4d71`
- Status: `SUCCESS`
- Time: `2026-03-08 17:40 UTC` to `2026-03-08 17:43 UTC`
- W&B run: `https://wandb.ai/shukla-vivek1993-startup/ledgerlab/runs/obfa3dim`
- Saved model path: `/workspace/outputs/ledgerlab-train-20260308-174221/model`
- Training settings that worked:
  - `train_tasks = 4`
  - `dataset_rows = 4`
  - `max_steps = 4`
  - `max_turns = 6`
  - `num_generations = 2`
  - `max_completion_length = 96`
  - `max_prompt_length = 1536`

## Current Safe Scale-Up Plan
- Keep the low-memory generation settings fixed.
- Increase duration by increasing train task count first.
- Next run target:
  - `train_tasks = 8`
  - `dataset_rows = 8`
  - `max_turns = 6`
  - `num_generations = 2`
  - `max_completion_length = 96`
  - `max_prompt_length = 1536`
- Reason: this should lengthen training without materially increasing peak memory in the same way that longer prompts/completions or extra generations would.

## Checkpoint Persistence
- Successful training runs now upload the saved model directory to W&B as a model artifact when a W&B run is active.
- This avoids losing trained weights when the Northflank job uses only ephemeral storage.
- Future continuation runs should resume from the downloaded W&B model artifact or from a persistent volume copy.

