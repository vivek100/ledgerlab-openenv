#!/usr/bin/env bash
# Push FinBench bundle to Hugging Face Space.
# Usage:
#   export HF_USERNAME=your_hf_username
#   export HF_SPACE_NAME=finbench-openenv   # or whatever you named the Space
#   ./scripts/push_to_hf_space.sh
#
# Or one-liner:
#   HF_USERNAME=youruser HF_SPACE_NAME=finbench-openenv ./scripts/push_to_hf_space.sh

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PARENT_DIR="$(dirname "$REPO_ROOT")"
BUNDLE_DIR="$REPO_ROOT/dist/hf_space"
CLONE_DIR="$PARENT_DIR/hf-finbench-space"

if [[ -z "$HF_USERNAME" || -z "$HF_SPACE_NAME" ]]; then
  echo "Set HF_USERNAME and HF_SPACE_NAME first."
  echo "Example: export HF_USERNAME=myuser && export HF_SPACE_NAME=finbench-openenv"
  exit 1
fi

echo "=== 1. Rebuilding bundle ==="
cd "$REPO_ROOT"
source .venv/bin/activate 2>/dev/null || true
python scripts/prepare_hf_space_bundle.py

echo "=== 2. Clone or update Space repo ==="
if [[ ! -d "$CLONE_DIR" ]]; then
  git clone "https://huggingface.co/spaces/${HF_USERNAME}/${HF_SPACE_NAME}" "$CLONE_DIR"
  cd "$CLONE_DIR"
else
  cd "$CLONE_DIR"
  git pull --rebase || true
fi

echo "=== 3. Sync bundle into repo ==="
# Don't use --delete: preserve .git and .gitattributes in the clone
rsync -av "$BUNDLE_DIR/" "$CLONE_DIR/"

echo "=== 4. Commit and push ==="
git add .
if git diff --staged --quiet; then
  echo "No changes to commit."
else
  git commit -m "Update FinBench Space bundle"
  git push
fi

echo "Done. Space URL: https://huggingface.co/spaces/${HF_USERNAME}/${HF_SPACE_NAME}"
echo "Health check: curl https://${HF_USERNAME}-${HF_SPACE_NAME}.hf.space/health"
