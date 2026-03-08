# Documentation Index

## Quick Links

| Document | Purpose |
|----------|---------|
| **[MASTER_PLAN.md](MASTER_PLAN.md)** | High-level status and overall project direction |
| **[PHASES.md](PHASES.md)** | Phase-by-phase implementation status |
| **[DEPLOYMENT_TRAINING_PLAN.md](DEPLOYMENT_TRAINING_PLAN.md)** | Detailed execution plan for Docker, HF Space, and H100 training (includes **Northflank CLI login** for GPU access) |
| **[SUBMISSION_PLAN.md](SUBMISSION_PLAN.md)** | Hackathon submission checklist and deliverable mapping |
| **[REWARD_REDESIGN.md](REWARD_REDESIGN.md)** | Reward system rationale and architecture |
| **[DATASET_SCALING.md](DATASET_SCALING.md)** | Final dataset scaling status |
| **[DATA_ORGANIZATION.md](DATA_ORGANIZATION.md)** | Current manifest and workspace layout |
| **[LLM_FIELD_EXTRACTION.md](LLM_FIELD_EXTRACTION.md)** | Final state of deterministic submission-field generation |

## Current Status

Current project state:
- environment exists and runs locally in Python
- `46/46` GDPval xlsx tasks are integrated
- `46/46` tasks have deterministic `submission_fields`
- split manifests exist: `34` train / `12` val / `0` test
- main inference runner works
- reward system has already been exercised with a large-model run

Current focus:
- Dockerize the environment
- validate locally
- deploy to Hugging Face Space
- prepare H100 training smoke runs on Northflank

## Recommended Reading Order

### For project execution right now
1. `DEPLOYMENT_TRAINING_PLAN.md`
2. `PHASES.md`
3. `SUBMISSION_PLAN.md`

### For contributors
1. `MASTER_PLAN.md`
2. `DATA_ORGANIZATION.md`
3. `REWARD_REDESIGN.md`

### For dataset context
1. `DATASET_SCALING.md`
2. `LLM_FIELD_EXTRACTION.md`
