#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export HF_HOME="${HF_HOME:-/workspace/.cache/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/workspace/.cache/huggingface}"
export TOKENIZERS_PARALLELISM="false"
export CC="${CC:-gcc}"
export CXX="${CXX:-g++}"

apt-get update
apt-get install -y --no-install-recommends python3 python3-dev python3-pip git curl build-essential
rm -rf /var/lib/apt/lists/*

mkdir -p /workspace/.cache/huggingface /workspace/outputs /workspace/artifacts
cd /workspace
rm -rf ledgerlab-openenv

git clone --depth 1 --branch main https://github.com/vivek100/ledgerlab-openenv ledgerlab-openenv
cd ledgerlab-openenv

python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install -r training/requirements-eval.txt
python3 -m ipykernel install --sys-prefix --name python3

mkdir -p traces data/_persistent_memory

DEFAULT_MODEL_SOURCE="${BASE_MODEL_SOURCE:-Qwen/Qwen3-1.7B}"
MODEL_SOURCE="${MODEL_SOURCE:-${DEFAULT_MODEL_SOURCE}}"
if [[ -n "${RESUME_MODEL_ARTIFACT:-}" ]]; then
  resume_root="/workspace/artifacts/resume_model"
  rm -rf "${resume_root}"
  mkdir -p "${resume_root}"
  python3 - <<'PY'
import os
import wandb

artifact_name = os.environ["RESUME_MODEL_ARTIFACT"]
root = "/workspace/artifacts/resume_model"
api = wandb.Api()
artifact = api.artifact(artifact_name, type="model")
path = artifact.download(root=root)
print(path)
PY
  MODEL_SOURCE="${resume_root}"
  echo "Serving fine-tuned checkpoint from W&B artifact: ${RESUME_MODEL_ARTIFACT}"
fi

SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-${DEFAULT_MODEL_SOURCE}}"
VLLM_HOST="${VLLM_HOST:-127.0.0.1}"
VLLM_PORT="${VLLM_PORT:-8000}"
VLLM_API_KEY="${VLLM_API_KEY:-dummy}"
VLLM_GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.80}"
VLLM_MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-4096}"

ts="$(date +%Y%m%d-%H%M%S)"
run_root="/workspace/outputs/ledgerlab-vllm-eval-${ts}"
mkdir -p "${run_root}"
vllm_log="${run_root}/vllm.log"

vllm_cmd=(
  vllm serve "${MODEL_SOURCE}"
  --host "${VLLM_HOST}"
  --port "${VLLM_PORT}"
  --api-key "${VLLM_API_KEY}"
  --served-model-name "${SERVED_MODEL_NAME}"
  --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTILIZATION}"
  --max-model-len "${VLLM_MAX_MODEL_LEN}"
  --generation-config vllm
)

if [[ "${VLLM_TRUST_REMOTE_CODE:-false}" == "true" ]]; then
  vllm_cmd+=(--trust-remote-code)
fi

printf 'Starting vLLM server:\n  %q' "${vllm_cmd[0]}"
for arg in "${vllm_cmd[@]:1}"; do
  printf ' %q' "${arg}"
done
printf '\n'

"${vllm_cmd[@]}" >"${vllm_log}" 2>&1 &
VLLM_PID=$!

show_vllm_log() {
  if [[ -f "${vllm_log}" ]]; then
    echo "===== vLLM log tail ====="
    tail -n 200 "${vllm_log}" || true
    echo "===== end vLLM log tail ====="
  fi
}

cleanup() {
  local exit_code=$?
  if (( exit_code != 0 )); then
    show_vllm_log
  fi
  if kill -0 "${VLLM_PID}" >/dev/null 2>&1; then
    kill "${VLLM_PID}" || true
    wait "${VLLM_PID}" || true
  fi
  exit ${exit_code}
}
trap cleanup EXIT

python3 - <<'PY'
import os
import sys
import time
import urllib.request

host = os.environ.get("VLLM_HOST", "127.0.0.1")
port = os.environ.get("VLLM_PORT", "8000")
api_key = os.environ.get("VLLM_API_KEY", "dummy")
deadline = time.time() + int(os.environ.get("VLLM_STARTUP_TIMEOUT", "900"))
url = f"http://{host}:{port}/v1/models"

while time.time() < deadline:
    try:
        request = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status == 200:
                print(f"vLLM ready at {url}")
                sys.exit(0)
    except Exception:
        time.sleep(5)

print(f"Timed out waiting for vLLM at {url}", file=sys.stderr)
sys.exit(1)
PY

wandb_args=()
if [[ "${EVAL_LOG_TO_WANDB:-true}" == "true" ]]; then
  wandb_args=(
    --log-to-wandb
    --wandb-project "${WANDB_PROJECT:-ledgerlab}"
    --wandb-entity "${WANDB_ENTITY:-}"
    --wandb-run-name "${WANDB_EVAL_NAME:-ledgerlab-vllm-eval-${ts}}"
  )
fi

eval_args=(
  --split "${EVAL_SPLIT:-val}"
  --num-tasks "${EVAL_NUM_TASKS:-12}"
  --max-steps "${EVAL_MAX_STEPS:-25}"
  --model "${SERVED_MODEL_NAME}"
  --api-key "${VLLM_API_KEY}"
  --base-url "http://${VLLM_HOST}:${VLLM_PORT}/v1"
  --output-json "${run_root}/summary.json"
)

if [[ -n "${EVAL_MANIFEST:-}" ]]; then
  eval_args+=(--manifest "${EVAL_MANIFEST}")
fi

echo "Running eval through local vLLM..."
python3 training/eval_finbench_baseline.py "${eval_args[@]}" "${wandb_args[@]}"

echo "Evaluation artifacts saved under ${run_root}"
echo "vLLM log saved to ${vllm_log}"

