#!/usr/bin/env python3
"""Smoke-test a running FinBench Docker container or HF Space."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finbench_env.client import FinBenchRemoteEnv
from openenv.core.env_server.mcp_types import CallToolAction


def print_reset(step_result):
    obs = step_result.observation
    metadata = getattr(obs, "metadata", {}) or {}
    text = metadata.get("tool_result", "")
    print("\n=== RESET ===")
    print(text[:1200])
    print(f"done={step_result.done} reward={step_result.reward}")


def main():
    parser = argparse.ArgumentParser(description="Smoke-test remote FinBench environment")
    parser.add_argument("--base-url", required=True, help="Remote env base URL, e.g. http://localhost:8000")
    parser.add_argument("--task-id", default=None, help="Optional task id to reset to")
    args = parser.parse_args()

    with FinBenchRemoteEnv(base_url=args.base_url).sync() as env:
        reset_result = env.reset(task_id=args.task_id, episode_id="remote_smoke")
        print_reset(reset_result)

        tools = env.list_tools()
        print("\n=== TOOLS ===")
        print([tool.name for tool in tools])

        files = env.call_tool("list_files", path="reference")
        print("\n=== list_files(reference) ===")
        print(str(files)[:2000])

        memory = env.call_tool("list_memory")
        print("\n=== list_memory ===")
        print(str(memory)[:1200])

        submit_result = env.step(CallToolAction(tool_name="submit", arguments={}))
        print("\n=== SUBMIT ===")
        print(
            json.dumps(
                {
                    "done": submit_result.done,
                    "reward": submit_result.reward,
                    "metadata": getattr(submit_result.observation, "metadata", {}),
                },
                indent=2,
                default=str,
            )[:3000]
        )


if __name__ == "__main__":
    main()
