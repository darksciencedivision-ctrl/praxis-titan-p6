"""
io_utils.py – Utility IO helpers for PRAXIS v1.1 Titan
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

# Correct relative import for reporting module
from . import reporting


def write_text(path: str | Path, content: str) -> None:
    """Write plain text to a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


def write_json(path: str | Path, data: Dict[str, Any]) -> None:
    """Write JSON to a file."""
    import json
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def write_markdown_report(out_path: str | Path, praxis_output: Dict[str, Any]) -> None:
    """
    Build the Markdown report using the reporting module.

    out_path: full file path for the .md file.
    praxis_output: full PRAXIS result dict.
    """
    reporting.write_markdown_report(out_path, praxis_output)

