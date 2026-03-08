"""
FinBench: Notebook-Driven Financial Analysis Agent Environment.

An OpenEnv environment that trains agents to work like data analysts —
creating notebooks, running cells iteratively, and producing deliverables
evaluated against GDPval rubrics.

Uses MCP protocol for tool interactions:
    from openenv.core.env_server.mcp_types import CallToolAction, ListToolsAction
"""

from .client import FinBenchEnv, FinBenchRemoteEnv
from .models import FinBenchState, AVAILABLE_TOOLS

__all__ = [
    "FinBenchEnv",
    "FinBenchRemoteEnv",
    "FinBenchState",
    "AVAILABLE_TOOLS",
]
