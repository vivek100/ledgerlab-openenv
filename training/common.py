#!/usr/bin/env python3
"""Shared training helpers for LedgerLab / FinBench."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data"
TRACES_DIR = ROOT / "traces"
DEFAULT_TRAIN_MANIFEST = DATA_PATH / "tasks" / "train_manifest.json"
DEFAULT_VAL_MANIFEST = DATA_PATH / "tasks" / "val_manifest.json"


def load_manifest_tasks(manifest_path: str | Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    manifest_path = Path(manifest_path)
    tasks = json.loads(manifest_path.read_text(encoding="utf-8"))
    if limit is not None:
        tasks = tasks[:limit]
    return tasks


def build_task_record(task: Dict[str, Any]) -> str:
    payload = {
        "task_id": task.get("task_id"),
        "task_prompt": task.get("prompt", ""),
        "task_json": json.dumps(task),
        "expected_deliverables": task.get("expected_deliverables", []) or [],
        "submission_fields": task.get("submission_fields", []) or [],
    }
    return json.dumps(payload)


def parse_task_record(record: str) -> Dict[str, Any]:
    payload = json.loads(record)
    if not isinstance(payload, dict):
        raise ValueError("task record must decode to a dictionary")
    return payload


def augment_task_message(task_message: str, task: Dict[str, Any]) -> str:
    expected = task.get("expected_deliverables", []) or []
    if expected:
        deliverable_lines = "\n".join(f"- output/{name}" for name in expected)
        task_message = (
            f"{task_message}\n\n"
            "Required deliverable filenames (use EXACT paths):\n"
            f"{deliverable_lines}\n"
        )

    sub_fields = task.get("submission_fields", []) or []
    if sub_fields:
        field_lines = []
        for sf in sub_fields:
            field_lines.append(
                f"- {sf['key']}: {sf['description']} (type: {sf['type']})"
            )
        task_message = (
            f"{task_message}\n\n"
            "VERIFICATION FIELDS - when you call submit(), include submission_values JSON with these keys:\n"
            + "\n".join(field_lines)
            + "\nCompute these from your analysis and include them in submit(submission_values='{...}').\n"
        )

    return task_message


def create_env(*, max_steps: int, manifest_path: str | Path | None = None, task_split: Optional[str] = None):
    from finbench_env.server.finbench_environment import FinBenchEnvironment

    return FinBenchEnvironment(
        data_path=str(DATA_PATH),
        traces_dir=str(TRACES_DIR),
        max_steps=max_steps,
        manifest_path=str(manifest_path) if manifest_path else None,
        task_split=task_split,
    )
