# LedgerLab

LedgerLab is an OpenEnv environment for training notebook-driven business agents on long-horizon professional tasks.

The agent works inside a real workspace with reference files, Jupyter notebooks, persistent memory, and a deterministic reward function tied to deliverables and verified answers. The environment is built for the OpenEnv Hackathon and is aligned to:
- Statement 2: (Super) Long-Horizon Planning and Instruction Following
- Statement 3.1: World Modeling / Professional Tasks
- Partner sub-themes: Scale AI and Mercor

## Submission Links
- Hugging Face Space: https://huggingface.co/spaces/weebhek/ledgerlab
- GitHub repo: https://github.com/vivek100/ledgerlab-openenv
- Space README: [hf_space/README.md](hf_space/README.md)
- Colab training notebook: [training/ledgerlab_trl_minimal_training_colab.ipynb](training/ledgerlab_trl_minimal_training_colab.ipynb)
- Minimal Colab guide: [docs/COLAB_SUBMISSION_GUIDE.md](docs/COLAB_SUBMISSION_GUIDE.md)

## What We Are Submitting For
### Statement 2: Long-Horizon Planning and Instruction Following
Why LedgerLab fits:
- episodes require multi-step tool use, not single-shot QA
- reward is sparse and delayed until `submit`
- the agent must inspect files, create notebooks, iterate on analysis, and recover from mistakes
- the workspace outlives any single model completion and pushes beyond simple context-window reasoning

Relevant implementation:
- Environment server: [finbench_env/server/finbench_environment.py](finbench_env/server/finbench_environment.py)
- Notebook execution: [finbench_env/server/notebook_executor.py](finbench_env/server/notebook_executor.py)
- Agent loop: [scripts/run_agent.py](scripts/run_agent.py)
- Training entrypoint: [training/train_finbench_grpo.py](training/train_finbench_grpo.py)

### Statement 3.1: World Modeling / Professional Tasks
Why LedgerLab fits:
- tasks are grounded in realistic spreadsheet and document workflows
- the agent operates in a partially observable workspace and must build state from files and tool outputs
- success depends on maintaining consistent internal state across a real multi-step workflow
- outputs are deliverables, not just text answers

Relevant implementation:
- Workspace tools: [finbench_env/server/workspace.py](finbench_env/server/workspace.py)
- Memory system: [finbench_env/server/memory.py](finbench_env/server/memory.py)
- Trace logging: [finbench_env/server/trace.py](finbench_env/server/trace.py)
- Task data: [data/tasks/task_manifest.json](data/tasks/task_manifest.json)

### Partner Sub-Themes
#### Scale AI
Why it fits:
- the environment is explicitly about long-horizon business workflows in non-code settings
- tasks include reporting, inventory analysis, scheduling, leasing, location reconciliation, and spreadsheet operations

#### Mercor
Why it fits:
- the reward has both capped and uncapped structure
- capped components score correctness and task completion
- uncapped depth bonuses reward richer analysis trajectories

Relevant implementation:
- Reward function: [finbench_env/server/rewards.py](finbench_env/server/rewards.py)
- Reward redesign notes: [docs/REWARD_REDESIGN.md](docs/REWARD_REDESIGN.md)

## Three Core Challenges We Solved
### 1. Long-horizon notebook execution
Most environments stop at text answers. LedgerLab forces the agent to work like an analyst:
- inspect files
- create notebooks
- run cells iteratively
- react to outputs and errors
- produce a final artifact

Code:
- [finbench_env/server/notebook_executor.py](finbench_env/server/notebook_executor.py)
- [finbench_env/server/finbench_environment.py](finbench_env/server/finbench_environment.py)

### 2. Deterministic reward on real deliverables
We did not want vague LLM-judge scoring. The environment checks concrete task signals:
- structural rubric checks
- submission field verification
- consistency between output files and submitted values
- execution quality and memory/process checks

Code and data:
- [finbench_env/server/rewards.py](finbench_env/server/rewards.py)
- [data/tasks/task_manifest.json](data/tasks/task_manifest.json)
- [scripts/generate_fields_llm.py](scripts/generate_fields_llm.py)

### 3. Reusable memory and workflow behavior
The agent can save and reuse notebook templates and intermediate workflow patterns across episodes.

Code:
- [finbench_env/server/memory.py](finbench_env/server/memory.py)
- [finbench_env/server/finbench_environment.py](finbench_env/server/finbench_environment.py)

## Environment Overview
LedgerLab exposes 18 tools across workspace, notebook, memory, and control surfaces.

Tool families:
- Workspace: `list_files`, `read_file`, `write_file`, `create_folder`, `search_files`
- Notebook: `create_notebook`, `read_notebook`, `add_cell`, `edit_cell`, `delete_cell`, `run_cell`, `write_and_run`, `run_all`
- Kernel: `get_kernel_state`
- Memory: `save_to_memory`, `list_memory`, `load_from_memory`
- Control: `submit`

Key files:
- Environment app: [finbench_env/server/app.py](finbench_env/server/app.py)
- Environment core: [finbench_env/server/finbench_environment.py](finbench_env/server/finbench_environment.py)
- Client: [finbench_env/client.py](finbench_env/client.py)
- OpenEnv spec: [finbench_env/openenv.yaml](finbench_env/openenv.yaml)

## Dataset And Training Data
Current dataset status:
- `46` curated GDPval-style tasks
- deterministic verified `submission_fields` for all `46`
- train/validation split: `34 / 12`

Important data files:
- Full manifest: [data/tasks/task_manifest.json](data/tasks/task_manifest.json)
- Train split: [data/tasks/train_manifest.json](data/tasks/train_manifest.json)
- Validation split: [data/tasks/val_manifest.json](data/tasks/val_manifest.json)
- Workspace examples: [data/tasks/workspaces](data/tasks/workspaces)

Supporting docs:
- Dataset scaling: [docs/DATASET_SCALING.md](docs/DATASET_SCALING.md)
- Data organization: [docs/DATA_ORGANIZATION.md](docs/DATA_ORGANIZATION.md)
- Submission-field generation: [docs/LLM_FIELD_EXTRACTION.md](docs/LLM_FIELD_EXTRACTION.md)

## Training
LedgerLab training uses Hugging Face TRL with GRPO.

Training assets:
- Main HF TRL script: [training/train_finbench_grpo.py](training/train_finbench_grpo.py)
- Shared helpers: [training/common.py](training/common.py)
- Baseline evaluation: [training/eval_finbench_baseline.py](training/eval_finbench_baseline.py)
- Minimal Colab notebook: [training/ledgerlab_trl_minimal_training_colab.ipynb](training/ledgerlab_trl_minimal_training_colab.ipynb)
- Training runbook: [docs/TRAINING_RUNBOOK.md](docs/TRAINING_RUNBOOK.md)
- Training results log: [docs/TRAINING_RESULTS.md](docs/TRAINING_RESULTS.md)

Northflank / H100 job assets:
- Training launcher: [scripts/run_h100_training_only.sh](scripts/run_h100_training_only.sh)
- Staged training launcher: [scripts/run_h100_training_staged.sh](scripts/run_h100_training_staged.sh)
- vLLM evaluation launcher: [scripts/run_h100_vllm_eval.sh](scripts/run_h100_vllm_eval.sh)
- Training job config: [northflank/ledgerlab_training_job.json](northflank/ledgerlab_training_job.json)
- vLLM eval job config: [northflank/ledgerlab_vllm_eval_job.json](northflank/ledgerlab_vllm_eval_job.json)

## Current Status
What is done:
- environment implemented and running locally in Docker
- Hugging Face Space packaging implemented
- dataset scaled to `46` tasks with deterministic reward questions
- HF TRL training pipeline implemented and exercised on H100
- W&B logging and model artifact persistence implemented
- minimal Colab HF TRL notebook prepared for submission

What is still being finalized:
- fair `Qwen/Qwen3-1.7B` base-model vLLM evaluation
- trained-checkpoint vLLM evaluation on the same validation split
- final before/after metric snapshot for README and demo

Placeholder results block:
- Base 1.7B vLLM eval: `TBD`
- Fine-tuned checkpoint vLLM eval: `TBD`
- Final before/after reward comparison: `TBD`

## How To Demo This Project
### Environment demo
- Space: https://huggingface.co/spaces/weebhek/ledgerlab
- Health endpoint: `https://weebhek-ledgerlab.hf.space/health`

### Minimal training demo
- Use the Colab notebook: [training/ledgerlab_trl_minimal_training_colab.ipynb](training/ledgerlab_trl_minimal_training_colab.ipynb)
- Guide: [docs/COLAB_SUBMISSION_GUIDE.md](docs/COLAB_SUBMISSION_GUIDE.md)

### Full project docs
- Master plan: [docs/MASTER_PLAN.md](docs/MASTER_PLAN.md)
- Phase tracking: [docs/PHASES.md](docs/PHASES.md)
- Submission plan: [docs/SUBMISSION_PLAN.md](docs/SUBMISSION_PLAN.md)
- Deployment and training plan: [docs/DEPLOYMENT_TRAINING_PLAN.md](docs/DEPLOYMENT_TRAINING_PLAN.md)

## How To Defend It In Judging
If asked what is novel or difficult here, the clean answer is:
1. this is a notebook-first OpenEnv environment for long-horizon business work, not a single-shot QA benchmark
2. the reward is grounded in deterministic task fields and deliverable checks, not only subjective judging
3. the training pipeline is real HF TRL GRPO, with H100 runs, W&B tracking, and a Colab notebook for the required minimal demo

## Local Quick Start
```bash
cd ReactAgentEnv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ../OpenEnv
pip install -r training/requirements-smoke.txt
python scripts/test_e2e.py
```
