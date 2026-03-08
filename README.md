# FinBench — Notebook-Driven Financial Analysis Agent Environment

An **OpenEnv** reinforcement learning environment that trains agents to work like
data analysts — creating Jupyter notebooks, running cells iteratively, reading data,
and producing deliverables evaluated against [GDPval](https://huggingface.co/datasets/openai/gdpval) rubrics.

## What This Does

Agents interact with a workspace through **18 MCP tools** to:

1. **Explore data** — read Excel/CSV files, search across workspace
2. **Create notebooks** — add/edit/run cells with a persistent Jupyter kernel
3. **Produce deliverables** — write Excel reports, summaries, analysis files
4. **Learn from memory** — load/save notebook templates across episodes
5. **Get multi-tier rewards** — rubric accuracy + execution quality + memory usage

## Architecture

```
Agent (LLM)  ←── MCP protocol ──→  FinBench (OpenEnv MCPEnvironment)
     │                                      │
     │ CallToolAction(tool, args)           │ 18 tools:
     │                                      │  Workspace: list_files, read_file, write_file,
     │                                      │             create_folder, search_files
     │                                      │  Notebook:  create_notebook, read_notebook,
     │                                      │             add_cell, edit_cell, delete_cell,
     │                                      │             run_cell, write_and_run, run_all
     │                                      │  Kernel:    get_kernel_state
     │                                      │  Memory:    save_to_memory, list_memory,
     │                                      │             load_from_memory
     │                                      │  Control:   submit
     └──── reward ◄─────────────────────────┘
           Capped: rubric(0.5) + exec_quality(0.25) + memory(0.25)
           Uncapped: depth bonus
```

## Quick Start

```bash
# 1. Set up virtual environment
cd ReactAgentEnv
python3 -m venv .venv
source .venv/bin/activate

# 2. Install OpenEnv core (from local repo)
pip install -e ../OpenEnv

# 3. Install env dependencies
pip install nbformat jupyter_client ipykernel pandas openpyxl openai

# 4. Create test data (3 synthetic tasks with rubrics)
python scripts/create_test_data.py

# 5. Run smoke test
python scripts/test_e2e.py

# 6. Test with real task + rubric scoring
python scripts/test_with_task.py
```

## Using the Client (Python)

```python
from finbench_env.client import FinBenchEnv

env = FinBenchEnv(data_path="./data", max_steps=30)
obs = env.reset(task_id="task_001")
print(obs.metadata["tool_result"])

# MCP tool calls
obs = env.call_tool("list_files", path="/reference")
obs = env.call_tool("create_notebook", path="work/analysis.ipynb")
obs = env.call_tool("write_and_run",
    notebook="work/analysis.ipynb",
    source="import pandas as pd\ndf = pd.read_excel('reference/data.xlsx')\nprint(df.head())")
obs = env.call_tool("submit")
print(f"Reward: {obs.reward}")
```

## Running the Server

```bash
uvicorn finbench_env.server.app:app --host 0.0.0.0 --port 8000
```

## Deploying to a Hugging Face Space (Docker)

1. **Create the Space** at [huggingface.co/new-space](https://huggingface.co/new-space): choose **SDK: Docker**, **Hardware: CPU Basic**.
2. **Create a write token** at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
3. **Build the bundle and push** (replace `YOUR_USERNAME` and `YOUR_SPACE_NAME`):

```bash
cd ReactAgentEnv
source .venv/bin/activate
python scripts/prepare_hf_space_bundle.py   # creates dist/hf_space/

cd ..
git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME hf-finbench-space
rsync -av --delete ReactAgentEnv/dist/hf_space/ hf-finbench-space/
cd hf-finbench-space
git add .
git commit -m "Update FinBench Space bundle"
git push   # use HF username + write token as password
```

Or use the one-shot script (e.g. for Space name **ledgerlab**):

```bash
export HF_USERNAME=your_hf_username
export HF_SPACE_NAME=ledgerlab
./scripts/push_to_hf_space.sh
```

After the Space builds, check: `curl https://YOUR_USERNAME-ledgerlab.hf.space/health`

Full step-by-step instructions (including LedgerLab naming): [docs/HF_SPACE_DEPLOY.md](docs/HF_SPACE_DEPLOY.md)

## Project Structure

```
ReactAgentEnv/
├── finbench_env/                  # The OpenEnv environment
│   ├── __init__.py
│   ├── models.py                  # FinBenchState (extends openenv State)
│   ├── client.py                  # Local client with call_tool() API
│   ├── server/
│   │   ├── app.py                 # FastAPI entry (create_app pattern)
│   │   ├── finbench_environment.py # MCPEnvironment + 18 FastMCP tools
│   │   ├── notebook_executor.py   # Jupyter kernel + nbformat
│   │   ├── workspace.py           # File ops + search
│   │   ├── memory.py              # Persistent memory bank
│   │   ├── trace.py               # Structured action logging
│   │   └── rewards.py             # 3-signal reward (structural + submission + consistency)
│   ├── openenv.yaml               # OpenEnv spec
│   └── pyproject.toml             # Package deps
├── data/
│   ├── tasks/                     # Curated GDPval tasks
│   │   ├── task_manifest.json
│   │   └── workspaces/{task_id}/reference/
│   ├── memory_seed/               # Pre-seeded memory templates
│   └── _persistent_memory/        # Agent-grown memory (persists across episodes)
├── traces/                        # Episode traces (JSON)
├── scripts/
│   ├── test_e2e.py                # Smoke test (all 18 tools)
│   ├── test_with_task.py          # Full task test with rubric scoring
│   ├── create_test_data.py        # Generate 3 synthetic tasks
│   ├── run_agent.py               # Inference agent (OpenAI-compatible)
│   └── generate_submission_fields.py  # Extract gold values for submission fields
├── docs/
│   ├── MASTER_PLAN.md             # Full design document
│   ├── PHASES.md                  # Phase-by-phase implementation plan
│   ├── REWARD_REDESIGN.md         # Reward function redesign rationale
│   └── SUBMISSION_PLAN.md         # Hackathon checklist & roadmap
└── training/
    └── train_finbench_grpo.py     # TRL GRPO training (Qwen3-1.7B)
```

## Reward System (3-Signal Architecture)

The reward function uses three deterministic signals to evaluate the agent's
output, replacing the previous naive NL rubric matching.

See [`docs/REWARD_REDESIGN.md`](docs/REWARD_REDESIGN.md) for full design rationale.

### Rubric Score (0.50 total weight)

| Signal | Weight | What it measures |
|--------|--------|------------------|
| **Structural** | 0.25 | File exists, headers present, row counts, column completeness — auto-parsed from rubric NL |
| **Submission Fields** | 0.60 | 3-5 key numeric/text values the agent must report at submit time, compared to gold file answers |
| **Consistency** | 0.15 | Cross-check that submitted values appear in the agent's actual output Excel file |

### Other Signals

| Component | Weight | What it measures |
|-----------|--------|------------------|
| **Execution Quality** | 0.25 | 8 binary checks: explored workspace, read refs first, created notebook, used search, 3+ cells, error recovery, verified output, produced deliverable |
| **Memory & Process** | 0.25 | 8 binary checks: read templates, self-referenced, organized workspace, documented work, structured notebooks, created intermediates, saved to memory, checked state |
| **Depth Bonus** | uncapped | +0.1 per reference file read, +0.1 per deep notebook, +0.1 per edit, +0.2 for saving to memory |

### How Submission Fields Work

Each task in `task_manifest.json` defines `submission_fields` — structured
questions the agent must answer from its analysis:

```json
{
  "submission_fields": [
    {"key": "total_shipped_cost", "type": "number", "description": "Total shipped $ at cost", "expected": 140008.20, "tolerance": 1.0},
    {"key": "po_row_count", "type": "integer", "description": "Number of PO data rows", "expected": 67}
  ]
}
```

The agent sees these as verification questions in its prompt and provides answers
via `submit(submission_values='{"total_shipped_cost": 140008.20, "po_row_count": 67}')`.
This is the primary correctness signal (60% of rubric weight).

## OpenEnv Patterns Used

This environment follows the exact patterns from `envs/finqa_env/` and `envs/echo_env/`:

- **`MCPEnvironment`** base class — auto-routes `ListToolsAction`/`CallToolAction`
- **`FastMCP`** tool registration — `@mcp.tool` decorators in `__init__`
- **`create_app(factory, ActionCls, ObsCls)`** — standard OpenEnv server pattern
- **`CallToolAction`/`CallToolObservation`** — standard MCP action/observation types

## Hackathon Problem Statements

- **Statement 2:** Long-Horizon Planning & Instruction Following
- **Statement 3.1:** Professional Services Tasks
- **Mercor:** Capped + uncapped rewards scaling with output quality
- **Scale AI:** Long-horizon business workflows with verifiable rubrics

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'openenv'` | `pip install -e /path/to/OpenEnv` |
| `No module named 'fastmcp'` | Comes with `openenv-core[core]` |
| Kernel won't start | `pip install ipykernel` in your venv |
| Cell outputs out of order | Fixed — iopub drain + parent_header filtering |

## Running the Agent

```bash
# HF Inference (small trainable model)
export HF_TOKEN=...
python scripts/run_agent.py --model Qwen/Qwen3-1.7B --base-url https://router.huggingface.co/v1

# OpenAI (quick testing)
export OPENAI_API_KEY=...
python scripts/run_agent.py --model gpt-4o-mini

# Local vLLM
python scripts/run_agent.py --model Qwen/Qwen3-1.7B --base-url http://localhost:8000/v1 --api-key dummy
```

### Agent Reliability Updates (Phase 1)

- `scripts/run_agent.py` now appends exact required deliverable filenames from the task metadata to the user task message (for example `output/PO Log June Ships.xlsx`).
- The agent loop now validates required tool arguments before calling MCP tools and returns a retryable validation error instead of letting malformed calls break execution.
- The agent loop includes a text-based tool-call fallback parser for models that output tool calls in text when `tool_calls` is empty.
- Notebook tool responses are now more actionable:
  - `create_notebook` returns a concrete `write_and_run(...)` example using the exact notebook path.
  - `write_and_run` now includes `notebook_summary` with current `cell_count`, recent `cell_id`s, and append guidance.

No LangGraph needed — uses the same OpenAI function-calling pattern as `OpenEnv/examples/finqa_inference.py`.

### Test Results

| Model | Task | Steps | Reward | Submission Score | Notes |
|-------|------|-------|--------|-----------------|-------|
| Qwen3-235B | PO Log June Ships | 22/30 | 0.6313 | 0.50 (2/4 fields) | Created file, submitted values, partial correctness |
| Qwen2.5-72B | PO Log June Ships | 20/25 | timeout | — | Got stuck debugging Excel column parsing |

## Training (TRL GRPO)

```bash
pip install trl vllm
python training/train_finbench_grpo.py  # H100 with vLLM
```

Trains `Qwen/Qwen3-1.7B` with GRPO — each rollout is one FinBench episode.
Same pattern as the [OpenEnv Wordle GRPO tutorial](https://github.com/huggingface/trl/blob/main/examples/notebooks/openenv_wordle_grpo.ipynb).

## Docs

- **`docs/SUBMISSION_PLAN.md`** — Hackathon checklist, judging criteria, full roadmap
- **`docs/PHASES.md`** — Phase-by-phase build status
- **`docs/REWARD_REDESIGN.md`** — Reward function redesign: why 3 signals, what changed, design rationale

## References

- [GDPval Dataset](https://huggingface.co/datasets/openai/gdpval)
- [OpenEnv Framework](https://github.com/meta-pytorch/OpenEnv)
- [OpenEnv Tutorial: Training](OpenEnv/tutorial/04-training.md)
- [TRL OpenEnv](https://huggingface.co/docs/trl/main/en/openenv)
- [APEX-Agents](https://arxiv.org/abs/2601.14242) (rubric inspiration)
