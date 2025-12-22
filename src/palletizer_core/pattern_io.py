from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def get_pattern_dir() -> str:
    env_dir = os.getenv("PALLETIZER_PATTERN_DIR")
    if env_dir:
        return str(Path(env_dir).expanduser().resolve())
    argv_path = Path(sys.argv[0]) if sys.argv[0] else None
    if argv_path and argv_path.is_file():
        base_dir = argv_path.parent
    else:
        base_dir = Path.cwd()
    default_dir = base_dir / "data" / "pallet_patterns"
    return str(default_dir.resolve())


def ensure_pattern_dir() -> str:
    path = Path(get_pattern_dir())
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _pattern_path(name: str) -> str:
    return str(Path(get_pattern_dir()) / f"{name}.json")


def list_pattern_files() -> list[str]:
    path = ensure_pattern_dir()
    files = [f[:-5] for f in os.listdir(path) if f.endswith(".json")]
    files.sort()
    return files


def list_patterns() -> list[str]:
    """Return available pattern names."""
    return list_pattern_files()


def load_pattern(name: str) -> Any:
    with open(_pattern_path(name), "r", encoding="utf-8") as f:
        return json.load(f)


def save_pattern(name: str, payload: Any) -> None:
    ensure_pattern_dir()
    with open(_pattern_path(name), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


__all__ = [
    "get_pattern_dir",
    "ensure_pattern_dir",
    "list_pattern_files",
    "list_patterns",
    "load_pattern",
    "save_pattern",
]
