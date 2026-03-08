#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export HF_HOME="${HF_HOME:-/workspace/.cache/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/workspace/.cache/huggingface}"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "HF_TOKEN is required for baseline eval."
  exit 1
fi

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
out_json="/workspace/outputs/ledgerlab-baseline-${ts}.json"

python3 training/eval_finbench_baseline.py \
  --split val \
  --num-tasks "${BASELINE_NUM_TASKS:-12}" \
  --max-steps "${BASELINE_MAX_STEPS:-15}" \
  --model "${BASELINE_MODEL:-Qwen/Qwen3-235B-A22B-Instruct-2507}" \
  --base-url "${BASELINE_BASE_URL:-https://router.huggingface.co/v1}" \
  --api-key "${HF_TOKEN}" \
  --output-json "${out_json}" \
  --log-to-wandb \
  --wandb-run-name "${WANDB_BASELINE_NAME:-ledgerlab-baseline-$(date +%Y%m%d-%H%M%S)}"

echo "Baseline summary saved to ${out_json}"
