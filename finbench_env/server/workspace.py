"""
Workspace file operations: list, read, write, search, create folders.
"""

import mimetypes
import os
import re
from typing import List, Optional


class Workspace:
    """Manages the episode workspace filesystem."""

    def __init__(self, root_path: str):
        self.root = root_path

    def list_files(self, path: str = "/") -> str:
        base = os.path.join(self.root, path.lstrip("/"))
        if not os.path.exists(base):
            return f"Path not found: {path}"
        if not os.path.isdir(base):
            return f"Not a directory: {path}"

        items = []
        for entry in sorted(os.scandir(base), key=lambda e: (not e.is_dir(), e.name)):
            if entry.is_dir():
                count = sum(1 for _ in os.scandir(entry.path))
                items.append(f"  [DIR]  {entry.name}/  ({count} items)")
            else:
                size = entry.stat().st_size
                mime, _ = mimetypes.guess_type(entry.path)
                ext = mime or "unknown"
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                items.append(f"  [FILE] {entry.name}  ({ext}, {size_str})")

        if not items:
            return f"{path}: (empty directory)"
        return f"{path}:\n" + "\n".join(items)

    def read_file(self, path: str) -> str:
        full = os.path.join(self.root, path.lstrip("/"))
        if not os.path.exists(full):
            return f"File not found: {path}"
        if os.path.isdir(full):
            return f"Is a directory, not a file: {path}"

        if full.endswith((".xlsx", ".xls")):
            return self._read_excel_preview(full)
        if full.endswith((".png", ".jpg", ".jpeg", ".gif")):
            return f"[Binary image file: {path}, {os.path.getsize(full)} bytes]"

        try:
            with open(full, "r", errors="replace") as f:
                content = f.read()
            if len(content) > 30000:
                return content[:30000] + f"\n... (truncated, {len(content)} chars total)"
            return content
        except Exception as e:
            return f"Error reading {path}: {e}"

    def _read_excel_preview(self, full_path: str) -> str:
        """Read Excel file and return a text summary."""
        try:
            import pandas as pd

            xl = pd.ExcelFile(full_path)
            parts = [f"Excel file with {len(xl.sheet_names)} sheet(s): {xl.sheet_names}"]
            for sheet in xl.sheet_names[:5]:
                df = xl.parse(sheet)
                parts.append(f"\n--- Sheet: '{sheet}' ({len(df)} rows, {len(df.columns)} cols) ---")
                parts.append(f"Columns: {df.columns.tolist()}")
                parts.append(df.head(10).to_string(index=False))
            return "\n".join(parts)
        except Exception as e:
            return f"Error reading Excel: {e}"

    def write_file(self, path: str, content: str) -> str:
        full = os.path.join(self.root, path.lstrip("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
        return f"Written {len(content)} chars to {path}"

    def create_folder(self, path: str) -> str:
        full = os.path.join(self.root, path.lstrip("/"))
        os.makedirs(full, exist_ok=True)
        return f"Folder created: {path}"

    def search_files(
        self,
        query: str,
        path: str = "/",
        file_pattern: str = "*",
    ) -> str:
        """Grep-like search across workspace files."""
        base = os.path.join(self.root, path.lstrip("/"))
        if not os.path.exists(base):
            return f"Path not found: {path}"

        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            pattern = re.compile(re.escape(query), re.IGNORECASE)

        import fnmatch

        matches = []
        for dirpath, _, filenames in os.walk(base):
            for fname in filenames:
                if not fnmatch.fnmatch(fname, file_pattern):
                    continue
                fpath = os.path.join(dirpath, fname)
                rel = os.path.relpath(fpath, self.root)

                if fpath.endswith((".xlsx", ".xls", ".png", ".jpg", ".ipynb")):
                    continue

                try:
                    with open(fpath, "r", errors="replace") as f:
                        for lineno, line in enumerate(f, 1):
                            if pattern.search(line):
                                snippet = line.strip()[:120]
                                matches.append(f"{rel}:{lineno}: {snippet}")
                                if len(matches) >= 50:
                                    break
                except Exception:
                    continue

                if len(matches) >= 50:
                    break

        if not matches:
            return f"No matches for '{query}' in {path}"
        return f"Found {len(matches)} match(es):\n" + "\n".join(matches)

    def get_all_files(self) -> List[str]:
        """List all files in workspace (relative paths)."""
        files = []
        for dirpath, _, filenames in os.walk(self.root):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                files.append(os.path.relpath(fpath, self.root))
        return files

    def file_exists(self, path: str) -> bool:
        return os.path.exists(os.path.join(self.root, path.lstrip("/")))
