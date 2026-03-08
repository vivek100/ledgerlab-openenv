#!/usr/bin/env python3
"""
Test FinBench with one real GDPval task.

This is a generic environment sanity check for the curated real-task set:
- reset on the first task (or FINBENCH_TASK_ID)
- inspect reference files
- create a notebook
- submit to verify reward plumbing / trace capture

Usage:
    source .venv/bin/activate
    python scripts/test_with_task.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finbench_env.client import FinBenchEnv


def obs_text(obs):
    if hasattr(obs, "result") and obs.result:
        try:
            return obs.result.content[0].text
        except Exception:
            return str(obs.result)
    return str(obs.metadata)


root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = FinBenchEnv(data_path=os.path.join(root, "data"), traces_dir=os.path.join(root, "traces"), max_steps=30)

manifest_path = os.path.join(root, "data", "tasks", "task_manifest.json")
with open(manifest_path) as f:
    manifest = json.load(f)
task_id = os.environ.get("FINBENCH_TASK_ID") or manifest[0]["task_id"]

try:
    obs = env.reset(task_id=task_id, episode_id=f"test_{task_id[:8]}")
    print("=== RESET ===")
    print(obs.metadata.get("tool_result", "")[:500])
    print(f"Task ID: {task_id}")

    # Step 1: List reference files
    obs = env.call_tool("list_files", path="/reference")
    print("\n=== list_files /reference ===")
    print(obs_text(obs))

    reference_files = obs.metadata.get("tool_result", "") if hasattr(obs, "metadata") else ""
    task_spec = next((t for t in manifest if t["task_id"] == task_id), {})
    first_ref = task_spec.get("reference_files", [None])[0]

    # Step 2: Read the first reference file
    if first_ref:
        obs = env.call_tool("read_file", path=f"reference/{first_ref}")
        print("\n=== read_file ===")
        print(obs_text(obs)[:600])

    # Step 3: Create notebook
    obs = env.call_tool("create_notebook", path="work/analysis.ipynb")
    print("\n=== create_notebook ===")
    print(obs_text(obs))

    # Step 4: List memory
    obs = env.call_tool("list_memory")
    print("\n=== list_memory ===")
    print(obs_text(obs)[:600])

    # Step 5: Submit without deliverable (expected to score low, just verifies evaluation path)
    obs = env.call_tool("submit")
    print("\n=== SUBMIT ===")
    print(json.dumps(obs.metadata, indent=2, default=str)[:3000])
    print(f"\nFinal reward: {obs.reward}")
    print(f"Done: {obs.done}")

finally:
    env.close()
