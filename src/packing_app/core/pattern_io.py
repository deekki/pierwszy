import os

from palletizer_core.pattern_io import (
    ensure_pattern_dir,
    get_pattern_dir,
    list_pattern_files,
    load_pattern,
    save_pattern,
)


def pattern_path(name: str) -> str:
    return os.path.join(get_pattern_dir(), f"{name}.json")


def list_patterns() -> list[str]:
    """Return available pattern names."""
    return list_pattern_files()
