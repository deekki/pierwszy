from __future__ import annotations

import json
import os
from typing import Any


def get_pattern_dir() -> str:
    env_dir = os.getenv("PALLETIZER_PATTERN_DIR")
    if env_dir:
        return os.path.abspath(os.path.expanduser(env_dir))
    default_dir = os.path.join(os.getcwd(), "data", "pallet_patterns")
    return os.path.abspath(default_dir)


def ensure_pattern_dir() -> str:
    path = get_pattern_dir()
    os.makedirs(path, exist_ok=True)
    return path


def _pattern_path(name: str) -> str:
    return os.path.join(get_pattern_dir(), f"{name}.json")


def list_pattern_files() -> list[str]:
    path = ensure_pattern_dir()
    files = [f[:-5] for f in os.listdir(path) if f.endswith(".json")]
    files.sort()
    return files


def load_pattern(name: str) -> Any:
    with open(_pattern_path(name), "r", encoding="utf-8") as f:
        return json.load(f)


def save_pattern(name: str, payload: Any) -> None:
    ensure_pattern_dir()
    with open(_pattern_path(name), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
