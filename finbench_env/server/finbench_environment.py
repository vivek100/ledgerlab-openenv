"""
FinBench Environment Implementation.

A notebook-driven financial analysis environment that evaluates agents on their
ability to create notebooks, run cells iteratively, and produce deliverables
evaluated against GDPval rubrics.

All interactions happen through MCP tools registered via FastMCP.
"""

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastmcp import FastMCP
from openenv.core.env_server.mcp_environment import MCPEnvironment
from openenv.core.env_server.mcp_types import CallToolAction, ListToolsAction
from openenv.core.env_server.types import Action, Observation

from ..models import AVAILABLE_TOOLS, FinBenchState
from .notebook_executor import NotebookExecutor
from .workspace import Workspace
from .memory import MemoryBank
from .trace import TraceLogger

logger = logging.getLogger(__name__)


class FinBenchEnvironment(MCPEnvironment):
    """
    Notebook-driven financial analysis environment.

    On reset(): Sets up workspace with reference files, seeds memory, starts kernel.
    On step(): Routes MCP tool calls, captures trace, returns observations.
    On submit: Computes multi-tier reward from rubrics + execution quality + memory/process.
    """

    def __init__(
        self,
        data_path: str = "./data",
        memory_seed_path: Optional[str] = None,
        traces_dir: str = "./traces",
        max_steps: int = 30,
        manifest_path: Optional[str] = None,
        task_split: Optional[str] = None,
    ):
        mcp = FastMCP("finbench_env")

        self.data_path = os.path.abspath(data_path)
        self.memory_seed_path = memory_seed_path or os.path.join(self.data_path, "memory_seed")
        self.traces_dir = traces_dir
        self.max_steps = max_steps
        self.manifest_path = self._resolve_manifest_path(manifest_path)
        self.task_split = task_split

        # Episode-scoped state (set in reset)
        self._executor: Optional[NotebookExecutor] = None
        self._workspace: Optional[Workspace] = None
        self._memory: Optional[MemoryBank] = None
        self._trace: Optional[TraceLogger] = None
        self._current_task: Optional[Dict] = None
        self._workspace_root: Optional[str] = None
        self._last_file_snapshot: Optional[Dict[str, Dict[str, Any]]] = None
        self._last_submit_metadata: Optional[Dict[str, Any]] = None
        self._last_trace_path: Optional[str] = None

        self._pending_submission_values: Dict[str, Any] = {}

        # Persistent memory (survives across episodes)
        self._persistent_memory_path = os.path.join(self.data_path, "_persistent_memory")
        os.makedirs(self._persistent_memory_path, exist_ok=True)

        # â”€â”€ Register MCP tools â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        @mcp.tool
        def list_files(path: str = "/") -> str:
            """List files and folders in the workspace at the given path."""
            return self._workspace.list_files(path)

        @mcp.tool
        def read_file(path: str) -> str:
            """Read a file from the workspace. Supports text, CSV, and Excel preview."""
            return self._workspace.read_file(path)

        @mcp.tool
        def write_file(path: str, content: str) -> str:
            """Write content to a file in the workspace."""
            result = self._workspace.write_file(path, content)
            self._state.files_created.append(path)
            return result

        @mcp.tool
        def create_folder(path: str) -> str:
            """Create a folder in the workspace."""
            return self._workspace.create_folder(path)

        @mcp.tool
        def search_files(query: str, path: str = "/", file_pattern: str = "*") -> str:
            """Grep-like search across workspace files. Supports regex."""
            return self._workspace.search_files(query, path, file_pattern)

        @mcp.tool
        def create_notebook(path: str) -> str:
            """Create an empty Jupyter notebook at the given path."""
            result = self._executor.create_notebook(path)
            if path not in self._state.notebooks:
                self._state.notebooks.append(path)
            return (
                f"{result}\n"
                "Next step example:\n"
                f'write_and_run(notebook="{path}", source="print(\'hello\')", position=0)\n'
                "Tip: use position=-1 to append cells."
            )

        @mcp.tool
        def read_notebook(path: str) -> str:
            """Read a notebook and return its cells with sources and outputs."""
            data = self._executor.read_notebook(path)
            return json.dumps(data, indent=2, default=str)

        @mcp.tool
        def add_cell(notebook: str, source: str, cell_type: str = "code", position: int = -1) -> str:
            """Add a new cell to a notebook. Returns the cell_id."""
            cell_id = self._executor.add_cell(notebook, source, cell_type, position)
            return f"Cell {cell_id} added to {notebook}"

        @mcp.tool
        def edit_cell(notebook: str, cell_id: str, new_source: str) -> str:
            """Edit an existing cell's source code."""
            return self._executor.edit_cell(notebook, cell_id, new_source)

        @mcp.tool
        def delete_cell(notebook: str, cell_id: str) -> str:
            """Remove a cell from a notebook."""
            return self._executor.delete_cell(notebook, cell_id)

        @mcp.tool
        def run_cell(notebook: str, cell_id: str) -> str:
            """Execute a single cell in the notebook and return its output."""
            result = self._executor.run_cell(notebook, cell_id)
            return json.dumps(result, indent=2, default=str)

        @mcp.tool
        def write_and_run(notebook: str, source: str, position: int = -1) -> str:
            """Add a code cell and immediately execute it. Returns cell_id and output."""
            result = self._executor.write_and_run(notebook, source, position)
            self._update_kernel_vars()
            notebook_state = self._executor.read_notebook(notebook)
            if isinstance(notebook_state, dict):
                cells = notebook_state.get("cells", [])
                result["notebook_summary"] = {
                    "path": notebook,
                    "position_used": position,
                    "cell_count": notebook_state.get("cell_count", len(cells)),
                    "recent_cell_ids": [c.get("cell_id", "") for c in cells[-5:]],
                    "next_hint": (
                        f'Use write_and_run(notebook="{notebook}", source="...", position=-1) '
                        "to append another cell."
                    ),
                }
            return json.dumps(result, indent=2, default=str)

        @mcp.tool
        def run_all(notebook: str) -> str:
            """Run all code cells in a notebook top-to-bottom. Stops on first error."""
            results = self._executor.run_all(notebook)
            self._update_kernel_vars()
            return json.dumps(results, indent=2, default=str)

        @mcp.tool
        def get_kernel_state() -> str:
            """Get all variables currently in the Python kernel with types/shapes."""
            kstate = self._executor.get_kernel_state()
            self._state.kernel_variables = list(kstate.keys())
            return json.dumps(kstate, indent=2, default=str)

        @mcp.tool
        def save_to_memory(notebook_path: str, name: str, tags: str, description: str) -> str:
            """Save a notebook to the persistent memory bank. Tags are comma-separated."""
            source = os.path.join(self._workspace_root, notebook_path.lstrip("/"))
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            result = self._memory.save_to_memory(source, name, tag_list, description)
            # Sync back to persistent storage
            shutil.copytree(
                os.path.join(self._workspace_root, "memory"),
                self._persistent_memory_path,
                dirs_exist_ok=True,
            )
            return result

        @mcp.tool
        def list_memory(tags: str = "") -> str:
            """List memory templates, optionally filtered by comma-separated tags."""
            tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
            entries = self._memory.list_memory(tag_list)
            return json.dumps(entries, indent=2, default=str)

        @mcp.tool
        def load_from_memory(name: str) -> str:
            """Load a memory template into the work/ directory."""
            dest_dir = os.path.join(self._workspace_root, "work")
            return self._memory.load_from_memory(name, dest_dir)

        @mcp.tool
        def submit(deliverable_paths: str = "", submission_values: str = "") -> str:
            """Submit your deliverables for evaluation.

            Args:
                deliverable_paths: Comma-separated output file paths (optional).
                submission_values: JSON string with verification field values, e.g.
                    {"june_total_shipped_cost": 140008.20, "june_row_count": 48}
            """
            if submission_values:
                try:
                    self._pending_submission_values = json.loads(submission_values)
                except (json.JSONDecodeError, TypeError):
                    self._pending_submission_values = {}
            else:
                self._pending_submission_values = {}
            return "Submission received."

        # Pass MCP server to base class
        super().__init__(mcp)
        self._state = FinBenchState()

    # â”€â”€ reset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_id: Optional[str] = None,
        task_json: Optional[str] = None,
        **kwargs: Any,
    ) -> Observation:
        """Reset for a new episode."""
        if self._executor:
            self._executor.stop_kernel()

        ep_id = episode_id or str(uuid4())[:12]

        # Load task
        if task_json:
            task = json.loads(task_json)
        elif task_id:
            task = self._load_task(task_id)
        else:
            task = self._load_random_task()

        if task is None:
            task = {
                "task_id": "default",
                "prompt": "Explore the workspace and analyze any data files you find.",
                "reference_files": [],
                "rubric": [],
                "expected_deliverables": [],
            }

        self._current_task = task

        # Fresh workspace
        self._workspace_root = tempfile.mkdtemp(prefix=f"finbench_{ep_id}_")
        os.makedirs(os.path.join(self._workspace_root, "reference"), exist_ok=True)
        os.makedirs(os.path.join(self._workspace_root, "output"), exist_ok=True)

        self._setup_reference_files(task)

        # Memory bank
        memory_in_workspace = os.path.join(self._workspace_root, "memory")
        if os.path.exists(self._persistent_memory_path) and os.listdir(self._persistent_memory_path):
            shutil.copytree(self._persistent_memory_path, memory_in_workspace)
        else:
            os.makedirs(memory_in_workspace, exist_ok=True)

        self._memory = MemoryBank(memory_in_workspace)
        self._memory.seed_from_directory(self.memory_seed_path)

        # Workspace + kernel
        self._workspace = Workspace(self._workspace_root)
        self._executor = NotebookExecutor(self._workspace_root)
        self._executor.start_kernel()

        # Trace
        self._trace = TraceLogger(ep_id, task.get("task_id", "unknown"))
        self._trace.add_metadata(
            task_prompt=task.get("prompt", ""),
            source=task.get("source", "local"),
            sector=task.get("sector"),
            occupation=task.get("occupation"),
        )
        self._last_file_snapshot = self._snapshot_files()
        self._last_submit_metadata = None
        self._last_trace_path = None

        # State
        self._state = FinBenchState(
            episode_id=ep_id,
            step_count=0,
            task_id=task.get("task_id", ""),
            task_prompt=task.get("prompt", ""),
            workspace_path=self._workspace_root,
            max_steps=self.max_steps,
        )

        # Build initial message
        file_listing = self._workspace.list_files("/")
        memory_entries = self._memory.list_memory()
        memory_summary = ""
        if memory_entries:
            lines = [f"  - {e['name']}: {e['description']} (tags: {e['tags']})" for e in memory_entries]
            memory_summary = "\n\nAvailable memory templates:\n" + "\n".join(lines)

        return Observation(
            done=False,
            reward=0.0,
            metadata={
                "task_id": task.get("task_id"),
                "task_prompt": task.get("prompt"),
                "manifest_path": self.manifest_path,
                "task_split": self.task_split,
                "workspace_files": self._workspace.get_all_files(),
                "memory_templates": [e["name"] for e in memory_entries],
                "tool_result": (
                    f"=== FinBench Episode {ep_id} ===\n\n"
                    f"Task: {task.get('prompt', 'No task specified')}\n\n"
                    f"Workspace:\n{file_listing}"
                    f"{memory_summary}\n\n"
                    f"Available tools: {', '.join(AVAILABLE_TOOLS)}"
                ),
            },
        )

    # â”€â”€ step â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _step_impl(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Handle non-MCP actions (not supported)."""
        return Observation(
            done=False,
            reward=0.0,
            metadata={
                "error": f"Unknown action type: {type(action).__name__}. "
                "Use ListToolsAction or CallToolAction for MCP interactions."
            },
        )

    def step(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Execute a step. Delegates MCP routing to base, handles submit + max-steps."""
        action_type = getattr(action, "type", None)
        if action_type == "list_tools" and not isinstance(action, ListToolsAction):
            action = ListToolsAction()
        elif action_type == "call_tool" and not isinstance(action, CallToolAction):
            action = CallToolAction(
                tool_name=getattr(action, "tool_name", "") or "",
                arguments=getattr(action, "arguments", {}) or {},
            )

        self._state.step_count += 1

        # Log trace before executing
        tool_name = ""
        tool_args = {}
        if isinstance(action, CallToolAction):
            tool_name = action.tool_name
            tool_args = action.arguments or {}

        before_snapshot = self._snapshot_files()

        # Let MCPEnvironment handle ListToolsAction / CallToolAction
        obs = super().step(action, timeout_s=timeout_s, **kwargs)

        # Log to trace
        if tool_name and self._trace:
            result_text = ""
            if hasattr(obs, "result") and obs.result:
                try:
                    content = obs.result.content
                    if content:
                        result_text = str(content[0].text) if hasattr(content[0], "text") else str(content[0])
                except Exception:
                    result_text = str(obs.result)
            elif hasattr(obs, "metadata"):
                result_text = str(obs.metadata)

            after_snapshot = self._snapshot_files()
            file_changes = self._diff_files(before_snapshot, after_snapshot)
            state_snapshot = {
                "notebooks": list(self._state.notebooks),
                "files": list(self._state.files_created),
                "kernel_variables": list(self._state.kernel_variables),
                "workspace_file_count": len(after_snapshot),
                "output_files": sorted(f for f in after_snapshot if f.startswith("output/")),
                "new_files": file_changes["new_files"],
                "modified_files": file_changes["modified_files"],
                "important_output_previews": self._preview_files(
                    file_changes["new_files"] + file_changes["modified_files"]
                ),
            }

            self._trace.log_step(
                tool=tool_name,
                args=tool_args,
                result=self._format_trace_result(tool_name, result_text),
                state_snapshot=state_snapshot,
            )
            self._last_file_snapshot = after_snapshot

        # Handle submit
        if isinstance(action, CallToolAction) and action.tool_name == "submit":
            return self._handle_submit()

        # Max steps check
        if self._state.step_count >= self.max_steps:
            logger.info(f"Episode {self._state.episode_id} terminated: max steps reached")
            if self._trace:
                self._last_trace_path = self._trace.save(self.traces_dir)
            return Observation(
                done=True,
                reward=-0.1,
                metadata={
                    **obs.metadata,
                    "error": f"Max steps ({self.max_steps}) reached without submitting.",
                },
            )

        return obs

    # â”€â”€ Submit + reward â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _handle_submit(self) -> Observation:
        """Compute full reward on submission."""
        from .rewards import compute_total_reward

        reward_data = compute_total_reward(
            task=self._current_task,
            trace=self._trace,
            workspace=self._workspace,
            executor=self._executor,
            workspace_root=self._workspace_root,
            submission_values=self._pending_submission_values or None,
        )

        if self._trace:
            self._trace.add_metadata(
                final_output_previews=self._preview_files(
                    sorted(
                        f for f in self._snapshot_files().keys()
                        if f.startswith("output/")
                    ),
                    max_files=4,
                ),
                reward_breakdown=reward_data,
            )
            self._last_trace_path = self._trace.save(self.traces_dir)

        self._executor.stop_kernel()

        self._last_submit_metadata = reward_data

        return Observation(
            done=True,
            reward=reward_data["total_reward"],
            metadata=reward_data,
        )

    # â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _update_kernel_vars(self) -> None:
        try:
            kstate = self._executor.get_kernel_state()
            self._state.kernel_variables = list(kstate.keys())
        except Exception:
            pass

    def _setup_reference_files(self, task: Dict) -> None:
        ref_dir = os.path.join(self._workspace_root, "reference")
        task_workspace = os.path.join(
            self.data_path, "tasks", "workspaces", task.get("task_id", "default"), "reference"
        )
        if os.path.exists(task_workspace):
            for f in os.listdir(task_workspace):
                src = os.path.join(task_workspace, f)
                dst = os.path.join(ref_dir, f)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)

    def _snapshot_files(self) -> Dict[str, Dict[str, Any]]:
        if not self._workspace_root or not os.path.exists(self._workspace_root):
            return {}

        snapshot: Dict[str, Dict[str, Any]] = {}
        for dirpath, _, filenames in os.walk(self._workspace_root):
            for fname in filenames:
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, self._workspace_root)
                stat = os.stat(full)
                snapshot[rel] = {
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
        return snapshot

    def _diff_files(
        self,
        before: Dict[str, Dict[str, Any]],
        after: Dict[str, Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        before_keys = set(before.keys())
        after_keys = set(after.keys())
        new_files = sorted(after_keys - before_keys)
        modified_files = sorted(
            path for path in (before_keys & after_keys)
            if before[path] != after[path]
        )
        return {
            "new_files": new_files[:10],
            "modified_files": modified_files[:10],
        }

    def _preview_files(self, paths: List[str], max_files: int = 3) -> List[Dict[str, str]]:
        previews: List[Dict[str, str]] = []
        seen = set()
        for rel_path in paths:
            if rel_path in seen or not rel_path.startswith(("output/", "work/")):
                continue
            seen.add(rel_path)
            full = os.path.join(self._workspace_root, rel_path)
            if not os.path.isfile(full):
                continue
            try:
                preview = self._workspace.read_file(rel_path)
            except Exception:
                continue
            previews.append({
                "path": rel_path,
                "preview": preview[:1500],
            })
            if len(previews) >= max_files:
                break
        return previews

    def _format_trace_result(self, tool_name: str, result_text: str) -> Any:
        parsed: Any = result_text[:2000]
        if result_text and result_text[:1] in ("{", "["):
            try:
                parsed = json.loads(result_text)
            except Exception:
                parsed = result_text[:2000]

        if isinstance(parsed, dict):
            summary: Dict[str, Any] = {}
            for key in ("success", "stdout", "stderr", "error", "execution_time_ms", "cell_id"):
                if key in parsed:
                    value = parsed[key]
                    if isinstance(value, str):
                        summary[key] = value[:600]
                    else:
                        summary[key] = value
            if summary:
                summary["tool"] = tool_name
                return summary
        return parsed

    def _resolve_manifest_path(self, manifest_path: Optional[str]) -> str:
        if manifest_path:
            candidate = Path(manifest_path)
            if candidate.is_absolute():
                return str(candidate)
            direct = Path(self.data_path) / candidate
            if direct.exists():
                return str(direct)
            return str(Path(self.data_path) / "tasks" / candidate)
        return str(Path(self.data_path) / "tasks" / "task_manifest.json")

    def _read_manifest(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            return []
        return []

    def _base_manifest_path(self) -> str:
        return str(Path(self.data_path) / "tasks" / "task_manifest.json")

    def _load_manifest(self) -> List[Dict[str, Any]]:
        tasks = self._read_manifest(self.manifest_path)
        if tasks:
            return tasks
        fallback = self._base_manifest_path()
        if fallback != self.manifest_path:
            return self._read_manifest(fallback)
        return []

    def _load_task(self, task_id: str) -> Optional[Dict]:
        tasks = self._load_manifest()
        for t in tasks:
            if t.get("task_id") == task_id:
                return t
        fallback = self._base_manifest_path()
        if fallback != self.manifest_path:
            for t in self._read_manifest(fallback):
                if t.get("task_id") == task_id:
                    return t
        return None

    def _load_random_task(self) -> Optional[Dict]:
        tasks = self._load_manifest()
        if self.task_split:
            split_tasks = [
                t for t in tasks
                if str(t.get("split", "")).lower() == self.task_split.lower()
            ]
            if split_tasks:
                tasks = split_tasks
        if not tasks:
            return None
        import random
        return random.choice(tasks)

    @property
    def state(self) -> FinBenchState:
        return self._state

    def close(self) -> None:
        if self._executor:
            self._executor.stop_kernel()
        super().close()

