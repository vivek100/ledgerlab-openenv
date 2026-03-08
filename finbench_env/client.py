"""
FinBench Environment Client.

Works locally (no server needed) â€” perfect for quick testing and training.

Usage:
    from finbench_env.client import FinBenchEnv

    env = FinBenchEnv()
    obs = env.reset(task_id="task_001")
    print(obs.metadata["tool_result"])

    obs = env.call_tool("list_files", path="/reference")
    obs = env.call_tool("create_notebook", path="work/analysis.ipynb")
    obs = env.call_tool("write_and_run", notebook="work/analysis.ipynb",
                         source="import pandas as pd; print('ok')")
    obs = env.call_tool("submit")
"""

from __future__ import annotations

from typing import Any, Optional

from openenv.core.mcp_client import MCPToolClient
from openenv.core.env_server.mcp_types import CallToolAction, ListToolsAction


class FinBenchEnv:
    """Local-first client for FinBench environment."""

    def __init__(
        self,
        data_path: str = "./data",
        memory_seed_path: Optional[str] = None,
        traces_dir: str = "./traces",
        max_steps: int = 30,
        manifest_path: Optional[str] = None,
        task_split: Optional[str] = None,
    ):
        self._data_path = data_path
        self._memory_seed_path = memory_seed_path
        self._traces_dir = traces_dir
        self._max_steps = max_steps
        self._manifest_path = manifest_path
        self._task_split = task_split
        self._env = None

    def _ensure_initialized(self) -> None:
        if self._env is not None:
            return
        from .server.finbench_environment import FinBenchEnvironment

        self._env = FinBenchEnvironment(
            data_path=self._data_path,
            memory_seed_path=self._memory_seed_path,
            traces_dir=self._traces_dir,
            max_steps=self._max_steps,
            manifest_path=self._manifest_path,
            task_split=self._task_split,
        )

    def reset(
        self,
        task_id: Optional[str] = None,
        task_json: Optional[str] = None,
        episode_id: Optional[str] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ):
        """Reset environment for new episode. Returns Observation."""
        self._ensure_initialized()
        return self._env.reset(
            seed=seed,
            episode_id=episode_id,
            task_id=task_id,
            task_json=task_json,
            **kwargs,
        )

    def call_tool(self, tool_name: str, **kwargs: Any):
        """Call an MCP tool by name. Returns Observation."""
        action = CallToolAction(tool_name=tool_name, arguments=kwargs)
        return self._env.step(action)

    def list_tools(self):
        """List available MCP tools. Returns ListToolsObservation."""
        return self._env.step(ListToolsAction())

    @property
    def state(self):
        return self._env.state

    def close(self) -> None:
        if self._env:
            self._env.close()
            self._env = None

    def __enter__(self) -> "FinBenchEnv":
        self._ensure_initialized()
        return self

    def __exit__(self, *args) -> None:
        self.close()



class FinBenchRemoteEnv(MCPToolClient):
    """Remote MCP client for Docker and Hugging Face Space deployments."""

    pass
