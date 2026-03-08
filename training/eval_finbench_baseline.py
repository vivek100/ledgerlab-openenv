#!/usr/bin/env python3
"""Baseline evaluation runner for LedgerLab / FinBench manifests."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import run_agent as agent_runner

from finbench_env.client import FinBenchEnv
from training.common import DEFAULT_TRAIN_MANIFEST, DEFAULT_VAL_MANIFEST, augment_task_message, load_manifest_tasks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run baseline eval over LedgerLab manifests')
    parser.add_argument('--split', choices=['train', 'val'], default='val')
    parser.add_argument('--manifest', default=None)
    parser.add_argument('--task-id', action='append', default=[])
    parser.add_argument('--num-tasks', type=int, default=3)
    parser.add_argument('--max-steps', type=int, default=25)
    parser.add_argument('--model', default='Qwen/Qwen3-1.7B')
    parser.add_argument('--api-key', default=None)
    parser.add_argument('--base-url', default=None)
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument('--output-json', default=None)
    parser.add_argument('--log-to-wandb', action='store_true', default=False)
    parser.add_argument('--wandb-project', default=None)
    parser.add_argument('--wandb-entity', default=None)
    parser.add_argument('--wandb-run-name', default=None)
    return parser.parse_args()


def resolve_manifest(args: argparse.Namespace) -> Path:
    if args.manifest:
        return Path(args.manifest)
    return DEFAULT_TRAIN_MANIFEST if args.split == 'train' else DEFAULT_VAL_MANIFEST


def evaluate_task(task: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    env = FinBenchEnv(
        data_path=str(ROOT / 'data'),
        traces_dir=str(ROOT / 'traces'),
        max_steps=args.max_steps,
    )
    env._ensure_initialized()
    try:
        obs = env.reset(task_json=json.dumps(task), episode_id=f"eval_{task['task_id']}")
        task_message = obs.metadata.get('tool_result', task.get('prompt', 'Explore the workspace.'))
        task_message = augment_task_message(task_message, task)

        list_obs = env.list_tools()
        mcp_tools = getattr(list_obs, 'tools', [])
        tools_openai = agent_runner.mcp_tools_to_openai(mcp_tools)

        result = agent_runner.run_episode(
            env._env,
            tools_openai,
            task_message,
            max_steps=args.max_steps,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
            verbose=args.verbose,
        )

        submit_meta = getattr(env._env, '_last_submit_metadata', {}) or {}
        reward_breakdown = submit_meta.get('reward_breakdown', {}) or {}

        return {
            'task_id': task.get('task_id'),
            'prompt': task.get('prompt', '')[:300],
            'done': result['done'],
            'reward': result['reward'],
            'step_count': result['step_count'],
            'reward_breakdown': reward_breakdown,
        }
    finally:
        env.close()


def maybe_log_to_wandb(summary: Dict[str, Any], args: argparse.Namespace) -> None:
    if not args.log_to_wandb:
        return

    import wandb

    project = args.wandb_project or os.environ.get('WANDB_PROJECT') or 'ledgerlab'
    entity = args.wandb_entity or os.environ.get('WANDB_ENTITY')
    run = wandb.init(
        project=project,
        entity=entity,
        name=args.wandb_run_name,
        job_type='baseline_eval',
        config={
            'manifest': summary['manifest'],
            'model': summary['model'],
            'split': args.split,
            'num_tasks': summary['num_tasks'],
            'max_steps': args.max_steps,
        },
    )

    table = wandb.Table(columns=['task_id', 'done', 'reward', 'step_count'])
    for item in summary['results']:
        table.add_data(item['task_id'], bool(item['done']), float(item['reward']), int(item['step_count']))

    wandb.log({
        'baseline/mean_reward': float(summary['mean_reward']),
        'baseline/min_reward': float(summary['min_reward']),
        'baseline/max_reward': float(summary['max_reward']),
        'baseline/done_rate': float(summary['done_rate']),
        'baseline/num_tasks': int(summary['num_tasks']),
        'baseline/results': table,
    })
    run.finish()


def main() -> None:
    args = parse_args()
    manifest_path = resolve_manifest(args)
    tasks = load_manifest_tasks(manifest_path)
    if args.task_id:
        wanted = set(args.task_id)
        tasks = [task for task in tasks if task.get('task_id') in wanted]
    else:
        tasks = tasks[:args.num_tasks]

    if not tasks:
        raise RuntimeError(f'No tasks selected from {manifest_path}')

    results = [evaluate_task(task, args) for task in tasks]
    rewards = [float(item.get('reward') or 0.0) for item in results]
    done_rate = sum(1 for item in results if item.get('done')) / len(results)

    summary = {
        'manifest': str(manifest_path),
        'model': args.model,
        'num_tasks': len(results),
        'mean_reward': statistics.fmean(rewards) if rewards else 0.0,
        'min_reward': min(rewards) if rewards else 0.0,
        'max_reward': max(rewards) if rewards else 0.0,
        'done_rate': done_rate,
        'results': results,
    }

    print(json.dumps(summary, indent=2, default=str))
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(summary, indent=2, default=str), encoding='utf-8')
    maybe_log_to_wandb(summary, args)


if __name__ == '__main__':
    main()
