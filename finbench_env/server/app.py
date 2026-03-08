"""
FastAPI server for the FinBench Environment.

Usage:
    uvicorn finbench_env.server.app:app --reload --host 0.0.0.0 --port 8000

Environment Variables:
    FINBENCH_DATA_PATH: Path to data directory (default: ./data)
    FINBENCH_MAX_STEPS: Maximum tool calls per episode (default: 30)
    FINBENCH_TRACES_DIR: Path for saving traces (default: ./traces)
"""

import json
import os
from typing import Any, Dict, Literal, Optional

from openenv.core.env_server.http_server import create_app
from openenv.core.env_server.mcp_types import CallToolObservation
from openenv.core.env_server.types import Action
from pydantic import Field, field_validator, model_validator

from .finbench_environment import FinBenchEnvironment

DATA_PATH = os.environ.get("FINBENCH_DATA_PATH", "./data")
MAX_STEPS = int(os.environ.get("FINBENCH_MAX_STEPS", "30"))
TRACES_DIR = os.environ.get("FINBENCH_TRACES_DIR", "./traces")
MANIFEST_PATH = os.environ.get("FINBENCH_MANIFEST_PATH")
TASK_SPLIT = os.environ.get("FINBENCH_TASK_SPLIT")


def _env_factory():
    """Create a new FinBenchEnvironment instance for each session."""
    return FinBenchEnvironment(
        data_path=DATA_PATH,
        max_steps=MAX_STEPS,
        traces_dir=TRACES_DIR,
        manifest_path=MANIFEST_PATH,
        task_split=TASK_SPLIT,
    )


class FinBenchAction(Action):
    """Action schema that supports both MCP list and call operations over WebSocket."""

    type: Literal["list_tools", "call_tool"]
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments", mode="before")
    @classmethod
    def parse_arguments(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, str):
            return json.loads(v)
        return v or {}

    @model_validator(mode="after")
    def validate_call_tool_payload(self) -> "FinBenchAction":
        if self.type == "call_tool" and not self.tool_name:
            raise ValueError("tool_name is required when type='call_tool'")
        return self


app = create_app(
    _env_factory, FinBenchAction, CallToolObservation, env_name="finbench_env"
)


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

