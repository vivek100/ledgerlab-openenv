#!/usr/bin/env python3
"""Create a standalone Hugging Face Space bundle for FinBench."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / 'dist' / 'hf_space'
COPY_DIRS = ['finbench_env', 'data']
COPY_FILES = ['.dockerignore']


def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(
            '__pycache__',
            '*.pyc',
            '*.pyo',
            '.DS_Store',
            '.gitkeep',
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description='Prepare Hugging Face Space bundle')
    parser.add_argument('--output-dir', default=str(DEFAULT_OUTPUT), help='Bundle output directory')
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for rel in COPY_DIRS:
        copy_tree(ROOT / rel, output_dir / rel)

    for rel in COPY_FILES:
        shutil.copy2(ROOT / rel, output_dir / rel)

    shutil.copy2(ROOT / 'Dockerfile.space', output_dir / 'Dockerfile')
    shutil.copy2(ROOT / 'hf_space' / 'README.md', output_dir / 'README.md')
    shutil.copy2(ROOT / 'hf_space' / '.gitattributes', output_dir / '.gitattributes')

    print(f'Created HF Space bundle at: {output_dir}')


if __name__ == '__main__':
    main()
