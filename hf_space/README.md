---
title: LedgerLab
emoji: 📊
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# LedgerLab

LedgerLab is a memory-first Jupyter workspace environment for training long-horizon business agents with OpenEnv.

This project targets the OpenEnv hackathon theme of long-horizon instruction following and business workflows. The environment forces an agent to work through realistic spreadsheet and document tasks by inspecting reference files, creating notebooks, running iterative analysis, producing deliverables, and finally submitting for reward.

## What The Agent Actually Does

Each episode gives the agent a task workspace with reference artifacts such as:
- Excel workbooks
- Word documents
- tabular business data
- prior memory snippets or reusable templates

The agent must then:
1. inspect the workspace and understand the task
2. create a Jupyter notebook and analyze the data incrementally
3. write or update output files in the workspace
4. use memory when it helps across similar episodes
5. submit the final state for reward

This is not a single-shot QA benchmark. It is a stateful tool-use environment with delayed reward and real file mutations.

## Why This Environment Exists

Most agent benchmarks collapse long tasks into one prompt or judge only final text. LedgerLab instead evaluates whether an agent can sustain a workflow over multiple steps:
- explore before acting
- recover from mistakes
- maintain useful intermediate state
- use notebooks as a working memory surface
- produce concrete deliverables instead of only explanations

That makes it a better fit for RL on realistic business workflows.

## Environment Design

LedgerLab is built on OpenEnv `0.2.1` and exposed as an MCP-compatible environment server.

Core properties:
- stateful per-session workspace
- notebook-first interaction model
- persistent memory bank across episodes
- reward based on both process and outcome
- real deliverable creation in the workspace

## Tooling Surface

The environment exposes 18 tools.

Workspace tools:
- `list_files`
- `read_file`
- `write_file`
- `create_folder`
- `search_files`

Notebook tools:
- `create_notebook`
- `read_notebook`
- `add_cell`
- `edit_cell`
- `delete_cell`
- `run_cell`
- `write_and_run`
- `run_all`

Kernel tool:
- `get_kernel_state`

Memory tools:
- `save_to_memory`
- `list_memory`
- `load_from_memory`

Control tool:
- `submit`

## Reward Logic

Reward is designed to avoid rewarding random output.

The scorer combines several signals:
- rubric and answer correctness for task-specific target fields
- structural completion checks
- consistency between generated artifacts and expected outputs
- execution quality, such as exploring files, using notebooks, and producing deliverables
- memory and process quality
- depth bonuses for richer trajectories

This gives partial credit for meaningful work while still reserving the highest reward for correct task completion.

## Dataset Status

Current environment data includes:
- 46 curated GDPval-style spreadsheet tasks
- deterministic verified submission fields for all 46 tasks
- train and validation manifests for training workflows

The tasks emphasize long-horizon business operations such as:
- inventory analysis
- location and logistics reconciliation
- planning sheets
- scheduling
- leasing and financial workbook editing
- operations reporting

## Deployment Interface

This Space hosts the environment server only.

Useful endpoints:
- health: `/health`
- OpenAPI docs: `/docs`
- MCP/OpenEnv websocket session endpoint: `/ws`

The intended use is to connect an OpenEnv-compatible client or agent runner to this deployed environment.

## Example Client Use

```python
from finbench_env.client import FinBenchRemoteEnv

with FinBenchRemoteEnv(base_url="https://weebhek-ledgerlab.hf.space").sync() as env:
    reset_result = env.reset(episode_id="demo")
    tools = env.list_tools()
    files = env.call_tool("list_files", path="reference")
```

## Local And Training Workflow

This Space is the deployment target for the environment.

Training is intended to run separately on GPU infrastructure, for example:
- Northflank H100 jobs for rollout generation and GRPO smoke training
- baseline evaluation with a stronger remote model
- smaller trainable models for RL fine-tuning

## Hackathon Submission Context

This project is aimed at the OpenEnv hackathon requirements:
- OpenEnv-based environment deployed on Hugging Face Spaces
- long-horizon business workflow setting
- coherent reward shaping for RL
- support for minimal training runs showing reward improvement

## Repo Notes

If you are a judge or reviewer, the key thing to evaluate is not just the final answer. The environment is designed to show whether an agent can operate like an analyst in a persistent notebook workspace over a multi-step trajectory.
