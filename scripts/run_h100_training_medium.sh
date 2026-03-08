#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export HF_HOME="${HF_HOME:-/workspace/.cache/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/workspace/.cache/huggingface}"

apt-get update
apt-get install -y --no-install-recommends python3 python3-pip git
rm -rf /var/lib/apt/lists/*

mkdir -p /workspace/.cache/huggingface /workspace/outputs
cd /workspace
rm -rf ledgerlab-openenv

git clone --depth 1 --branch main https://github.com/vivek100/ledgerlab-openenv ledgerlab-openenv
cd ledgerlab-openenv

python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install --index-url https://download.pytorch.org/whl/cu124 torch
python3 -m pip install -r training/requirements-smoke.txt
python3 -m ipykernel install --sys-prefix --name python3

mkdir -p traces data/_persistent_memory

ts="$(date +%Y%m%d-%H%M%S)"
run_root="/workspace/outputs/ledgerlab-medium-${ts}"
mkdir -p "${run_root}"

if [[ -n "${HF_TOKEN:-}" ]]; then
  export WANDB_NAME="${WANDB_BASELINE_NAME:-ledgerlab-baseline-qwen3-1.7b-${ts}}"
  python3 training/eval_finbench_baseline.py \
    --split val \
    --num-tasks 12 \
    --max-steps 15 \
    --model "${BASELINE_MODEL:-Qwen/Qwen3-1.7B}" \
    --base-url "${BASELINE_BASE_URL:-https://router.huggingface.co/v1}" \
    --api-key "${HF_TOKEN}" \
    --output-json "${run_root}/baseline_pretrain.json" \
    --log-to-wandb \
    --wandb-run-name "${WANDB_NAME}"
else
  echo "HF_TOKEN is not set; skipping remote baseline eval."
fi

export WANDB_NAME="${WANDB_TRAIN_NAME:-ledgerlab-grpo-medium-${ts}}"
export WANDB_RUN_GROUP="${WANDB_RUN_GROUP:-ledgerlab-grpo-medium}"
python3 training/train_finbench_grpo.py \
  --max-train-tasks "${TRAIN_TASK_LIMIT:-34}" \
  --repeats-per-task "${REPEATS_PER_TASK:-2}" \
  --num-train-epochs "${NUM_TRAIN_EPOCHS:-2}" \
  --max-turns "${MAX_TURNS:-12}" \
  --save-steps "${SAVE_STEPS:-20}" \
  --output-dir "${run_root}/model" \
  --no-vllm

echo "Training artifacts saved under ${run_root}"
