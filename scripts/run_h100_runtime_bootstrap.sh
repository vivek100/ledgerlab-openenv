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

if [[ -n "${HF_TOKEN:-}" ]]; then
  python3 training/eval_finbench_baseline.py \
    --split val \
    --num-tasks 1 \
    --max-steps 12 \
    --model "${BASELINE_MODEL:-Qwen/Qwen3-235B-A22B-Instruct-2507}" \
    --base-url "${BASELINE_BASE_URL:-https://router.huggingface.co/v1}" \
    --api-key "${HF_TOKEN}"
else
  echo "HF_TOKEN is not set; skipping remote baseline eval."
fi

python3 training/train_finbench_grpo.py \
  --max-train-tasks 2 \
  --repeats-per-task 1 \
  --num-train-epochs 1 \
  --max-turns 8 \
  --output-dir /workspace/outputs/ledgerlab-grpo-smoke \
  --no-vllm
