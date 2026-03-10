# LedgerLab

LedgerLab is an OpenEnv environment for training notebook-driven business agents on long-horizon professional tasks. It models the real workflows of a financial analyst: reading spreadsheets, building notebooks, iterating on analysis, and producing deliverables — not just answering questions.

## What LedgerLab Models

Most agent benchmarks treat the world as a question-answering surface. LedgerLab treats it as a workspace. The agent operates in a partially observable environment with reference files, a live Jupyter kernel, persistent memory, and a reward function tied to concrete deliverables.

This design is grounded in how professional knowledge work actually happens:

- The analyst does not know in advance which files contain the right data
- Intermediate outputs change what steps come next
- Mistakes must be detected and corrected within the same session
- The final deliverable must be consistent with everything computed along the way

### The Agent's World

The agent starts each episode with a workspace containing business documents — spreadsheets, ledgers, inventory files, lease records, location data. It must build an accurate internal model of that workspace through tool use, then produce a verified output.

Key world-modeling demands:
- **Partial observability**: the agent must discover relevant data by inspecting files, not by being told what they contain
- **State accumulation**: information gathered in early steps must be carried forward correctly through notebook cells and memory
- **Consistency checking**: submitted answers are verified against intermediate computations, so the agent cannot hallucinate final values
- **Error recovery**: cell execution errors are real feedback the agent must interpret and act on

## Environment Design

### Tools

LedgerLab exposes 18 tools across four surfaces:

- **Workspace**: `list_files`, `read_file`, `write_file`, `create_folder`, `search_files`
- **Notebook**: `create_notebook`, `read_notebook`, `add_cell`, `edit_cell`, `delete_cell`, `run_cell`, `write_and_run`, `run_all`
- **Kernel**: `get_kernel_state`
- **Memory**: `save_to_memory`, `list_memory`, `load_from_memory`
- **Control**: `submit`

### Reward Structure

Reward is sparse and delayed until `submit`. The agent receives no signal for individual tool calls. The reward function checks:

- Structural rubric compliance
- Verified submission field values
- Consistency between output files and submitted answers
- Execution quality, memory use, and process checks

There is no LLM judge. All reward signals are deterministic and tied to the actual task deliverable.

Reward design: [finbench_env/server/rewards.py](finbench_env/server/rewards.py) · [docs/REWARD_REDESIGN.md](docs/REWARD_REDESIGN.md)

### Memory System

The agent can persist notebook templates and intermediate workflow patterns across episodes. This allows it to build reusable mental models of recurring task types rather than rediscovering structure from scratch each time.

Memory implementation: [finbench_env/server/memory.py](finbench_env/server/memory.py)

## Task Dataset

LedgerLab includes 46 curated tasks grounded in realistic business workflows:

- Inventory analysis and reconciliation
- Financial reporting and ledger review
- Scheduling and capacity planning
- Lease and location data reconciliation
- Spreadsheet operations and derived metrics

Each task has deterministic verified `submission_fields` — concrete values the agent must compute correctly.

| Split | Tasks |
|-------|-------|
| Train | 34 |
| Validation | 12 |

Key data files:
- Full manifest: [data/tasks/task_manifest.json](data/tasks/task_manifest.json)
- Train split: [data/tasks/train_manifest.json](data/tasks/train_manifest.json)
- Validation split: [data/tasks/val_manifest.json](data/tasks/val_manifest.json)
- Workspace examples: [data/tasks/workspaces](data/tasks/workspaces)

Supporting docs:
- [docs/DATASET_SCALING.md](docs/DATASET_SCALING.md)
- [docs/DATA_ORGANIZATION.md](docs/DATA_ORGANIZATION.md)
- [docs/LLM_FIELD_EXTRACTION.md](docs/LLM_FIELD_EXTRACTION.md)

## Training

LedgerLab uses Hugging Face TRL with GRPO. The sparse, delayed reward structure makes this a genuine reinforcement learning problem — the agent cannot learn by imitating single-step completions.

Training assets:
- Main script: [training/train_finbench_grpo.py](training/train_finbench_grpo.py)
- Shared helpers: [training/common.py](training/common.py)
- Baseline evaluation: [training/eval_finbench_baseline.py](training/eval_finbench_baseline.py)
- Colab notebook: [training/ledgerlab_trl_minimal_training_colab.ipynb](training/ledgerlab_trl_minimal_training_colab.ipynb)
- Training runbook: [docs/TRAINING_RUNBOOK.md](docs/TRAINING_RUNBOOK.md)
- Results log: [docs/TRAINING_RESULTS.md](docs/TRAINING_RESULTS.md)

H100 job configs:
- [scripts/run_h100_training_only.sh](scripts/run_h100_training_only.sh)
- [northflank/ledgerlab_training_job.json](northflank/ledgerlab_training_job.json)

## Key Implementation Files

| Component | File |
|-----------|------|
| Environment core | [finbench_env/server/finbench_environment.py](finbench_env/server/finbench_environment.py) |
| Notebook executor | [finbench_env/server/notebook_executor.py](finbench_env/server/notebook_executor.py) |
| Workspace tools | [finbench_env/server/workspace.py](finbench_env/server/workspace.py) |
| Memory system | [finbench_env/server/memory.py](finbench_env/server/memory.py) |
| Reward function | [finbench_env/server/rewards.py](finbench_env/server/rewards.py) |
| Trace logging | [finbench_env/server/trace.py](finbench_env/server/trace.py) |
| Agent loop | [scripts/run_agent.py](scripts/run_agent.py) |
| Environment app | [finbench_env/server/app.py](finbench_env/server/app.py) |
| Client | [finbench_env/client.py](finbench_env/client.py) |
| OpenEnv spec | [finbench_env/openenv.yaml](finbench_env/openenv.yaml) |

## Demo and Deployment

- Hugging Face Space: https://huggingface.co/spaces/weebhek/ledgerlab
- Health endpoint: `https://weebhek-ledgerlab.hf.space/health`
- Colab training guide: [docs/COLAB_SUBMISSION_GUIDE.md](docs/COLAB_SUBMISSION_GUIDE.md)

## Local Quick Start

```bash
cd ReactAgentEnv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ../OpenEnv
pip install -r training/requirements-smoke.txt
python scripts/test_e2e.py
```

## Further Reading

- [docs/MASTER_PLAN.md](docs/MASTER_PLAN.md)
- [docs/PHASES.md](docs/PHASES.md)
- [docs/DEPLOYMENT_TRAINING_PLAN.md](docs/DEPLOYMENT_TRAINING_PLAN.md)
