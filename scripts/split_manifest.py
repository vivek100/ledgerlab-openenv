#!/usr/bin/env python3
"""
Split task_manifest.json into train/val/test manifests based on 'split' field.

This script:
1. Reads data/tasks/task_manifest.json
2. Groups tasks by their 'split' field (train/val/test)
3. Writes separate manifest files for each split
4. Validates the split distribution

Usage:
    python scripts/split_manifest.py

The script expects each task to have a 'split' field.
If missing, it will assign splits automatically based on sector.
"""

import json
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "data" / "tasks" / "task_manifest.json"
TRAIN_PATH = BASE_DIR / "data" / "tasks" / "train_manifest.json"
VAL_PATH = BASE_DIR / "data" / "tasks" / "val_manifest.json"
TEST_PATH = BASE_DIR / "data" / "tasks" / "test_manifest.json"


def assign_splits(tasks):
    """
    Assign train/val/test splits to tasks that don't have them.
    
    Strategy:
    - Synthetic tasks (task_*) → test
    - GDPval tasks → stratified by sector (75% train, 25% val)
    """
    synthetic = []
    gdpval = []
    
    for task in tasks:
        if task.get("split"):
            continue  # Already has split
        
        if task["task_id"].startswith("task_"):
            task["split"] = "test"
            synthetic.append(task)
        else:
            gdpval.append(task)
    
    # Group GDPval by sector
    by_sector = {}
    for task in gdpval:
        sector = task.get("sector", "Unknown")
        by_sector.setdefault(sector, []).append(task)
    
    # Stratified split within each sector
    for sector, sector_tasks in by_sector.items():
        n = len(sector_tasks)
        n_val = max(1, n // 4)  # 25% val, at least 1
        
        # Sort by task_id for deterministic split
        sector_tasks.sort(key=lambda t: t["task_id"])
        
        for i, task in enumerate(sector_tasks):
            task["split"] = "val" if i < n_val else "train"
    
    return tasks


def main():
    print("=" * 70)
    print("Manifest Splitter")
    print("=" * 70)
    
    # Load master manifest
    with open(MANIFEST_PATH) as f:
        tasks = json.load(f)
    print(f"\nLoaded {len(tasks)} tasks from {MANIFEST_PATH}")
    
    # Check if splits exist
    with_split = sum(1 for t in tasks if t.get("split"))
    if with_split < len(tasks):
        print(f"  {len(tasks) - with_split} tasks missing 'split' field")
        print("  Assigning splits automatically...")
        tasks = assign_splits(tasks)
        
        # Write back updated master manifest
        with open(MANIFEST_PATH, "w") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Updated master manifest with splits")
    
    # Split tasks
    train_tasks = [t for t in tasks if t.get("split") == "train"]
    val_tasks = [t for t in tasks if t.get("split") == "val"]
    test_tasks = [t for t in tasks if t.get("split") == "test"]
    
    print(f"\nSplit distribution:")
    print(f"  Train: {len(train_tasks)} tasks")
    print(f"  Val:   {len(val_tasks)} tasks")
    print(f"  Test:  {len(test_tasks)} tasks")
    
    # Show sector distribution
    print(f"\nTrain tasks by sector:")
    train_sectors = Counter(t.get("sector", "Synthetic") for t in train_tasks)
    for sector, count in train_sectors.most_common():
        print(f"  {sector:45s} {count:2d}")
    
    print(f"\nVal tasks by sector:")
    val_sectors = Counter(t.get("sector", "Synthetic") for t in val_tasks)
    for sector, count in val_sectors.most_common():
        print(f"  {sector:45s} {count:2d}")
    
    # Write split manifests
    with open(TRAIN_PATH, "w") as f:
        json.dump(train_tasks, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Wrote {TRAIN_PATH}")
    
    with open(VAL_PATH, "w") as f:
        json.dump(val_tasks, f, indent=2, ensure_ascii=False)
    print(f"✓ Wrote {VAL_PATH}")
    
    with open(TEST_PATH, "w") as f:
        json.dump(test_tasks, f, indent=2, ensure_ascii=False)
    print(f"✓ Wrote {TEST_PATH}")
    
    print("\n" + "=" * 70)
    print("Split complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
