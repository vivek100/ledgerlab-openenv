"""
State types for the FinBench environment.

FinBench uses MCP protocol for tool interactions. Use CallToolAction and
ListToolsAction from openenv.core.env_server.mcp_types to interact.
"""

from typing import Dict, List, Optional

from openenv.core.env_server import State


AVAILABLE_TOOLS = [
    "list_files",
    "read_file",
    "write_file",
    "create_folder",
    "search_files",
    "create_notebook",
    "read_notebook",
    "add_cell",
    "edit_cell",
    "delete_cell",
    "run_cell",
    "write_and_run",
    "run_all",
    "get_kernel_state",
    "save_to_memory",
    "list_memory",
    "load_from_memory",
    "submit",
]


class FinBenchState(State):
    """
    Internal environment state for tracking the current episode.

    Attributes:
        task_id: Current task identifier
        task_prompt: Task description shown to agent
        workspace_path: Absolute path to episode workspace
        notebooks: Paths of notebooks in workspace
        kernel_variables: Variable names in kernel
        files_created: Files created by agent
        max_steps: Max tool calls per episode
        # Inherited from State: episode_id, step_count
    """

    task_id: str = ""
    task_prompt: str = ""
    workspace_path: str = ""
    notebooks: List[str] = []
    kernel_variables: List[str] = []
    files_created: List[str] = []
    max_steps: int = 30
