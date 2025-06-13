import json
import os

PATTERN_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'pallet_patterns')


def _ensure_dir() -> None:
    os.makedirs(PATTERN_DIR, exist_ok=True)


def pattern_path(name: str) -> str:
    return os.path.join(PATTERN_DIR, f"{name}.json")


def save_pattern(name: str, data: dict) -> None:
    """Save pattern data under the given name."""
    _ensure_dir()
    with open(pattern_path(name), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_pattern(name: str) -> dict:
    """Load pattern data by name."""
    with open(pattern_path(name), 'r', encoding='utf-8') as f:
        return json.load(f)


def list_patterns() -> list:
    """Return available pattern names."""
    _ensure_dir()
    files = [f[:-5] for f in os.listdir(PATTERN_DIR) if f.endswith('.json')]
    files.sort()
    return files
