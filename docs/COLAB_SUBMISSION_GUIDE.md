# Colab Submission Guide

## Notebook
- File: `training/ledgerlab_trl_minimal_training_colab.ipynb`
- Purpose: minimal reproducible HF TRL training demo for LedgerLab.
- This notebook calls the real project training entrypoint:
  - `training/train_finbench_grpo.py`

## What To Say In The Submission
- The environment training implementation uses **Hugging Face TRL**.
- The notebook is a minimal Colab wrapper around the real project training script.
- The larger training runs were executed on an H100 because the environment is long-horizon and tool-using.

## How To Put It On Colab
1. Open Colab: `https://colab.research.google.com/`
2. Click `File -> Upload notebook`.
3. Upload `training/ledgerlab_trl_minimal_training_colab.ipynb`.
4. In `Runtime -> Change runtime type`, select `GPU`.
5. Run the cells top to bottom.

## Optional W&B Logging In Colab
- In the notebook, uncomment these lines and set your values:
  - `os.environ['WANDB_API_KEY'] = 'YOUR_WANDB_API_KEY'`
  - `os.environ['WANDB_ENTITY'] = 'YOUR_WANDB_ENTITY'`

## Important Caveat
- The notebook is the minimal HF TRL training demo for hackathon submission.
- It is not the recommended setup for your longer training runs.
- The real larger runs should remain on Northflank H100.
