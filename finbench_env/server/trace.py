"""
Trace capture: logs every agent action with state snapshots.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional


class TraceLogger:
    """Captures a structured trace of the agent's episode."""

    def __init__(self, episode_id: str, task_id: str):
        self.episode_id = episode_id
        self.task_id = task_id
        self.steps: List[Dict[str, Any]] = []
        self.start_time = time.time()

    def log_step(
        self,
        tool: str,
        args: Dict[str, Any],
        result: Any,
        state_snapshot: Optional[Dict[str, Any]] = None,
        step_reward: float = 0.0,
    ) -> None:
        """Log a single tool call."""
        sanitized_args = {}
        for k, v in args.items():
            if isinstance(v, str) and len(v) > 2000:
                sanitized_args[k] = v[:2000] + "..."
            else:
                sanitized_args[k] = v

        sanitized_result = result
        if isinstance(result, str) and len(result) > 2000:
            sanitized_result = result[:2000] + "..."
        elif isinstance(result, dict):
            sanitized_result = {
                k: (v[:500] + "..." if isinstance(v, str) and len(v) > 500 else v)
                for k, v in result.items()
            }

        self.steps.append({
            "step": len(self.steps) + 1,
            "tool": tool,
            "args": sanitized_args,
            "result": sanitized_result,
            "step_reward": step_reward,
            "timestamp_ms": int((time.time() - self.start_time) * 1000),
            "state": state_snapshot or {},
        })

    def get_trace(self) -> Dict[str, Any]:
        """Return the full trace as a dict."""
        return {
            "episode_id": self.episode_id,
            "task_id": self.task_id,
            "total_steps": len(self.steps),
            "total_time_ms": int((time.time() - self.start_time) * 1000),
            "steps": self.steps,
        }

    def add_metadata(self, **kwargs: Any) -> None:
        """Attach top-level metadata to the trace."""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def save(self, traces_dir: str) -> str:
        """Save trace to a JSON file."""
        os.makedirs(traces_dir, exist_ok=True)
        path = os.path.join(traces_dir, f"{self.episode_id}.json")
        with open(path, "w") as f:
            trace = self.get_trace()
            for key, value in self.__dict__.items():
                if key not in trace and key not in {"steps", "start_time"}:
                    trace[key] = value
            json.dump(trace, f, indent=2, default=str)
        return path

    # ---- Query helpers for reward computation ----

    def first_index(self, tool: str = None, path_contains: str = None) -> int:
        """Find the first step matching criteria. Returns 999 if not found."""
        for i, s in enumerate(self.steps):
            if tool and s["tool"] != tool:
                continue
            if path_contains:
                path_val = s.get("args", {}).get("path", "") or s.get("args", {}).get("notebook", "")
                if path_contains not in path_val:
                    continue
            return i
        return 999

    def last_index(self, tool: str = None, tool_in: List[str] = None, path_contains: str = None) -> int:
        """Find the last step matching criteria. Returns -1 if not found."""
        for i in range(len(self.steps) - 1, -1, -1):
            s = self.steps[i]
            if tool and s["tool"] != tool:
                continue
            if tool_in and s["tool"] not in tool_in:
                continue
            if path_contains:
                path_val = s.get("args", {}).get("path", "") or s.get("args", {}).get("notebook", "")
                if path_contains not in path_val:
                    continue
            return i
        return -1

    def count_tool(self, tool: str) -> int:
        return sum(1 for s in self.steps if s["tool"] == tool)

    def count_successful_cells(self) -> int:
        return sum(
            1 for s in self.steps
            if s["tool"] in ("run_cell", "write_and_run")
            and (isinstance(s.get("result"), dict) and s["result"].get("success", False))
        )

    def has_error_then_fix(self) -> bool:
        """Check if agent ever fixed an error (edit after failed execution)."""
        for i, s in enumerate(self.steps):
            if s["tool"] in ("run_cell", "write_and_run"):
                result = s.get("result", {})
                if isinstance(result, dict) and not result.get("success", True):
                    for j in range(i + 1, min(i + 4, len(self.steps))):
                        if self.steps[j]["tool"] in ("edit_cell", "write_and_run", "add_cell"):
                            return True
        return False
