#!/usr/bin/env python3
"""
Curate one shared real-task set from GDPval and download assets locally.

This is the main dataset builder for FinBench now. It:
1. Loads the real OpenAI GDPval dataset
2. Filters to tasks our environment can currently support
3. Ranks candidates by rubric size / file complexity
4. Downloads reference files and gold deliverables
5. Writes `data/tasks/task_manifest.json`

The manifest keeps the original GDPval rubrics so we can:
- run qualitative evals immediately
- improve deterministic check conversion over time
- compare agent outputs against gold deliverables during debugging

Usage:
    python scripts/download_tasks.py
    python scripts/download_tasks.py --limit 12
    python scripts/download_tasks.py --task-id 83d10b06-26d1-4636-a32c-23f92c57f30b
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import unquote, urlsplit

import requests
from datasets import load_dataset


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
DATA_DIR = ROOT / "data" / "tasks"
WORKSPACES_DIR = DATA_DIR / "workspaces"
SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".txt"}

if ENV_FILE.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV_FILE, override=False)
    except Exception:
        pass


def _ext(path: str) -> str:
    return Path(path).suffix.lower()


def _is_supported(path: str) -> bool:
    return _ext(path) in SUPPORTED_EXTENSIONS


def _is_spreadsheet(path: str) -> bool:
    return _ext(path) in {".xlsx", ".xls", ".csv"}


def _normalize_basename(path_or_url: str) -> str:
    name = os.path.basename(urlsplit(path_or_url).path)
    return unquote(name)


def _parse_rubric_items(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        parsed = json.loads(row.get("rubric_json") or "[]")
    except json.JSONDecodeError:
        parsed = []

    rubric = []
    for item in parsed:
        rubric.append({
            "score": item.get("score", 1),
            "criterion": item.get("criterion", ""),
            "rubric_item_id": item.get("rubric_item_id"),
            "tags": item.get("tags", []),
        })
    return rubric


def _candidate_score(row: Dict[str, Any]) -> Tuple[int, int, int, int]:
    rubric_items = len(_parse_rubric_items(row))
    multi_ref_bonus = len(row.get("reference_files", []))
    prompt = (row.get("prompt") or "").lower()
    keyword_bonus = sum(
        1 for kw in (
            "variance",
            "reconcile",
            "forecast",
            "schedule",
            "sample",
            "analysis",
            "workbook",
            "worksheet",
            "tab",
            "column",
        )
        if kw in prompt
    )
    spreadsheet_refs = sum(1 for path in row.get("reference_files", []) if _is_spreadsheet(path))
    return (rubric_items, multi_ref_bonus, spreadsheet_refs, keyword_bonus)


def _supported_row(row: Dict[str, Any]) -> bool:
    refs = row.get("reference_files", [])
    dels = row.get("deliverable_files", [])
    if not refs or not dels:
        return False
    if not all(_is_supported(path) for path in refs):
        return False
    if not all(_is_supported(path) for path in dels):
        return False
    if not any(_is_spreadsheet(path) for path in refs):
        return False
    if not any(_is_spreadsheet(path) or _ext(path) == ".txt" for path in dels):
        return False
    return True


def _build_manifest_entry(row: Dict[str, Any]) -> Dict[str, Any]:
    rubric = _parse_rubric_items(row)
    return {
        "task_id": row["task_id"],
        "source": "gdpval",
        "sector": row.get("sector"),
        "occupation": row.get("occupation"),
        "prompt": row.get("prompt", ""),
        "reference_files": [_normalize_basename(x) for x in row.get("reference_files", [])],
        "reference_file_urls": row.get("reference_file_urls", []),
        "deliverable_files": [_normalize_basename(x) for x in row.get("deliverable_files", [])],
        "deliverable_file_urls": row.get("deliverable_file_urls", []),
        "expected_deliverables": [_normalize_basename(x) for x in row.get("deliverable_files", [])],
        "rubric": rubric,
        "rubric_pretty": row.get("rubric_pretty", ""),
        "rubric_json": row.get("rubric_json", "[]"),
        "checks": [],
        "difficulty_signals": {
            "rubric_items": len(rubric),
            "reference_files": len(row.get("reference_files", [])),
            "deliverable_files": len(row.get("deliverable_files", [])),
        },
    }


def _download_file(url: str, dest: Path, token: str | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with requests.get(url, stream=True, timeout=120, headers=headers) as response:
        response.raise_for_status()
        with open(dest, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def curate_rows(limit: int, task_id: str | None = None) -> List[Dict[str, Any]]:
    dataset = load_dataset("openai/gdpval", "default", split="train")
    rows = [dict(row) for row in dataset if _supported_row(dict(row))]
    rows.sort(key=_candidate_score, reverse=True)

    if task_id:
        rows = [row for row in rows if row["task_id"] == task_id]
    else:
        rows = rows[:limit]
    return rows


def write_manifest(rows: List[Dict[str, Any]], token: str | None = None) -> Path:
    manifest = []
    for row in rows:
        task_id = row["task_id"]
        task_dir = WORKSPACES_DIR / task_id
        ref_dir = task_dir / "reference"
        gold_dir = task_dir / "gold"
        ref_dir.mkdir(parents=True, exist_ok=True)
        gold_dir.mkdir(parents=True, exist_ok=True)

        for src_path, src_url in zip(row.get("reference_files", []), row.get("reference_file_urls", [])):
            filename = _normalize_basename(src_path)
            _download_file(src_url, ref_dir / filename, token=token)

        for src_path, src_url in zip(row.get("deliverable_files", []), row.get("deliverable_file_urls", [])):
            filename = _normalize_basename(src_path)
            _download_file(src_url, gold_dir / filename, token=token)

        manifest.append(_build_manifest_entry(row))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = DATA_DIR / "task_manifest.json"
    with open(manifest_path, "w") as handle:
        json.dump(manifest, handle, indent=2)

    report = {
        "task_count": len(manifest),
        "task_ids": [task["task_id"] for task in manifest],
        "sources": ["gdpval"],
    }
    with open(DATA_DIR / "curation_report.json", "w") as handle:
        json.dump(report, handle, indent=2)

    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and curate GDPval tasks for FinBench")
    parser.add_argument("--limit", type=int, default=12, help="Number of tasks to keep")
    parser.add_argument("--task-id", default=None, help="Single GDPval task_id to download")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN")
    rows = curate_rows(limit=args.limit, task_id=args.task_id)
    if not rows:
        raise SystemExit("No supported GDPval tasks matched the current filter.")

    manifest_path = write_manifest(rows, token=token)
    print(f"Curated {len(rows)} GDPval tasks")
    for row in rows:
        rubric_items = len(_parse_rubric_items(row))
        print(
            f"  {row['task_id']} | rubric_items={rubric_items} | "
            f"refs={len(row.get('reference_files', []))} | dels={len(row.get('deliverable_files', []))}"
        )
    print(f"\nManifest written to: {manifest_path}")


if __name__ == "__main__":
    main()
