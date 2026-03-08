# FinBench ? Hackathon Submission and Delivery Plan

## Current Status

Hackathon-relevant status right now:
- OpenEnv environment implemented
- dataset expanded to `46` xlsx GDPval tasks
- all tasks have deterministic verified `submission_fields`
- split manifests exist for train and validation
- main agent runner works
- reward system has already been exercised by a large-model baseline run

## Required Deliverables

| Requirement | Plan | Current Status |
|-------------|------|----------------|
| OpenEnv-based environment | FinBench env in `finbench_env/` | Complete |
| Deploy on HF Spaces | Docker Space deployment of the environment | Not started |
| Minimal training script | TRL GRPO script + smoke run evidence | Script exists, run pending |
| One-minute demo video | Record after env + training smoke are working | Not started |
| Public repo | Ensure final repo visibility before submit | Pending |

## Final Delivery Sequence

The delivery order should be:
1. local Docker environment validation
2. HF Space deployment validation
3. Northflank H100 training smoke run
4. reward / trace screenshots or logs
5. demo recording
6. final submission packaging

This order reduces risk because it separates packaging, deployment, and training concerns.

## What We Need To Show Judges

### Environment
- the environment running on HF Spaces
- real task reset / tool use / submit
- reward breakdown returned by the environment

### Training
- a minimal training script using TRL
- evidence that rewards are being produced during rollouts
- ideally a before/after or short improvement signal

### Story
- notebook-centric professional workflow
- deterministic reward verification
- long-horizon business tasks

## Infrastructure Decision

### HF Spaces
Use for:
- final deployed environment for judges

### Northflank H100
Use for:
- baseline evaluation
- short RL smoke training
- real training runs if time permits

### Fallback
If HF Space has deployment issues:
- run the environment colocated on Northflank for testing and training
- keep HF Space as a packaging milestone, not a blocker for progress

## Execution Checklist

### Packaging and Deploy
- [ ] Create Dockerized env image
- [ ] Run env locally in Docker
- [ ] Verify client connectivity locally
- [ ] Deploy Docker env to HF Space
- [ ] Verify remote connectivity

### Training
- [ ] Make training script use split manifests explicitly
- [ ] Add small baseline eval pass
- [ ] Run short H100 smoke job
- [ ] Inspect rewards, traces, and logs

### Demo and Submit
- [ ] Capture working env demo
- [ ] Capture training smoke evidence
- [ ] Record 1-minute video
- [ ] Verify repo is public
- [ ] Submit links and description

## Immediate Next Step

The immediate next implementation step is Dockerizing the environment and validating it locally.

That is the correct next step because:
- the dataset work is complete
- the reward path is already partially exercised
- deployment packaging is now the highest-risk unresolved area
