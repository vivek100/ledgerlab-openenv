#!/usr/bin/env python3
"""GRPO training entrypoint for LedgerLab / FinBench."""

from __future__ import annotations

import argparse
import json
import os
import sys
from inspect import signature
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openenv.core.env_server.mcp_types import CallToolAction

from training.common import (
    DEFAULT_TRAIN_MANIFEST,
    DEFAULT_VAL_MANIFEST,
    augment_task_message,
    build_task_record,
    create_env,
    load_manifest_tasks,
    parse_task_record,
)

MODEL_NAME = "Qwen/Qwen3-1.7B"
SYSTEM_PROMPT = """You are a financial data analyst. You have a workspace with tools.

## Workspace (all paths are RELATIVE - no leading slash)
- reference/  - input data files (Excel, CSV). READ THESE FIRST.
- memory/     - saved notebook templates from past episodes.
- work/       - create notebooks and intermediate files here.
- output/     - final deliverables go here.

## How to work
1. list_files('reference') to see input data.
2. read_file('reference/filename.xlsx') to understand the data.
3. create_notebook('work/analysis.ipynb') then write_and_run to add and execute cells.
4. In notebook code, use RELATIVE paths like pd.read_excel('reference/data.xlsx') - NOT absolute paths.
5. Iterate: read output, edit_cell or add more cells. Check get_kernel_state.
6. Write final deliverable to output/ with write_file or from notebook code.
7. Call submit with both deliverable_paths AND submission_values (JSON with verification answers).

## Submission
When you call submit, you MUST provide submission_values - a JSON string with answers to the verification fields listed in the task. Example:
  submit(deliverable_paths='output/Report.xlsx', submission_values='{"total_revenue": 50000, "row_count": 120}')

IMPORTANT: All file paths are relative to the workspace root. Use 'reference/file.xlsx' not '/reference/file.xlsx'."""


def obs_to_text(obs: Any) -> str:
    if obs is None:
        return ""
    if hasattr(obs, "result") and obs.result is not None:
        result = obs.result
        if hasattr(result, "content") and result.content:
            return getattr(result.content[0], "text", str(result.content[0]))
        if hasattr(result, "data") and result.data is not None:
            return str(result.data)
        return str(result)
    if hasattr(obs, "metadata"):
        return str(obs.metadata.get("tool_result", obs.metadata))
    return str(obs)


def parse_tool_call(text: str, tool_names: set[str]) -> tuple[str, Dict[str, Any]]:
    text = (text or "").strip()
    for line in text.split("\n"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = payload.get("tool") or payload.get("tool_name") or payload.get("name", "")
        args = payload.get("arguments") or payload.get("args") or {}
        if isinstance(name, str) and name in tool_names and isinstance(args, dict):
            return name, args

    for name in tool_names:
        if name in text:
            return name, {}
    return "submit", {}


def make_user_prompt(task_text: str, history: List[Dict[str, str]]) -> str:
    hist_text = ""
    if history:
        hist_lines = [f"[Tool: {item['tool']}] -> {item['result'][:300]}" for item in history[-6:]]
        hist_text = "\n\nRecent actions:\n" + "\n".join(hist_lines)
    return (
        f"Task:\n{task_text}{hist_text}\n\n"
        'What tool should you call next? Reply with a JSON object: '
        '{"tool": "tool_name", "arguments": {...}}'
    )


def rollout_once(trainer, env, tokenizer, task_record: str, system_prompt: str, max_turns: int) -> Dict[str, Any]:
    from trl.experimental.openenv import generate_rollout_completions

    tool_names = {
        "list_files", "read_file", "write_file", "create_folder", "search_files",
        "create_notebook", "read_notebook", "add_cell", "edit_cell", "delete_cell",
        "run_cell", "write_and_run", "run_all", "get_kernel_state",
        "save_to_memory", "list_memory", "load_from_memory", "submit",
    }

    record = parse_task_record(task_record)
    task_json = record["task_json"]
    obs = env.reset(task_json=task_json)

    current_task = json.loads(task_json)
    task_text = obs.metadata.get("tool_result", record.get("task_prompt", ""))
    task_text = augment_task_message(task_text, current_task)

    prompt_ids: List[int] = []
    completion_ids: List[int] = []
    logprobs: List[float] = []
    history: List[Dict[str, str]] = []
    total_reward = 0.0
    rubric_reward = 0.0

    for _ in range(max_turns):
        user_prompt = make_user_prompt(task_text, history)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        prompt_text = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False,
            enable_thinking=False,
        )

        rollout_out = generate_rollout_completions(trainer, [prompt_text])[0]
        prompt_ids.extend(rollout_out["prompt_ids"])
        completion_ids.extend(rollout_out["completion_ids"])
        logprobs.extend(rollout_out["logprobs"])
        completion_text = rollout_out.get("text") or tokenizer.decode(
            rollout_out["completion_ids"], skip_special_tokens=True
        )

        tool_name, tool_args = parse_tool_call(completion_text, tool_names)
        obs = env.step(CallToolAction(tool_name=tool_name, arguments=tool_args))
        result_text = obs_to_text(obs)
        history.append({"tool": tool_name, "result": result_text})

        if getattr(obs, "done", False):
            total_reward = float(getattr(obs, "reward", 0.0) or 0.0)
            metadata = getattr(obs, "metadata", {}) or {}
            rubric_reward = float(metadata.get("rubric_score", 0.0))
            break

    return {
        "prompt_ids": prompt_ids,
        "completion_ids": completion_ids,
        "logprobs": logprobs,
        "total_reward": total_reward,
        "rubric_reward": rubric_reward,
    }


def rollout_func(prompts, trainer=None):
    from transformers import AutoTokenizer

    args = rollout_func.args
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    all_prompt_ids = []
    all_completion_ids = []
    all_logprobs = []
    total_rewards = []
    rubric_rewards = []

    for task_record in prompts:
        env = create_env(max_steps=args.max_turns, manifest_path=args.train_manifest)
        try:
            episode = rollout_once(
                trainer=trainer,
                env=env,
                tokenizer=tokenizer,
                task_record=task_record,
                system_prompt=SYSTEM_PROMPT,
                max_turns=args.max_turns,
            )
        finally:
            env.close()

        all_prompt_ids.append(episode["prompt_ids"])
        all_completion_ids.append(episode["completion_ids"])
        all_logprobs.append(episode["logprobs"])
        total_rewards.append(episode["total_reward"])
        rubric_rewards.append(episode["rubric_reward"])

    return {
        "prompt_ids": all_prompt_ids,
        "completion_ids": all_completion_ids,
        "logprobs": all_logprobs,
        "total_reward": total_rewards,
        "rubric_reward": rubric_rewards,
    }


def reward_total(completions, **kwargs):
    rewards = kwargs.get("total_reward")
    return [float(r) for r in rewards] if rewards else [0.0] * len(completions)


def reward_rubric(completions, **kwargs):
    rewards = kwargs.get("rubric_reward")
    return [float(r) for r in rewards] if rewards else [0.0] * len(completions)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LedgerLab/FinBench with GRPO")
    parser.add_argument("--model-name", default=MODEL_NAME)
    parser.add_argument("--output-dir", default="finbench-grpo-Qwen3-1.7B")
    parser.add_argument("--train-manifest", default=str(DEFAULT_TRAIN_MANIFEST))
    parser.add_argument("--val-manifest", default=str(DEFAULT_VAL_MANIFEST))
    parser.add_argument("--max-turns", type=int, default=15)
    parser.add_argument("--max-train-tasks", type=int, default=None)
    parser.add_argument("--repeats-per-task", type=int, default=2)
    parser.add_argument("--num-train-epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=16)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--warmup-steps", type=int, default=5)
    parser.add_argument("--num-generations", type=int, default=2)
    parser.add_argument("--max-completion-length", type=int, default=256)
    parser.add_argument("--max-prompt-length", type=int, default=4096)
    parser.add_argument("--use-vllm", action="store_true", default=True)
    parser.add_argument("--no-vllm", dest="use_vllm", action="store_false")
    parser.add_argument("--vllm-mode", default="colocate")
    parser.add_argument("--vllm-gpu-memory-utilization", type=float, default=0.3)
    parser.add_argument("--logging-steps", type=int, default=1)
    parser.add_argument("--save-steps", type=int, default=10)
    parser.add_argument("--push-to-hub", action="store_true", default=False)
    return parser.parse_args()


def main() -> None:
    from datasets import Dataset
    from transformers import AutoTokenizer
    from trl import GRPOConfig, GRPOTrainer

    args = parse_args()
    rollout_func.args = args

    train_tasks = load_manifest_tasks(args.train_manifest, limit=args.max_train_tasks)
    if not train_tasks:
        raise RuntimeError(f"No tasks loaded from train manifest: {args.train_manifest}")

    dataset_records: List[str] = []
    for task in train_tasks:
        record = build_task_record(task)
        dataset_records.extend([record] * max(1, args.repeats_per_task))

    dataset = Dataset.from_dict({"prompt": dataset_records})

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    tokenizer.pad_token = tokenizer.eos_token

    config_kwargs = {
        "num_train_epochs": args.num_train_epochs,
        "learning_rate": args.learning_rate,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "per_device_train_batch_size": args.per_device_train_batch_size,
        "warmup_steps": args.warmup_steps,
        "num_generations": args.num_generations,
        "max_completion_length": args.max_completion_length,
        "max_prompt_length": args.max_prompt_length,
        "use_vllm": args.use_vllm,
        "vllm_mode": args.vllm_mode,
        "vllm_gpu_memory_utilization": args.vllm_gpu_memory_utilization,
        "output_dir": args.output_dir,
        "logging_steps": args.logging_steps,
        "save_steps": args.save_steps,
        "gradient_checkpointing": True,
        "gradient_checkpointing_kwargs": {"use_reentrant": False},
        "push_to_hub": args.push_to_hub,
        "report_to": "wandb",
        "bf16": True,
    }
    supported_args = set(signature(GRPOConfig.__init__).parameters)
    filtered_kwargs = {k: v for k, v in config_kwargs.items() if k in supported_args}
    skipped_args = sorted(set(config_kwargs) - set(filtered_kwargs))
    if skipped_args:
        print(f"Skipping unsupported GRPOConfig args for installed TRL version: {', '.join(skipped_args)}")

    grpo_config = GRPOConfig(**filtered_kwargs)

    trainer = GRPOTrainer(
        model=args.model_name,
        processing_class=tokenizer,
        reward_funcs=[reward_total, reward_rubric],
        train_dataset=dataset,
        args=grpo_config,
        rollout_func=rollout_func,
    )

    print("Starting GRPO training...")
    print(f"Train manifest: {args.train_manifest}")
    print(f"Val manifest:   {args.val_manifest}")
    print(f"Train tasks:    {len(train_tasks)}")
    print(f"Dataset rows:   {len(dataset_records)}")

    trainer_stats = trainer.train()
    print("\nTraining complete.")
    print(f"  Runtime: {trainer_stats.metrics['train_runtime']:.0f}s")

    trainer.save_model(args.output_dir)
    print(f"Model saved to {args.output_dir}")


if __name__ == "__main__":
    main()

