from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


def sha256_of_strings(chunks: Iterable[str]) -> str:
    """
    Compute a SHA256 hash over one or more text chunks.
    """
    h = hashlib.sha256()
    for chunk in chunks:
        h.update(chunk.encode("utf-8"))
    return h.hexdigest()


def sha256_of_file(path: str | Path) -> str:
    """
    Compute SHA256 of a file's contents.
    """
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()
