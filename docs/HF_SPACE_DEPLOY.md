# Deploy LedgerLab to a Hugging Face Space

**LedgerLab: A Memory-First Notebook Workspace for Business RL**

Full instructions to deploy this environment as a Docker Space on Hugging Face.

---

## 1. Create the Space

1. Go to **https://huggingface.co/new-space**
2. Choose:
   - **Owner:** your user (or org)
   - **Space name:** `ledgerlab` (short slug; the full title appears in the Space README)
   - **SDK:** **Docker**
   - **Hardware:** **CPU basic**
   - **Visibility:** Public or Private
3. Click **Create Space**. You get an empty Space repo.

---

## 2. Create a write token (if you don’t have one)

1. Go to **https://huggingface.co/settings/tokens**
2. **Create new token**
3. **Role:** **Write**
4. Copy the token and keep it safe (you’ll use it as the Git password when pushing).

---

## 3. Log in with the Hugging Face CLI (one-time)

In WSL, from the project root:

```bash
cd /home/vivek/projects/openenvHack/ReactAgentEnv
source .venv/bin/activate
hf auth login
```

When prompted, paste your **write** token.  
Optional: so Git can remember your token when pushing:

```bash
git config --global credential.helper store
```

---

## 4. Push the bundle to your Space

Replace `YOUR_HF_USERNAME` with your actual Hugging Face username (e.g. `vivek` or your org).

**Option A – One-shot script (recommended):**

```bash
cd /home/vivek/projects/openenvHack/ReactAgentEnv
source .venv/bin/activate
export HF_USERNAME=YOUR_HF_USERNAME
export HF_SPACE_NAME=ledgerlab
./scripts/push_to_hf_space.sh
```

**Option B – Manual steps:**

```bash
cd /home/vivek/projects/openenvHack/ReactAgentEnv
source .venv/bin/activate
python scripts/prepare_hf_space_bundle.py

cd /home/vivek/projects/openenvHack
git clone https://huggingface.co/spaces/YOUR_HF_USERNAME/ledgerlab hf-finbench-space
rsync -av --delete /home/vivek/projects/openenvHack/ReactAgentEnv/dist/hf_space/ /home/vivek/projects/openenvHack/hf-finbench-space/
cd hf-finbench-space
git add .
git commit -m "LedgerLab: initial Space bundle"
git push
```

**Git push with a token (required):** HF no longer accepts password-at-prompt. Use your **write token** in the remote URL once, then push:

```bash
cd /path/to/hf-finbench-space
git remote set-url origin "https://YOUR_HF_USERNAME:YOUR_WRITE_TOKEN@huggingface.co/spaces/YOUR_HF_USERNAME/ledgerlab"
git push
git remote set-url origin "https://YOUR_HF_USERNAME@huggingface.co/spaces/YOUR_HF_USERNAME/ledgerlab"
```

Replace `YOUR_HF_USERNAME` and `YOUR_WRITE_TOKEN`. The last line removes the token from the remote URL again (recommended).

**Binary files (Git LFS):** HF requires binary files (xlsx, pdf, docx, jpg, etc.) to be stored with Git LFS. The bundle includes a `.gitattributes` that marks these. If a push is rejected for "binary files", in the Space repo run:

```bash
cd /path/to/hf-finbench-space
git lfs install
git add .gitattributes
git add .
git status   # binaries should show as "filter=lfs"
git commit -m "Use Git LFS for binary files"
git push
```

If the bad commit is already made: `git reset --soft HEAD~1` then `git reset HEAD` (unstage all), add `.gitattributes`, `git lfs install`, `git add .`, commit, push.

**Alternatively, use SSH:** Add an SSH key at [huggingface.co/settings/keys](https://huggingface.co/settings/keys), then:

```bash
git remote set-url origin git@hf.co:spaces/YOUR_HF_USERNAME/ledgerlab
git push
```

---

## 5. Wait for the build

- Space page: **https://huggingface.co/spaces/YOUR_HF_USERNAME/ledgerlab**
- HF will build the Docker image; wait until the Space shows as **Running**.

---

## 6. Verify

**Health check:**

```bash
curl https://YOUR_HF_USERNAME-ledgerlab.hf.space/health
```

You should get a healthy response.

**Test from the repo (optional):**

```bash
cd /home/vivek/projects/openenvHack/ReactAgentEnv
source .venv/bin/activate
# Set BASE_URL in script or env to your Space URL, then:
python scripts/test_remote_env.py
```

---

## 7. Updating the Space later

Re-run the push script (same as step 4). It will rebuild the bundle, sync into the existing clone, commit, and push:

```bash
cd /home/vivek/projects/openenvHack/ReactAgentEnv
source .venv/bin/activate
export HF_USERNAME=YOUR_HF_USERNAME
export HF_SPACE_NAME=ledgerlab
./scripts/push_to_hf_space.sh
```

---

## Summary

| Step | Action |
|------|--------|
| 1 | Create Space at [new-space](https://huggingface.co/new-space) (Docker, CPU basic, name: `ledgerlab`) |
| 2 | Create write token at [tokens](https://huggingface.co/settings/tokens) |
| 3 | `source .venv/bin/activate` → `hf auth login` (and optionally `git config --global credential.helper store`) |
| 4 | `export HF_USERNAME=...` and `HF_SPACE_NAME=ledgerlab` → `./scripts/push_to_hf_space.sh` |
| 5 | Wait for build on the Space page |
| 6 | `curl https://YOUR_USERNAME-ledgerlab.hf.space/health` |

**Space URL:** `https://huggingface.co/spaces/YOUR_USERNAME/ledgerlab`  
**App title (in README):** LedgerLab: A Memory-First Notebook Workspace for Business RL
