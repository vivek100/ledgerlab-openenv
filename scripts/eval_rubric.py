#!/usr/bin/env python3
"""
Rubric Calibration: run a model on all tasks and audit check accuracy.

For each task:
  1. Run full episode (reset → agent loop → submit)
  2. Save workspace snapshot + trace
  3. Print per-check audit (PASS/FAIL, expected vs actual)
  4. Save results to traces/rubric_audit.json

Usage:
    # Gold model (72B) — validates that checks are correct
    python scripts/eval_rubric.py --model Qwen/Qwen2.5-72B-Instruct --max-steps 15

    # Weak model (8B) — validates score distribution
    python scripts/eval_rubric.py --model Qwen/Qwen3-8B --max-steps 12

    # Single task only
    python scripts/eval_rubric.py --task-id task_sales --max-steps 10
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "scripts"))

_env_file = os.path.join(_root, ".env")
if os.path.isfile(_env_file):
    from dotenv import load_dotenv
    load_dotenv(_env_file, override=False)

from run_agent import mcp_tools_to_openai, run_episode
from finbench_env.client import FinBenchEnv


def load_manifest() -> list:
    path = os.path.join(_root, "data", "tasks", "task_manifest.json")
    with open(path) as f:
        return json.load(f)


def preview_output_files(workspace_root: str) -> List[Dict[str, str]]:
    output_dir = os.path.join(workspace_root, "output")
    previews: List[Dict[str, str]] = []
    if not os.path.isdir(output_dir):
        return previews

    for name in sorted(os.listdir(output_dir))[:4]:
        path = os.path.join(output_dir, name)
        if not os.path.isfile(path):
            continue
        text = ""
        try:
            if path.endswith((".xlsx", ".xls")):
                import pandas as pd

                xl = pd.ExcelFile(path)
                parts = [f"Workbook sheets: {xl.sheet_names}"]
                for sheet in xl.sheet_names[:2]:
                    df = xl.parse(sheet)
                    parts.append(f"\n[{sheet}] rows={len(df)} cols={list(df.columns)}")
                    parts.append(df.head(6).to_string(index=False))
                text = "\n".join(parts)
            else:
                with open(path, "r", errors="replace") as handle:
                    text = handle.read(1500)
        except Exception as exc:
            text = f"Preview error: {exc}"

        previews.append({"path": f"output/{name}", "preview": text[:1500]})
    return previews


def run_one_task(task_id: str, model: str, max_steps: int, verbose: bool) -> Dict[str, Any]:
    """Run one task and return full audit data."""
    env = FinBenchEnv(
        data_path=os.path.join(_root, "data"),
        traces_dir=os.path.join(_root, "traces"),
        max_steps=max_steps,
    )
    env._ensure_initialized()

    try:
        obs = env.reset(task_id=task_id)
        task_msg = obs.metadata.get("tool_result", "Explore the workspace.")

        list_obs = env.list_tools()
        mcp_tools = getattr(list_obs, "tools", [])
        if not mcp_tools:
            from finbench_env.models import AVAILABLE_TOOLS
            mcp_tools = [type("T", (), {"name": n, "description": n, "input_schema": {}})() for n in AVAILABLE_TOOLS]
        tools_openai = mcp_tools_to_openai(mcp_tools)

        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("HF_TOKEN")
        base_url = os.environ.get("API_BASE_URL")

        start = time.time()
        result = run_episode(
            env._env, tools_openai, task_msg,
            max_steps=max_steps, model=model,
            api_key=api_key, base_url=base_url,
            verbose=verbose,
        )
        elapsed = time.time() - start

        submit_meta = {}
        if hasattr(env, '_env') and hasattr(env._env, '_last_submit_metadata'):
            submit_meta = env._env._last_submit_metadata or {}

        return {
            "task_id": task_id,
            "model": model,
            "steps": result["step_count"],
            "done": result["done"],
            "reward": result["reward"],
            "elapsed_s": round(elapsed, 1),
            "submit_metadata": submit_meta,
            "agent_trace": result.get("agent_trace", []),
            "trace_path": getattr(env._env, "_last_trace_path", None),
            "workspace_root": getattr(env._env, "_workspace_root", None),
            "output_previews": preview_output_files(getattr(env._env, "_workspace_root", "")),
        }
    finally:
        env.close()


def print_audit(task_result: Dict, task_spec: Dict):
    """Print formatted audit for one task."""
    tid = task_result["task_id"]
    reward = task_result["reward"]
    steps = task_result["steps"]
    elapsed = task_result["elapsed_s"]
    meta = task_result.get("submit_metadata", {})

    rubric_score = meta.get("rubric_score", "?")
    rubric_details = meta.get("rubric_details", [])
    exec_checks = meta.get("execution_checks", {})
    mem_checks = meta.get("memory_checks", {})

    print(f"\n{'='*60}")
    print(f"  TASK: {tid}")
    print(f"  Steps: {steps}  Reward: {reward}  Time: {elapsed}s")
    print(f"  Rubric: {rubric_score}  Exec: {meta.get('execution_quality', '?')}  Memory: {meta.get('memory_process', '?')}")
    print(f"{'='*60}")

    if rubric_details:
        print(f"\n  Rubric Checks ({len(rubric_details)}):")
        for i, d in enumerate(rubric_details, 1):
            status = "PASS" if d["passed"] else "FAIL"
            marker = "  [+]" if d["passed"] else "  [-]"
            print(f"  {marker} Check {i}: {d['check']} (score={d['score']}) — {status}")
            print(f"       {d.get('reason', '')}")

    if exec_checks:
        passed = sum(1 for v in exec_checks.values() if v)
        print(f"\n  Execution Quality ({passed}/{len(exec_checks)}):")
        for k, v in exec_checks.items():
            print(f"    {'[+]' if v else '[-]'} {k}")

    if mem_checks:
        passed = sum(1 for v in mem_checks.values() if v)
        print(f"\n  Memory & Process ({passed}/{len(mem_checks)}):")
        for k, v in mem_checks.items():
            print(f"    {'[+]' if v else '[-]'} {k}")

    agent_trace = task_result.get("agent_trace", [])
    if agent_trace:
        print(f"\n  Agent Steps ({len(agent_trace)}):")
        for step in agent_trace[:12]:
            print(
                f"    Step {step['step']:>2}: {step['tool_name']} "
                f"args={json.dumps(step['tool_arguments'])[:90]}"
            )
            preview = step.get("tool_result_preview", "").replace("\n", " ")
            if preview:
                print(f"           result: {preview[:140]}")

    output_previews = task_result.get("output_previews", [])
    if output_previews:
        print("\n  Important Output Previews:")
        for item in output_previews:
            print(f"    {item['path']}")
            preview = item["preview"].strip().replace("\n", "\n      ")
            print(f"      {preview[:500]}")

    if task_result.get("trace_path"):
        print(f"\n  Trace file: {task_result['trace_path']}")


def main():
    parser = argparse.ArgumentParser(description="Rubric calibration eval")
    parser.add_argument("--model", default="Qwen/Qwen2.5-72B-Instruct")
    parser.add_argument("--max-steps", type=int, default=15)
    parser.add_argument("--task-id", default=None, help="Run single task (default: all)")
    parser.add_argument("--verbose", action="store_true", default=False)
    args = parser.parse_args()

    manifest = load_manifest()
    if args.task_id:
        manifest = [t for t in manifest if t["task_id"] == args.task_id]
        if not manifest:
            print(f"Task '{args.task_id}' not found in manifest.")
            sys.exit(1)

    print(f"Rubric Calibration Eval")
    print(f"Model: {args.model}")
    print(f"Tasks: {len(manifest)}")
    print(f"Max steps: {args.max_steps}")
    print()

    results = []
    for task_spec in manifest:
        tid = task_spec["task_id"]
        print(f"Running {tid}...", end=" ", flush=True)

        try:
            result = run_one_task(tid, args.model, args.max_steps, args.verbose)
            print(f"done (reward={result['reward']}, steps={result['steps']})")
            results.append(result)
            print_audit(result, task_spec)
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "task_id": tid, "model": args.model, "error": str(e),
                "steps": 0, "done": False, "reward": None,
            })

    # Summary table
    print(f"\n\n{'='*60}")
    print(f"  SUMMARY: {args.model}")
    print(f"{'='*60}")
    print(f"  {'Task':<25s} {'Rubric':>8s} {'Reward':>8s} {'Steps':>6s} {'Time':>6s}")
    print(f"  {'-'*55}")

    total_rubric = 0
    total_reward = 0
    count = 0
    for r in results:
        meta = r.get("submit_metadata") or {}
        rubric = meta.get("rubric_score", 0)
        reward = r.get("reward") or 0
        print(f"  {r['task_id']:<25s} {rubric:>8.2f} {reward:>8.3f} {r['steps']:>6d} {r.get('elapsed_s', 0):>5.0f}s")
        total_rubric += rubric
        total_reward += reward
        count += 1

    if count > 0:
        print(f"  {'-'*55}")
        print(f"  {'AVERAGE':<25s} {total_rubric/count:>8.2f} {total_reward/count:>8.3f}")

    # Save audit
    audit_path = os.path.join(_root, "traces", "rubric_audit.json")
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    audit = {
        "timestamp": datetime.now().isoformat(),
        "model": args.model,
        "max_steps": args.max_steps,
        "results": results,
    }
    with open(audit_path, "w") as f:
        json.dump(audit, f, indent=2, default=str)
    print(f"\nAudit saved: {audit_path}")


if __name__ == "__main__":
    main()
