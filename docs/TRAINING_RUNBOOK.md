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
