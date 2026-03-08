#!/usr/bin/env bash
set -euo pipefail

cd /app

mkdir -p /workspace/outputs /app/traces

python3 training/eval_finbench_baseline.py   --split val   --num-tasks 1   --max-steps 12   --model "${BASELINE_MODEL:-Qwen/Qwen3-235B-A22B-Instruct-2507}"   --base-url "${BASELINE_BASE_URL:-https://router.huggingface.co/v1}"   --api-key "${HF_TOKEN:-}"

python3 training/train_finbench_grpo.py   --max-train-tasks 2   --repeats-per-task 1   --num-train-epochs 1   --max-turns 8   --output-dir /workspace/outputs/ledgerlab-grpo-smoke   --no-vllm
