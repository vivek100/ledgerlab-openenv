#!/usr/bin/env python3
"""
Test the FinBench agent with a REAL LLM (no mocks).

Requires OPENAI_API_KEY or HF_TOKEN in env (or in .env). Runs one short episode
and asserts the model was actually called and at least one tool was executed.

Usage:
    # Load key from .env
    python scripts/test_agent_with_llm.py

    # Or set in env
    export OPENAI_API_KEY=...
    python scripts/test_agent_with_llm.py

    # Use a specific model
    python scripts/test_agent_with_llm.py --model gpt-4o-mini --max-steps 5
"""

from __future__ import annotations

import argparse
import os
import sys

# Load .env from project root so OPENAI_API_KEY / HF_TOKEN are set
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_file = os.path.join(_root, ".env")
if os.path.isfile(_env_file):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass

sys.path.insert(0, _root)
# So we can import run_agent from the scripts folder
sys.path.insert(0, os.path.join(_root, "scripts"))


def _get_api_key() -> str | None:
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("HF_TOKEN")


def main():
    parser = argparse.ArgumentParser(description="Test agent with real LLM")
    parser.add_argument("--model", default="gpt-4o-mini", help="Model name")
    parser.add_argument("--base-url", default=None, help="API base URL (e.g. HF Inference)")
    parser.add_argument("--task-id", default="task_sales", help="Task to run")
    parser.add_argument("--max-steps", type=int, default=8, help="Max tool calls (keep low for test)")
    parser.add_argument("--quiet", action="store_true", help="Less output")
    args = parser.parse_args()

    api_key = _get_api_key()
    if not api_key:
        print("ERROR: Set OPENAI_API_KEY or HF_TOKEN (or add to .env)")
        sys.exit(1)

    # Reuse run_agent helpers (run from project root: python scripts/test_agent_with_llm.py)
    from run_agent import (
        mcp_tools_to_openai,
        run_episode,
    )
    from finbench_env.client import FinBenchEnv

    env = FinBenchEnv(
        data_path=os.path.join(_root, "data"),
        traces_dir=os.path.join(_root, "traces"),
        max_steps=args.max_steps,
    )
    env._ensure_initialized()

    obs = env.reset(task_id=args.task_id)
    task_msg = obs.metadata.get("tool_result", "Explore the workspace.")

    list_obs = env.list_tools()
    mcp_tools = getattr(list_obs, "tools", [])
    if not mcp_tools:
        from finbench_env.models import AVAILABLE_TOOLS
        mcp_tools = [type("T", (), {"name": n, "description": n, "input_schema": {}})() for n in AVAILABLE_TOOLS]
    tools_openai = mcp_tools_to_openai(mcp_tools)

    if not args.quiet:
        print(f"Testing with real LLM: {args.model}")
        print(f"Task: {args.task_id} | max_steps: {args.max_steps}")
        print(f"Task prompt: {task_msg[:200]}...")
        print()

    try:
        result = run_episode(
            env._env,
            tools_openai,
            task_msg,
            max_steps=args.max_steps,
            model=args.model,
            api_key=api_key,
            base_url=os.environ.get("API_BASE_URL") or args.base_url,
            verbose=not args.quiet,
        )
    finally:
        env.close()

    # Assertions: we actually used the LLM and the env
    step_count = result["step_count"]
    done = result["done"]
    reward = result["reward"]

    if step_count < 1:
        print("FAIL: No steps taken — LLM was not called or did not return a tool call.")
        sys.exit(1)

    print()
    print("=" * 50)
    print("TEST PASSED: Real LLM was called and tools were executed.")
    print(f"  Steps: {step_count}  Done: {done}  Reward: {reward}")
    print("=" * 50)


if __name__ == "__main__":
    main()
