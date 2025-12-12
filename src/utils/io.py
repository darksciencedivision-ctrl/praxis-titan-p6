"""
PRAXIS P6 TITAN — Unified JSON + file I/O helpers.
This module exposes both legacy and new names:
    - read_json / write_json  (old)
    - load_json / save_json   (new, used by P6.1 engine)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


# ---------------------------------------------------------------------------
# JSON Loading
# ---------------------------------------------------------------------------

def read_json(path: Path | str) -> Dict[str, Any]:
    """Legacy interface — kept for backward compatibility."""
    return load_json(path)


def load_json(path: Path | str) -> Dict[str, Any]:
    """Primary JSON-load function used by PRAXIS P6.1."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"JSON file does not exist: {p}")

    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# JSON Writing
# ---------------------------------------------------------------------------

def write_json(path: Path | str, data: Dict[str, Any]) -> None:
    """Legacy interface — kept for backward compatibility."""
    save_json(path, data)


def save_json(path: Path | str, data: Dict[str, Any]) -> None:
    """Primary JSON-save function used by PRAXIS P6.1."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Text & path helpers
# ---------------------------------------------------------------------------

def read_text(path: Path | str) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8")


def write_text(path: Path | str, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
