#!/usr/bin/env python3
"""
Download new GDPval tasks (xlsx-only) from HuggingFace dataset.

This script:
1. Loads the GDPval dataset
2. Filters to xlsx-only deliverables not already in our manifest
3. Downloads reference files and gold deliverables
4. Adds new task entries to task_manifest.json

Run with:
    python scripts/download_gdpval_tasks.py [--limit N] [--dry-run]

Requirements:
    pip install datasets huggingface_hub requests
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import unquote

import requests
from datasets import load_dataset


BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "data" / "tasks" / "task_manifest.json"
WORKSPACES_DIR = BASE_DIR / "data" / "tasks" / "workspaces"


def download_file(url: str, dest_path: Path) -> bool:
    """Download a file from URL to dest_path. Returns True on success."""
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"  ✓ {dest_path.name} ({dest_path.stat().st_size // 1024} KB)")
        return True
    except Exception as e:
        print(f"  ✗ {dest_path.name}: {e}")
        return False


def extract_filename_from_url(url: str) -> str:
    """Extract clean filename from HF dataset URL."""
    # URLs look like: .../reference_files/hash/File%20Name.xlsx
    parts = unquote(url).split("/")
    return parts[-1]


def main():
    parser = argparse.ArgumentParser(description="Download GDPval xlsx tasks")
    parser.add_argument("--limit", type=int, help="Max tasks to download (for testing)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded without downloading")
    args = parser.parse_args()

    print("=" * 70)
    print("GDPval Task Downloader")
    print("=" * 70)

    # Load current manifest
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
        existing_ids = {task["task_id"] for task in manifest}
        print(f"\nCurrent manifest: {len(manifest)} tasks")
    else:
        manifest = []
        existing_ids = set()
        print(f"\nNo existing manifest, starting fresh")

    # Load GDPval dataset
    print(f"\nLoading GDPval dataset...")
    ds = load_dataset("openai/gdpval", split="train")
    print(f"  {len(ds)} total tasks in GDPval")

    # Filter to xlsx-only tasks not already in manifest
    xlsx_tasks = []
    for row in ds:
        urls = row.get("deliverable_file_urls") or []
        all_xlsx = all(u.endswith(".xlsx") for u in urls) and len(urls) > 0
        if all_xlsx and row["task_id"] not in existing_ids:
            xlsx_tasks.append(row)

    print(f"  {len(xlsx_tasks)} new xlsx-only tasks available")

    if args.limit:
        xlsx_tasks = xlsx_tasks[:args.limit]
        print(f"  Limited to {args.limit} tasks for testing")

    if not xlsx_tasks:
        print("\n✓ No new tasks to download.")
        return

    print(f"\n{'DRY RUN - ' if args.dry_run else ''}Downloading {len(xlsx_tasks)} tasks...")
    print()

    downloaded = 0
    failed = []

    for i, task in enumerate(xlsx_tasks, 1):
        task_id = task["task_id"]
        short_id = task_id[:12]
        sector = task.get("sector", "Unknown")[:40]
        
        print(f"[{i}/{len(xlsx_tasks)}] {short_id}  ({sector})")

        # Prepare workspace directories
        workspace = WORKSPACES_DIR / task_id
        ref_dir = workspace / "reference"
        gold_dir = workspace / "gold"

        if args.dry_run:
            print(f"  Would create: {workspace}")
            ref_urls = task.get("reference_file_urls") or []
            deliv_urls = task.get("deliverable_file_urls") or []
            print(f"  Reference files: {len(ref_urls)}")
            print(f"  Deliverable files: {len(deliv_urls)}")
            continue

        ref_dir.mkdir(parents=True, exist_ok=True)
        gold_dir.mkdir(parents=True, exist_ok=True)

        # Download reference files
        ref_urls = task.get("reference_file_urls") or []
        ref_files = []
        for url in ref_urls:
            filename = extract_filename_from_url(url)
            dest = ref_dir / filename
            if download_file(url, dest):
                ref_files.append(filename)

        # Download deliverable (gold) files
        deliv_urls = task.get("deliverable_file_urls") or []
        deliv_files = []
        for url in deliv_urls:
            filename = extract_filename_from_url(url)
            dest = gold_dir / filename
            if download_file(url, dest):
                deliv_files.append(filename)

        if not deliv_files:
            print(f"  ⚠ No deliverables downloaded, skipping task")
            failed.append(short_id)
            continue

        # Add to manifest
        new_task = {
            "task_id": task_id,
            "source": "gdpval",
            "sector": task.get("sector", "Unknown"),
            "occupation": task.get("occupation", "Unknown"),
            "prompt": task.get("prompt", ""),
            "reference_files": ref_files,
            "reference_file_urls": ref_urls,
            "deliverable_files": deliv_files,
            "deliverable_file_urls": deliv_urls,
            "expected_deliverables": deliv_files,
            "rubric": task.get("rubric_json", []),
        }
        manifest.append(new_task)
        downloaded += 1
        print()

    if args.dry_run:
        print(f"\n✓ Dry run complete. Would download {len(xlsx_tasks)} tasks.")
        return

    # Write updated manifest
    if downloaded > 0:
        with open(MANIFEST_PATH, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print("=" * 70)
        print(f"✓ Successfully downloaded {downloaded} tasks")
        print(f"✓ Updated manifest: {MANIFEST_PATH}")
        print(f"  Total tasks in manifest: {len(manifest)}")
        if failed:
            print(f"  Failed tasks: {len(failed)} ({', '.join(failed)})")
    else:
        print("\n✗ No tasks were successfully downloaded.")
        sys.exit(1)


if __name__ == "__main__":
    main()
