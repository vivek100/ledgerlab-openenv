# FinBench: Notebook-Driven Financial Analysis Agent Environment

## Status Snapshot

Current project status:
- dataset scaling to the full xlsx-compatible GDPval subset is complete
- `46/46` tasks now have deterministic, verified `submission_fields`
- split manifests are in place: `34` train, `12` validation, `0` test
- the main inference runner works against the environment
- a large-model baseline run has been executed successfully end-to-end
- one real reward-scorer crash was found and fixed during that baseline run

Current bottleneck:
- not data collection
- not field generation
- not basic environment functionality
- the bottleneck is now training readiness and reward hardening

## Recommended Next Step

The next step should be:
1. reward hardening on real agent traces
2. baseline evaluation on a small batch of train/val tasks
3. training script wiring to split manifests
4. short GRPO smoke training run

## The Problem We're Solving

Current AI agents are bad at five specific things that real professionals do every day:

| Capability Gap | What Agents Do Today | What We Train Them To Do |
|---|---|---|
| **Multi-file reasoning** | Lose track after 2-3 files | Connect info across 5+ reference files without losing context |
| **Iterative refinement** | Write one big code block, give up on errors | Run a cell ? see output ? edit ? re-run ? build up analysis |
| **State management** | Re-read files they already parsed, forget variables | Create notebooks as working memory, reference past cells |
| **Structured output** | Dump text answers | Produce Excel workbooks with named sheets, formatted reports |
| **Self-verification** | Submit first attempt | Check own work by reading notebook outputs before submitting |

## What We Build

An **OpenEnv environment** where an agent works like a data analyst:

1. Receives a professional task + reference files in a workspace (from GDPval dataset)
2. Explores workspace, searches files, organizes folders
3. Creates Jupyter notebooks to analyze data ? adds cells, runs them, sees output, iterates
4. Writes intermediate files (cleaned data, notes) as working memory
5. Saves useful notebooks as reusable templates to a persistent memory bank
6. Produces deliverables (Excel reports, documents) checked against rubrics
7. All actions are traced ? we capture the full process, not just the answer

The notebooks serve THREE purposes:
- **Execution environment** ? persistent kernel, variables carry between cells
- **Working memory** ? agent can re-read its own past analysis
- **Evaluable artifact** ? we score notebook quality, not just the final deliverable

## Hackathon Challenge Alignment

| Challenge | How We Address It |
|---|---|
| **Statement 2: Long-Horizon Planning** | 10-20+ tool calls per episode. Agent must plan exploration, analysis, deliverable creation. Sparse rewards (only on submission). |
| **Statement 3.1: Professional Tasks / World Modeling** | Real professional tasks from GDPval. Workspace IS a partially observable world the agent must model. |
| **Mercor Sub-Theme** | Capped reward = rubric score (0.0-1.0, hard ceiling). Uncapped reward = depth bonus that scales with thoroughness of analysis. |
| **Scale AI Sub-Theme** | Long-horizon business data analysis workflows. Multi-step, multi-file, multi-tool. |

---

## Tool Design

### 1. Notebook Tools (the core differentiator)

```
create_notebook(path: str) -> str
    Creates an empty .ipynb notebook at the given workspace path.
    Returns: confirmation with notebook path.

read_notebook(path: str) -> NotebookView
    Returns ALL cells: cell_id, cell_type (code/markdown), source, outputs, execution status.
    This IS the agent's memory ? it re-reads what it already did.

add_cell(notebook: str, source: str, cell_type: str = "code", position: int = -1) -> str
    Adds a cell at position (-1 = end).
    Returns: cell_id.

edit_cell(notebook: str, cell_id: str, new_source: str) -> str
    Modifies an existing cell's source.

delete_cell(notebook: str, cell_id: str) -> str
    Removes a cell.

run_cell(notebook: str, cell_id: str) -> CellOutput
    Executes one cell in the persistent kernel.
    Returns: stdout, stderr, display_data, error.
    Variables persist for subsequent cells.

write_and_run(notebook: str, source: str, position: int = -1) -> CellOutput
    Shortcut: adds a cell AND executes it in one action.
    Returns: cell_id + output. Most common operation.

run_all(notebook: str) -> list[CellOutput]
    Runs all cells top-to-bottom. Useful after editing earlier cells.

get_kernel_state() -> KernelState
    Returns: all variable names, types, shapes/sizes in the kernel.
    Agent explicitly checks what's in memory instead of guessing.
```

### 2. Workspace Tools (file & folder management)

```
list_files(path: str = "/") -> str
    Lists files/folders with type, size, modification time.

read_file(path: str) -> str
    Reads text content of any file (truncated if large).

write_file(path: str, content: str) -> str
    Creates/overwrites a file. Works for text, CSV, markdown, etc.

create_folder(path: str) -> str
    Creates a directory (and parents). Agent organizes its workspace.

search_files(query: str, path: str = "/", file_pattern: str = "*") -> str
    Grep-like search across files. Returns matching lines with file paths and line numbers.
    Supports regex. Can filter by file pattern (e.g. "*.csv", "*.py").
    Critical for multi-file reasoning ? agent finds relevant content without reading everything.
```
