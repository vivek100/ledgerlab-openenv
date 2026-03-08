# Deployment and Training Execution Plan

## Objective

Finish the hackathon path in the lowest-risk order:
1. package the environment as Docker
2. run the Docker image locally
3. deploy the same environment image to Hugging Face Spaces
4. verify remote connectivity from the client / agent runner
5. run a small RL smoke test on Northflank H100
6. use a colocated env on H100 as fallback if HF Space is unstable

This is the execution plan we should follow from this point onward.

## Current Starting Point

Current project state:
- environment exists and runs locally in Python
- `46/46` tasks have deterministic verified `submission_fields`
- split manifests exist: `34` train / `12` val / `0` test
- main inference runner exists: `scripts/run_agent.py`
- reward system has been exercised with a large-model run
- one scorer crash was found and fixed
- Northflank CLI is installed locally in WSL

## Core Decision

We will separate responsibilities:

### Hugging Face Space
Use for:
- deployed OpenEnv environment for judges
- remote environment validation
- final public demo target

Do not use HF Space as the first place to debug RL training.

### Northflank H100
Use for:
- baseline evaluation jobs
- GRPO smoke training
- real training runs
- fallback environment hosting if HF Space deployment has issues

## Recommended Deployment Shape

### Image A: Environment image
Purpose:
- local Docker validation
- Hugging Face Space deployment
- optional CPU fallback service anywhere else

Responsibilities:
- expose `finbench_env.server.app:app`
- include `data/`
- include environment dependencies only
- listen on port `8000`

### Image B: Training image
Purpose:
- Northflank H100 jobs

Responsibilities:
- install training dependencies (`trl`, `vllm`, torch stack, eval tooling)
- run baseline eval or GRPO jobs
- optionally start the env locally in-process or in-container
- write checkpoints/logs to mounted disk

We should not force HF Space and GPU training into the same image.

## Current Deployment Status

Validated locally:
- `Dockerfile.space` builds successfully
- local container works on `http://localhost:8000`
- generated Hugging Face Space bundle at `dist/hf_space/` builds successfully as a standalone Docker context
- bundle container works on `http://localhost:7860`
- remote smoke test passes against both local Docker targets

Current fallback posture:
- if Hugging Face Space deployment is delayed or unstable, the same Docker image can be run on Northflank as the environment host

Current remote deployment status:
- Hugging Face Space repo is created and the Docker image build completed successfully
- Space runtime is still pending investigation because it remains in `Starting`
- this is no longer the blocker because we can run the environment colocated with training on H100

Immediate next step:
- log into Northflank / H100 and run a tiny colocated eval + GRPO smoke test

## Infrastructure Recommendations

## Hugging Face Space

Type:
- Docker Space

Runtime:
- CPU is fine

Storage:
- no persistent volume required
- bundle the dataset in the image

Why:
- dataset is small
- judges need the environment endpoint, not local training weights
- simpler deployment is better

## Northflank H100

Type:
- GPU job, not long-running service, for the first training runs

GPU:
- `1x H100` is the right initial target

Disk:
- recommended: persistent disk
- minimum reasonable size: `50 GB`
- safer size: `100 GB`

Why disk matters:
- HF cache
- model cache
- logs
- checkpoints
- restart safety

Without disk, a smoke run is still possible, but it is not the recommended default.

## Model Strategy

### Big model baseline
Use a remote large model for evaluation only.
Example:
- `Qwen/Qwen3-235B-A22B-Instruct-2507` via HF router

Purpose:
- establish a strong baseline trajectory
- surface reward/scorer issues
- validate agent loop quality

### Trainable model
Use the small trainable model already wired in the repo.
Current recommendation:
- `Qwen/Qwen3-1.7B`

Purpose:
- GRPO smoke training
- demo of reward improvement
- manageable memory/runtime footprint on one H100

## Execution Order

## Phase A: Dockerize the environment

Goal:
- create the environment image and run it locally

Tasks:
1. create `Dockerfile.space` or equivalent environment Dockerfile
2. ensure it installs the environment package cleanly
3. ensure it bundles `data/`
4. ensure it launches the FastAPI server on port `8000`
5. verify local container boot

Definition of done:
- container starts locally
- health / API endpoint is reachable
- local client can connect
- one task can be reset and stepped successfully

## Phase B: Validate environment behavior locally through Docker

Goal:
- prove the Docker artifact works before any remote deploy

Tasks:
1. run the container locally
2. connect with `FinBenchEnv` or `scripts/run_agent.py`
3. verify tools list
4. run at least one task end-to-end
5. verify traces and reward response

Definition of done:
- same image works locally without source-tree assumptions
- reward path completes without crashing

## Phase C: Deploy the environment to Hugging Face Space

Goal:
- push the Dockerized environment to HF Spaces

Tasks:
1. create Docker Space
2. add required secrets if needed
3. push Docker-based app
4. verify the Space boots
5. verify OpenEnv route is reachable
6. connect from local client to remote Space

Definition of done:
- remote Space responds correctly
- client can reset and step against it
- at least one remote smoke episode works

## Phase D: Prepare the training image and H100 workflow

Goal:
- make the training path reproducible

Tasks:
1. create `Dockerfile.train`
2. make training script explicitly manifest-aware
3. make validation script explicitly manifest-aware
4. define checkpoint/log output paths
5. define mounted disk paths

Definition of done:
- training container builds
- smoke eval command works
- smoke GRPO command starts on H100

## Phase E: Run a small H100 smoke test

Goal:
- confirm the training loop works before scaling

Recommended first smoke run:
1. small baseline eval over a few tasks
2. very short GRPO run
3. inspect reward outputs and traces
4. confirm checkpoints/logs are written

Important recommendation:
- for the first RL smoke test, run the environment colocated with training on H100
- do not make the first training smoke test depend on HF Space networking

Definition of done:
- no trainer crash
- rollout loop completes
- reward values are non-degenerate
- traces look sane

## Phase F: Fallback path

If HF Space deployment is unstable:
- run the environment directly on Northflank as a colocated service or process
- continue training and demo validation there
- keep HF Space deployment as a packaging task rather than a blocker

This fallback should be treated as operational insurance, not the primary path.

## Tracking Checklist

## Environment Packaging
- [ ] Create env Dockerfile
- [ ] Build image locally
- [ ] Run image locally
- [ ] Verify client connection locally
- [ ] Verify one end-to-end task locally

## Hugging Face Space
- [ ] Create Docker Space
- [ ] Push env image / source
- [ ] Confirm Space boots
- [ ] Confirm remote client connection
- [ ] Confirm remote smoke episode

## Training Readiness
- [ ] Create training Dockerfile
- [x] Update training script to use split manifests
- [x] Add baseline eval runner
- [ ] Define checkpoint/log paths
- [ ] Define H100 launch commands

## Northflank CLI: Login and GPU Access

To run training on Northflank H100 you must authenticate the CLI and have an API token.

### Prerequisites
- **Node.js** (v12+) and **npm** (or yarn)
- Northflank account (or team access with an API role)

### Install CLI
```powershell
npm i -g @northflank/cli
```
Or with yarn: `yarn global add @northflank/cli`

### Login (create/use API token)
1. Run:
   ```powershell
   northflank login
   ```
2. A browser window opens. In [Northflank](https://app.northflank.com/) go to **Account/Team → API → Tokens** (or [tokens page](https://app.northflank.com/s/account/api/tokens)).
3. Create an API token (or select an existing one). If you're on a team, an [API role](https://northflank.com/docs/v1/application/secure/grant-api-access) must exist and be available to you.
4. Select or paste the token in the CLI flow. The CLI creates a **context** and switches to it.

**Optional:** Name the context or pass a token non-interactively:
```powershell
northflank login -n my-context -t YOUR_API_TOKEN
```

### Contexts
- List contexts: `northflank context ls`
- Switch context: `northflank context use`
- Set default project/service for the context so you don't need to pass `--project`/`--service` every time: `northflank context use project` or `northflank context use service`

### After login
- Create or select a project, then provision a **GPU job** (e.g. 1× H100) and optional persistent disk (50–100 GB recommended for cache, checkpoints, logs).
- See [Northflank GPU workloads](https://northflank.com/docs/v1/application/run/run-gpu-workloads) and [Deploy GPUs on Northflank's managed cloud](https://northflank.com/docs/v1/application/gpu-workloads/deploy-gpus-on-northflank-cloud) for H100 setup.

---

## Northflank: Link a Git repository

To build and deploy (or run jobs) from your repo, link your Git account first. Then you choose the repo when creating a service or job.

### 1. Link your Git account (team-level)
- Open **[Git integrations](https://app.northflank.com/s/account/integrations/vcs)** in Northflank (team dashboard → Integrations → Git).
- **GitHub**: Click **Link GitHub** → you’re sent to GitHub to install the Northflank app. Choose which repos (or all) Northflank can access.
- **GitLab**: Click **Link GitLab** → OAuth on GitLab. You can then restrict access to certain namespaces.
- **Bitbucket**: Click **Link Bitbucket** → OAuth on Bitbucket; optional namespace restrictions.

You may be prompted to link a Git account when creating a team, or if the team has no Git provider linked.

### 2. Use the repo in a service or job
- Create a **build service**, **combined service**, or **job** (e.g. [create service](https://app.northflank.com/s/project/create/service)).
- When configuring the build source, **select the linked repository** and the **branch** (and optionally build context path, e.g. `/` or `/training` for a subfolder).
- CI can build automatically on push to monitored branches/PRs; you can also trigger builds manually from a branch/commit.

### Optional
- **Build context**: If the code to build is not at repo root, set a path (e.g. `/app` or `/training`) in the service/job build options.
- **Build rules**: Restrict which branches/PRs trigger builds (e.g. `master`, `feature/*`) in build options.
- **Path rules**: Trigger builds only when specific files/dirs change, or ignore paths (e.g. `README.md`), in advanced build settings.

Docs: [Link your Git account](https://northflank.com/docs/v1/application/getting-started/link-your-git-account), [Build from a Git repository](https://northflank.com/docs/v1/application/build/build-code-from-a-git-repository), [Manage Git integrations](https://northflank.com/docs/v1/application/collaborate/manage-git-integrations).

---

## H100 Smoke Test
- [ ] Log into Northflank CLI
- [ ] Create or select project
- [ ] Provision H100 job
- [ ] Attach disk
- [ ] Run baseline eval
- [ ] Run short GRPO smoke job
- [ ] Inspect reward curves / traces

## Risks and Mitigations

### Risk: HF Space boot issues
Mitigation:
- validate locally in Docker first
- keep Northflank colocated fallback ready

### Risk: reward false negatives
Mitigation:
- baseline eval on multiple tasks before long training
- inspect reward breakdowns, not just total reward

### Risk: training script uses wrong manifest
Mitigation:
- explicitly pass `train_manifest.json` and `val_manifest.json`
- avoid relying on implicit defaults

### Risk: losing checkpoints on Northflank restart
Mitigation:
- use persistent disk for training jobs

## Immediate Next Task

The next concrete implementation step is:
1. log into Northflank / the H100 box
2. run baseline eval on 1 to 3 manifest tasks with the env colocated locally
3. run a tiny GRPO smoke job on a very small subset of the train manifest
4. confirm rewards, traces, and checkpoints look sane

We should use the colocated environment first so networking and HF Space runtime do not block the training smoke test.

## Tiny H100 Smoke Scope

Recommended first smoke settings:
- baseline eval: `training/eval_finbench_baseline.py --split val --num-tasks 1`
- GRPO smoke: `training/train_finbench_grpo.py --max-train-tasks 2 --repeats-per-task 1 --num-train-epochs 1`
- keep `max_turns` low for the first run
- save logs and traces for manual inspection
