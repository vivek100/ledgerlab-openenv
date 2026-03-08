#!/usr/bin/env python3
"""
FinBench inference agent — OpenAI-compatible function calling.

Runs one episode: reset(task) → tool-calling loop → submit → reward.
Works with any OpenAI-compatible API: HF Inference, vLLM, OpenAI, etc.

Same pattern as OpenEnv/examples/finqa_inference.py — no LangGraph needed.
Judges interact with the env via HF Spaces; this script is for testing
and as the basis for the TRL GRPO rollout function.

Usage:
    # With HF Inference (small model — trainable)
    export HF_TOKEN=...
    python scripts/run_agent.py \\
        --model Qwen/Qwen3-1.7B \\
        --base-url https://router.huggingface.co/v1

    # With OpenAI (for quick testing)
    export OPENAI_API_KEY=...
    python scripts/run_agent.py --model gpt-4o-mini

    # With local vLLM
    python scripts/run_agent.py \\
        --model Qwen/Qwen3-1.7B \\
        --base-url http://localhost:8000/v1 \\
        --api-key dummy
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

# Auto-load .env
_env_file = os.path.join(_root, ".env")
if os.path.isfile(_env_file):
    from dotenv import load_dotenv
    load_dotenv(_env_file, override=False)

from openenv.core.env_server.mcp_types import CallToolAction


SYSTEM_PROMPT = """You are a financial data analyst. You have a workspace with tools.

## Workspace (all paths are RELATIVE — no leading slash)
- reference/  — input data files (Excel, CSV). READ THESE FIRST.
- memory/     — saved notebook templates from past episodes.
- work/       — create notebooks and intermediate files here.
- output/     — final deliverables go here.

## How to work
1. list_files("reference") to see input data.
2. read_file("reference/filename.xlsx") to understand the data.
3. create_notebook("work/analysis.ipynb") then write_and_run to add and execute cells.
4. In notebook code, use RELATIVE paths like pd.read_excel("reference/data.xlsx") — NOT absolute paths.
5. Iterate: read output, edit_cell or add more cells. Check get_kernel_state.
6. Write final deliverable to output/ with write_file or from notebook code.
7. Call submit with both deliverable_paths AND submission_values (JSON with verification answers).

## Submission
When you call submit, you MUST provide submission_values — a JSON string with answers to the verification fields listed in the task. Example:
  submit(deliverable_paths="output/Report.xlsx", submission_values='{"total_revenue": 50000, "row_count": 120}')

IMPORTANT: All file paths are relative to the workspace root. Use "reference/file.xlsx" not "/reference/file.xlsx"."""


def obs_to_text(obs: Any) -> str:
    """Extract text from any observation type."""
    if obs is None:
        return ""
    if hasattr(obs, "result") and obs.result is not None:
        r = obs.result
        if hasattr(r, "content") and r.content:
            return getattr(r.content[0], "text", str(r.content[0]))
        if hasattr(r, "data") and r.data is not None:
            return str(r.data)
        return str(r)
    if hasattr(obs, "metadata"):
        return str(obs.metadata.get("tool_result", obs.metadata))
    return str(obs)


def mcp_tools_to_openai(tools: List[Any]) -> List[Dict]:
    """Convert MCP Tool objects to OpenAI function-calling format."""
    result = []
    for t in tools:
        schema = getattr(t, "input_schema", None) or getattr(t, "inputSchema", {}) or {}
        props = schema.get("properties", {})
        result.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": getattr(t, "description", "") or t.name,
                "parameters": {
                    "type": "object",
                    "properties": {
                        k: {"type": v.get("type", "string"), "description": v.get("description", "")}
                        for k, v in props.items()
                    },
                    "required": schema.get("required", []),
                },
            },
        })
    return result


def parse_text_tool_call(content: str, tool_names: set[str]) -> tuple[str, Dict[str, Any]] | None:
    """Best-effort parser for text-formatted tool calls."""
    if not content:
        return None

    # Try extracting JSON blocks (including tool wrapper tags often emitted by open models).
    candidates = re.findall(r"\{[\s\S]*\}", content)
    for block in candidates:
        try:
            payload = json.loads(block)
        except Exception:
            continue

        name = payload.get("name") or payload.get("tool_name") or payload.get("tool")
        args = payload.get("arguments") or payload.get("args") or {}

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        if not isinstance(args, dict):
            args = {}

        if isinstance(name, str) and name in tool_names:
            return name, args

    return None


def run_episode(
    env,
    tools_openai: List[Dict],
    task_message: str,
    *,
    max_steps: int = 25,
    model: str = "Qwen/Qwen3-1.7B",
    api_key: str | None = None,
    base_url: str | None = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Run one FinBench episode. Returns dict with step_count, done, reward."""
    from openai import OpenAI

    resolved_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("HF_TOKEN")
    resolved_url = base_url or os.environ.get("API_BASE_URL")
    # Auto-detect HF Inference: if key starts with hf_ and no base_url set
    if not resolved_url and resolved_key and resolved_key.startswith("hf_"):
        resolved_url = "https://router.huggingface.co/v1"
    client = OpenAI(api_key=resolved_key, base_url=resolved_url)

    tool_names = {t["function"]["name"] for t in tools_openai}
    required_by_tool = {
        t["function"]["name"]: set(t["function"].get("parameters", {}).get("required", []))
        for t in tools_openai
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task_message},
    ]
    agent_trace = []

    for step in range(1, max_steps + 1):
        if verbose:
            print(f"\n--- Step {step}/{max_steps} ---")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools_openai,
            tool_choice="auto",
            max_tokens=2048,
        )
        msg = response.choices[0].message

        # Parse tool call; fall back to text parser before forced submit.
        if msg.tool_calls:
            tc = msg.tool_calls[0]
            name = tc.function.name if tc.function.name in tool_names else "submit"
            raw_tool_arguments = tc.function.arguments or "{}"
            try:
                args = json.loads(raw_tool_arguments) if raw_tool_arguments else {}
            except json.JSONDecodeError:
                args = {}
            call_id = tc.id
        else:
            parsed = parse_text_tool_call(msg.content or "", tool_names)
            if parsed:
                name, args = parsed
                call_id = "text_tool_call"
                raw_tool_arguments = json.dumps(args)
                if verbose:
                    print("  Parsed text-based tool call fallback.")
            else:
                name, args, call_id = "submit", {}, "forced_submit"
                raw_tool_arguments = "{}"
                if verbose:
                    print(f"  Model text (no tool call): {(msg.content or '')[:150]}")

        if verbose:
            print(f"  → {name}({json.dumps(args)[:100]})")

        # Append assistant message
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}}
                for tc in (msg.tool_calls or [])
            ] or None,
        })

        required_fields = required_by_tool.get(name, set())
        missing_fields = sorted(
            field for field in required_fields
            if args.get(field, None) in (None, "")
        )
        if missing_fields:
            result_text = (
                f"Tool call validation error for {name}: missing required "
                f"argument(s): {', '.join(missing_fields)}. "
                "Retry with valid JSON arguments."
            )
            done = False
            reward = None
        else:
            # Execute in environment
            obs = env.step(CallToolAction(tool_name=name, arguments=args))
            result_text = obs_to_text(obs)
            done = getattr(obs, "done", False)
            reward = getattr(obs, "reward", None)

        if verbose:
            print(f"  ← {result_text[:200]}")

        # Append tool result
        messages.append({"role": "tool", "tool_call_id": call_id, "content": result_text[:6000]})
        agent_trace.append({
            "step": step,
            "assistant_text": (msg.content or "")[:1200],
            "tool_name": name,
            "tool_arguments": args,
            "raw_tool_arguments": raw_tool_arguments[:1200],
            "tool_result_preview": result_text[:1200],
        })

        if done:
            if verbose:
                print(f"\n  Episode done. Reward: {reward}")
            return {
                "step_count": step,
                "done": True,
                "reward": reward,
                "agent_trace": agent_trace,
            }

    return {
        "step_count": max_steps,
        "done": False,
        "reward": -0.1,
        "agent_trace": agent_trace,
    }


def main():
    parser = argparse.ArgumentParser(description="Run FinBench agent (one episode)")
    parser.add_argument("--task-id", default=None, help="Task ID from manifest")
    parser.add_argument("--max-steps", type=int, default=25)
    parser.add_argument("--model", default="Qwen/Qwen3-1.7B",
                        help="Model name (Qwen/Qwen3-1.7B, gpt-4o-mini, etc.)")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default=None,
                        help="API base URL (https://router.huggingface.co/v1 for HF)")
    parser.add_argument("--verbose", action="store_true", default=True)
    parser.add_argument("--no-verbose", dest="verbose", action="store_false")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    from finbench_env.client import FinBenchEnv

    env = FinBenchEnv(
        data_path=os.path.join(root, "data"),
        traces_dir=os.path.join(root, "traces"),
        max_steps=args.max_steps,
    )
    env._ensure_initialized()

    obs = env.reset(task_id=args.task_id)
    task_msg = obs.metadata.get("tool_result", "Explore the workspace.")
    current_task = getattr(env._env, "_current_task", {}) or {}
    expected = current_task.get("expected_deliverables", []) or []
    if expected:
        deliverable_lines = "\n".join(f"- output/{name}" for name in expected)
        task_msg = (
            f"{task_msg}\n\n"
            "Required deliverable filenames (use EXACT paths):\n"
            f"{deliverable_lines}\n"
        )

    sub_fields = current_task.get("submission_fields", []) or []
    if sub_fields:
        field_lines = []
        for sf in sub_fields:
            field_lines.append(f"- {sf['key']}: {sf['description']} (type: {sf['type']})")
        task_msg = (
            f"{task_msg}\n\n"
            "VERIFICATION FIELDS — when you call submit(), include submission_values JSON with these keys:\n"
            + "\n".join(field_lines)
            + "\nCompute these from your analysis and include them in submit(submission_values='{...}').\n"
        )

    list_obs = env.list_tools()
    mcp_tools = getattr(list_obs, "tools", [])
    if not mcp_tools:
        from finbench_env.models import AVAILABLE_TOOLS
        mcp_tools = [type("T", (), {"name": n, "description": n, "input_schema": {}})() for n in AVAILABLE_TOOLS]
    tools_openai = mcp_tools_to_openai(mcp_tools)

    if args.verbose:
        print(f"Model: {args.model}")
        print(f"Tools: {[t['function']['name'] for t in tools_openai]}")
        print(f"Task: {task_msg[:300]}")

    try:
        result = run_episode(
            env._env, tools_openai, task_msg,
            max_steps=args.max_steps, model=args.model,
            api_key=args.api_key, base_url=args.base_url,
            verbose=args.verbose,
        )
        print(f"\n{'='*50}")
        print(f"Steps: {result['step_count']}  Done: {result['done']}  Reward: {result['reward']}")
        print(f"{'='*50}")
    finally:
        env.close()


if __name__ == "__main__":
    main()
