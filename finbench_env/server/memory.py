"""
Memory bank: persistent notebook templates across episodes.

Pre-seeded with example templates and grows as agent saves useful notebooks.
"""

import json
import os
import shutil
from typing import Dict, List, Optional


class MemoryBank:
    """Manages the /memory/ folder in the workspace."""

    MANIFEST_FILE = "manifest.json"

    def __init__(self, memory_path: str):
        self.path = memory_path
        os.makedirs(self.path, exist_ok=True)
        self._ensure_manifest()

    def _ensure_manifest(self) -> None:
        manifest_path = os.path.join(self.path, self.MANIFEST_FILE)
        if not os.path.exists(manifest_path):
            self._write_manifest({})

    def _read_manifest(self) -> Dict:
        manifest_path = os.path.join(self.path, self.MANIFEST_FILE)
        try:
            with open(manifest_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write_manifest(self, data: Dict) -> None:
        manifest_path = os.path.join(self.path, self.MANIFEST_FILE)
        with open(manifest_path, "w") as f:
            json.dump(data, f, indent=2)

    def save_to_memory(
        self,
        source_path: str,
        name: str,
        tags: List[str],
        description: str,
    ) -> str:
        """Copy a notebook into the memory bank with metadata."""
        if not os.path.exists(source_path):
            return f"Source not found: {source_path}"

        dest_filename = f"{name}.ipynb"
        dest_path = os.path.join(self.path, dest_filename)
        shutil.copy2(source_path, dest_path)

        import nbformat
        try:
            with open(dest_path) as f:
                nb = nbformat.read(f, as_version=4)
            cell_count = len(nb.cells)
        except Exception:
            cell_count = 0

        manifest = self._read_manifest()
        manifest[name] = {
            "filename": dest_filename,
            "tags": tags,
            "description": description,
            "cell_count": cell_count,
        }
        self._write_manifest(manifest)

        return f"Saved '{name}' to memory ({cell_count} cells, tags: {tags})"

    def list_memory(self, tags: Optional[List[str]] = None) -> List[Dict]:
        """List all templates, optionally filtered by tags."""
        manifest = self._read_manifest()
        entries = []
        for name, meta in manifest.items():
            if tags:
                if not any(t in meta.get("tags", []) for t in tags):
                    continue
            entries.append({
                "name": name,
                "path": f"memory/{meta['filename']}",
                "tags": meta.get("tags", []),
                "description": meta.get("description", ""),
                "cell_count": meta.get("cell_count", 0),
            })
        return entries

    def load_from_memory(self, name: str, dest_dir: str) -> str:
        """Copy a memory template into the workspace working directory."""
        manifest = self._read_manifest()
        if name not in manifest:
            return f"Template '{name}' not found in memory"

        source = os.path.join(self.path, manifest[name]["filename"])
        if not os.path.exists(source):
            return f"Template file missing: {manifest[name]['filename']}"

        dest = os.path.join(dest_dir, f"{name}.ipynb")
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(source, dest)
        return f"Loaded '{name}' to {os.path.relpath(dest, os.path.dirname(dest_dir))}"

    def seed_from_directory(self, seed_dir: str) -> int:
        """Load pre-seeded templates from a directory."""
        if not os.path.exists(seed_dir):
            return 0

        count = 0
        seed_manifest = os.path.join(seed_dir, self.MANIFEST_FILE)
        if os.path.exists(seed_manifest):
            with open(seed_manifest) as f:
                seed_data = json.load(f)
        else:
            seed_data = {}

        for fname in os.listdir(seed_dir):
            if not fname.endswith(".ipynb"):
                continue
            src = os.path.join(seed_dir, fname)
            dst = os.path.join(self.path, fname)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                name = fname.replace(".ipynb", "")
                if name not in self._read_manifest():
                    manifest = self._read_manifest()
                    manifest[name] = seed_data.get(name, {
                        "filename": fname,
                        "tags": ["example"],
                        "description": f"Pre-seeded template: {name}",
                        "cell_count": 0,
                    })
                    self._write_manifest(manifest)
                count += 1

        return count
