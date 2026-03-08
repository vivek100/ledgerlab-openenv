"""
Notebook execution engine using jupyter_client + nbformat.

Manages:
- Persistent Jupyter kernel (variables survive across cells)
- Notebook files (.ipynb) via nbformat
- Cell CRUD operations
- Execution with output capture
"""

import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

logger = logging.getLogger(__name__)

# Timeout for kernel message responses
EXECUTE_TIMEOUT_S = 30


class NotebookExecutor:
    """Manages notebooks on disk and a shared Jupyter kernel for execution."""

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self._kernel_manager = None
        self._kernel_client = None
        self._started = False

    def start_kernel(self) -> None:
        """Start the Jupyter kernel."""
        if self._started:
            return

        from jupyter_client import KernelManager

        self._kernel_manager = KernelManager(kernel_name="python3")
        self._kernel_manager.start_kernel()
        self._kernel_client = self._kernel_manager.client()
        self._kernel_client.start_channels()
        self._kernel_client.wait_for_ready(timeout=30)

        self._execute_silent(
            f"import os; os.chdir({self.workspace_path!r})"
        )
        self._execute_silent(
            "import pandas as pd, numpy as np, json, re, math, os, statistics, datetime, collections"
        )
        self._started = True
        logger.info("Jupyter kernel started and initialized")

    def stop_kernel(self) -> None:
        """Stop the Jupyter kernel."""
        if self._kernel_client:
            self._kernel_client.stop_channels()
        if self._kernel_manager and self._kernel_manager.is_alive():
            self._kernel_manager.shutdown_kernel(now=True)
        self._started = False

    # ---- Notebook file operations ----

    def create_notebook(self, path: str) -> str:
        """Create an empty notebook at the given workspace-relative path."""
        full_path = self._resolve(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        nb = new_notebook()
        nb.metadata["kernelspec"] = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }
        with open(full_path, "w") as f:
            nbformat.write(nb, f)
        return f"Notebook created: {path}"

    def read_notebook(self, path: str) -> Dict[str, Any]:
        """Read a notebook and return its structure."""
        full_path = self._resolve(path)
        if not os.path.exists(full_path):
            return {"error": f"Notebook not found: {path}"}

        nb = self._load_nb(full_path)
        cells = []
        for cell in nb.cells:
            cell_info = {
                "cell_id": cell.get("id", ""),
                "cell_type": cell.cell_type,
                "source": cell.source,
                "executed": bool(cell.get("execution_count")),
            }
            if cell.cell_type == "code" and cell.get("outputs"):
                outputs = []
                for out in cell.outputs:
                    if out.output_type == "stream":
                        outputs.append(out.text)
                    elif out.output_type == "execute_result":
                        outputs.append(out.data.get("text/plain", ""))
                    elif out.output_type == "error":
                        outputs.append(
                            f"ERROR: {out.ename}: {out.evalue}"
                        )
                cell_info["outputs"] = "\n".join(outputs)
            cells.append(cell_info)

        return {"path": path, "cells": cells, "cell_count": len(cells)}

    def add_cell(
        self,
        notebook_path: str,
        source: str,
        cell_type: str = "code",
        position: int = -1,
    ) -> str:
        """Add a cell to a notebook. Returns the cell_id."""
        full_path = self._resolve(notebook_path)
        nb = self._load_nb(full_path)

        cell_id = str(uuid.uuid4())[:8]
        if cell_type == "markdown":
            cell = new_markdown_cell(source)
        else:
            cell = new_code_cell(source)
        cell["id"] = cell_id

        if position < 0 or position >= len(nb.cells):
            nb.cells.append(cell)
        else:
            nb.cells.insert(position, cell)

        self._save_nb(full_path, nb)
        return cell_id

    def edit_cell(
        self, notebook_path: str, cell_id: str, new_source: str
    ) -> str:
        """Edit an existing cell's source."""
        full_path = self._resolve(notebook_path)
        nb = self._load_nb(full_path)
        cell = self._find_cell(nb, cell_id)
        if cell is None:
            return f"Cell {cell_id} not found in {notebook_path}"
        cell.source = new_source
        cell.outputs = []
        cell["execution_count"] = None
        self._save_nb(full_path, nb)
        return f"Cell {cell_id} updated"

    def delete_cell(self, notebook_path: str, cell_id: str) -> str:
        """Remove a cell from a notebook."""
        full_path = self._resolve(notebook_path)
        nb = self._load_nb(full_path)
        nb.cells = [c for c in nb.cells if c.get("id") != cell_id]
        self._save_nb(full_path, nb)
        return f"Cell {cell_id} deleted"

    # ---- Execution ----

    def run_cell(self, notebook_path: str, cell_id: str) -> Dict[str, Any]:
        """Execute a single cell and capture outputs."""
        full_path = self._resolve(notebook_path)
        nb = self._load_nb(full_path)
        cell = self._find_cell(nb, cell_id)
        if cell is None:
            return {
                "cell_id": cell_id,
                "success": False,
                "error": f"Cell {cell_id} not found",
                "stdout": "",
                "stderr": "",
            }
        if cell.cell_type != "code":
            return {
                "cell_id": cell_id,
                "success": True,
                "stdout": "(markdown cell, no execution)",
                "stderr": "",
            }

        result = self._execute_code(cell.source)

        cell.outputs = self._build_cell_outputs(result)
        cell["execution_count"] = result.get("execution_count", 1)
        self._save_nb(full_path, nb)

        return {
            "cell_id": cell_id,
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "success": result.get("success", False),
            "error": result.get("error"),
            "display_data": result.get("display_data"),
            "new_variables": result.get("new_variables", []),
            "execution_time_ms": result.get("execution_time_ms", 0),
        }

    def write_and_run(
        self, notebook_path: str, source: str, position: int = -1
    ) -> Dict[str, Any]:
        """Add a cell and immediately run it."""
        cell_id = self.add_cell(notebook_path, source, "code", position)
        result = self.run_cell(notebook_path, cell_id)
        result["cell_id"] = cell_id
        return result

    def run_all(self, notebook_path: str) -> List[Dict[str, Any]]:
        """Run all code cells top to bottom."""
        full_path = self._resolve(notebook_path)
        nb = self._load_nb(full_path)
        results = []
        for cell in nb.cells:
            if cell.cell_type == "code" and cell.source.strip():
                cell_id = cell.get("id", "unknown")
                result = self.run_cell(notebook_path, cell_id)
                results.append(result)
                if not result.get("success", True):
                    break
        return results

    # ---- Kernel state ----

    def get_kernel_state(self) -> Dict[str, str]:
        """Get all user variables from the kernel."""
        code = """
import json as _json, types as _types
_SKIP = {'In', 'Out', 'get_ipython', 'exit', 'quit', 'os', 'pd', 'np', 'json',
         're', 'math', 'statistics', 'datetime', 'collections'}
_vars = {}
for _name, _val in list(globals().items()):
    if _name.startswith('_') or _name in _SKIP or isinstance(_val, _types.ModuleType):
        continue
    try:
        if hasattr(_val, 'shape'):
            _vars[_name] = f"{type(_val).__name__} shape={_val.shape}"
        elif hasattr(_val, '__len__') and not isinstance(_val, str):
            _vars[_name] = f"{type(_val).__name__} len={len(_val)}"
        elif callable(_val) and not isinstance(_val, type):
            _vars[_name] = "function"
        elif isinstance(_val, type):
            _vars[_name] = "class"
        else:
            _r = repr(_val)
            _vars[_name] = _r[:100] if len(_r) > 100 else _r
    except Exception:
        _vars[_name] = f"{type(_val).__name__}"
print(_json.dumps(_vars))
"""
        result = self._execute_code(code)
        stdout = result.get("stdout", "").strip()
        # The last line should be the JSON
        lines = stdout.strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{"):
                try:
                    import json
                    return json.loads(line)
                except Exception:
                    continue
        return {"_raw": stdout}

    # ---- Internal helpers ----

    def _resolve(self, path: str) -> str:
        """Resolve workspace-relative path to absolute."""
        return os.path.join(self.workspace_path, path.lstrip("/"))

    def _load_nb(self, full_path: str) -> nbformat.NotebookNode:
        with open(full_path) as f:
            return nbformat.read(f, as_version=4)

    def _save_nb(self, full_path: str, nb: nbformat.NotebookNode) -> None:
        with open(full_path, "w") as f:
            nbformat.write(nb, f)

    def _find_cell(self, nb, cell_id: str):
        for cell in nb.cells:
            if cell.get("id") == cell_id:
                return cell
        return None

    def _execute_silent(self, code: str) -> None:
        """Execute code without capturing output. Used for setup."""
        if not self._kernel_client:
            return
        self._kernel_client.execute(code, silent=True)
        self._kernel_client.get_shell_msg(timeout=EXECUTE_TIMEOUT_S)

    def _drain_iopub(self) -> None:
        """Drain any pending iopub messages from prior executions."""
        while True:
            try:
                self._kernel_client.get_iopub_msg(timeout=0.05)
            except Exception:
                break

    def _execute_code(self, code: str) -> Dict[str, Any]:
        """Execute code in the kernel and capture all outputs."""
        if not self._kernel_client:
            return {"success": False, "error": "Kernel not started", "stdout": "", "stderr": ""}

        self._drain_iopub()

        start = time.time()
        msg_id = self._kernel_client.execute(code)

        stdout_parts = []
        stderr_parts = []
        display_parts = []
        error_msg = None
        success = True

        # Wait for shell reply
        reply = self._kernel_client.get_shell_msg(timeout=EXECUTE_TIMEOUT_S)
        exec_count = reply.get("content", {}).get("execution_count")
        if reply["content"].get("status") == "error":
            success = False
            error_msg = f"{reply['content'].get('ename', 'Error')}: {reply['content'].get('evalue', '')}"

        # Drain iopub for outputs (only messages from this execution)
        while True:
            try:
                msg = self._kernel_client.get_iopub_msg(timeout=3)
            except Exception:
                break

            if msg.get("parent_header", {}).get("msg_id") != msg_id:
                continue

            msg_type = msg.get("msg_type", "")
            content = msg.get("content", {})

            if msg_type == "stream":
                if content.get("name") == "stderr":
                    stderr_parts.append(content.get("text", ""))
                else:
                    stdout_parts.append(content.get("text", ""))
            elif msg_type == "execute_result":
                display_parts.append(
                    content.get("data", {}).get("text/plain", "")
                )
            elif msg_type == "display_data":
                display_parts.append(
                    content.get("data", {}).get("text/plain", "")
                )
            elif msg_type == "error":
                success = False
                tb = content.get("traceback", [])
                error_msg = f"{content.get('ename', 'Error')}: {content.get('evalue', '')}"
                stderr_parts.append("\n".join(tb) if tb else error_msg)
            elif msg_type == "status" and content.get("execution_state") == "idle":
                break

        elapsed_ms = (time.time() - start) * 1000

        stdout = "".join(stdout_parts)
        stderr = "".join(stderr_parts)

        # Truncate long outputs
        max_len = 8192
        if len(stdout) > max_len:
            stdout = stdout[:max_len] + f"\n... (truncated, {len(stdout)} chars total)"
        if len(stderr) > max_len:
            stderr = stderr[:max_len] + f"\n... (truncated)"

        return {
            "stdout": stdout,
            "stderr": stderr,
            "display_data": "\n".join(display_parts) if display_parts else None,
            "success": success,
            "error": error_msg,
            "execution_count": exec_count,
            "execution_time_ms": elapsed_ms,
            "new_variables": [],
        }

    def _build_cell_outputs(self, result: Dict) -> list:
        """Convert execution result into nbformat cell outputs."""
        outputs = []
        if result.get("stdout"):
            outputs.append(nbformat.v4.new_output("stream", text=result["stdout"], name="stdout"))
        if result.get("stderr"):
            outputs.append(nbformat.v4.new_output("stream", text=result["stderr"], name="stderr"))
        if result.get("display_data"):
            outputs.append(
                nbformat.v4.new_output(
                    "execute_result",
                    data={"text/plain": result["display_data"]},
                    execution_count=result.get("execution_count"),
                )
            )
        if result.get("error"):
            outputs.append(
                nbformat.v4.new_output(
                    "error",
                    ename="ExecutionError",
                    evalue=result["error"],
                    traceback=[result.get("stderr", result["error"])],
                )
            )
        return outputs
