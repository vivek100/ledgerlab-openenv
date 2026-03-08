# Training Results

## Baseline Reference
- Job: `ledgerlab-baseline-eval`
- Run ID: `2e32c1da-f4a3-47eb-a32c-c802da2e3e5f`
- Status: `SUCCESS`
- W&B run: `https://wandb.ai/shukla-vivek1993-startup/ledgerlab/runs/cx1mhzzr`
- Summary artifact: `/workspace/outputs/ledgerlab-baseline-20260308-171452.json`
- Metrics:
  - `num_tasks = 12`
  - `mean_reward = 0.005933333333333329`
  - `done_rate = 1.0`
- Important caveat:
  - this baseline used `Qwen/Qwen3-235B-A22B-Instruct-2507`
  - it is useful as an operational benchmark, not the final apples-to-apples comparison for the fine-tuned `Qwen/Qwen3-1.7B`

## First Successful Training Run
- Job: `ledgerlab-medium-train`
- Run ID: `10032551-a954-4330-b09a-1a8f365e4d71`
- Status: `SUCCESS`
- W&B run: `https://wandb.ai/shukla-vivek1993-startup/ledgerlab/runs/obfa3dim`
- Saved model path: `/workspace/outputs/ledgerlab-train-20260308-174221/model`
- Successful config:
  - `train_tasks = 4`
  - `dataset_rows = 4`
  - `max_steps = 4`
  - `max_turns = 6`
  - `num_generations = 2`
  - `max_completion_length = 96`
  - `max_prompt_length = 1536`

## Failed Training Runs And What They Taught Us
1. Run `04a7790d-71fd-48c6-9b45-945cdd6ef968`
- Failure: CUDA OOM
- Lesson: peak memory is dominated by prompt/completion length, generations, and rollout state, not just model size.

2. Run `8390ec0b-e166-4515-b456-a51c16507187`
- Failure: invalid GRPO config with `num_generations = 1`
- Lesson: GRPO requires at least 2 generations per prompt.

## Next Comparison We Still Need
- Evaluate the base `Qwen/Qwen3-1.7B` model on the same validation tasks.
- Evaluate the fine-tuned checkpoint on the same validation tasks.
- Compare both in W&B using the same metric set.

## Artifact Persistence
- Future successful training runs will upload the saved checkpoint directory to W&B as a model artifact from inside 	rain_finbench_grpo.py.
- This is the persistence mechanism we are using until a persistent Northflank volume is attached.

