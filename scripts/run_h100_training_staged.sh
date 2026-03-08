#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export HF_HOME="${HF_HOME:-/workspace/.cache/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/workspace/.cache/huggingface}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export TOKENIZERS_PARALLELISM="false"

apt-get update
apt-get install -y --no-install-recommends python3 python3-pip git
rm -rf /var/lib/apt/lists/*

mkdir -p /workspace/.cache/huggingface /workspace/outputs /workspace/artifacts
cd /workspace
rm -rf ledgerlab-openenv

git clone --depth 1 --branch main https://github.com/vivek100/ledgerlab-openenv ledgerlab-openenv
cd ledgerlab-openenv

python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install --index-url https://download.pytorch.org/whl/cu124 torch
python3 -m pip install -r training/requirements-smoke.txt
python3 -m ipykernel install --sys-prefix --name python3

mkdir -p traces data/_persistent_memory

MODEL_SOURCE="${MODEL_SOURCE:-Qwen/Qwen3-1.7B}"
if [[ -n "${RESUME_MODEL_ARTIFACT:-}" ]]; then
  resume_root="/workspace/artifacts/resume_model"
  rm -rf "${resume_root}"
  mkdir -p "${resume_root}"
  python3 - <<'PY'
import os
import wandb
artifact_name = os.environ['RESUME_MODEL_ARTIFACT']
root = '/workspace/artifacts/resume_model'
api = wandb.Api()
artifact = api.artifact(artifact_name, type='model')
path = artifact.download(root=root)
print(path)
PY
  MODEL_SOURCE="${resume_root}"
  echo "Resuming staged training from W&B artifact: ${RESUME_MODEL_ARTIFACT}"
fi

ts="$(date +%Y%m%d-%H%M%S)"
run_root="/workspace/outputs/ledgerlab-staged-${ts}"
mkdir -p "${run_root}"

SCHEDULE="${TRAIN_TASK_SCHEDULE:-4,8,12}"
IFS=',' read -r -a PHASE_TASKS <<< "${SCHEDULE}"
PHASE_COUNT="${#PHASE_TASKS[@]}"

for idx in "${!PHASE_TASKS[@]}"; do
  phase="$((idx + 1))"
  train_task_limit="${PHASE_TASKS[$idx]}"
  phase_dir="${run_root}/phase-${phase}"
  mkdir -p "${phase_dir}"

  export WANDB_NAME="${WANDB_TRAIN_NAME_PREFIX:-ledgerlab-grpo-staged}-${ts}-p${phase}"
  export WANDB_RUN_GROUP="${WANDB_RUN_GROUP:-ledgerlab-grpo-staged}"
  export WANDB_MODEL_ARTIFACT_NAME="${WANDB_MODEL_ARTIFACT_PREFIX:-ledgerlab-model-staged}-${ts}-p${phase}"

  echo "Starting staged training phase ${phase}/${PHASE_COUNT} with ${train_task_limit} tasks"
  python3 training/train_finbench_grpo.py \
    --model-name "${MODEL_SOURCE}" \
    --max-train-tasks "${train_task_limit}" \
    --repeats-per-task "${REPEATS_PER_TASK:-1}" \
    --num-train-epochs "${NUM_TRAIN_EPOCHS:-1}" \
    --max-turns "${MAX_TURNS:-6}" \
    --num-generations "${NUM_GENERATIONS:-2}" \
    --max-completion-length "${MAX_COMPLETION_LENGTH:-96}" \
    --max-prompt-length "${MAX_PROMPT_LENGTH:-1536}" \
    --save-steps "${SAVE_STEPS:-5}" \
    --output-dir "${phase_dir}/model" \
    --no-vllm

  MODEL_SOURCE="${phase_dir}/model"
  echo "Completed phase ${phase}; next phase will resume from ${MODEL_SOURCE}"
done

echo "Staged training artifacts saved under ${run_root}"
