import os
import sys


def _ensure_src_on_path() -> None:
    src_path = os.path.join(os.path.dirname(__file__), "src")
    if os.path.isdir(src_path) and src_path not in sys.path:
        sys.path.insert(0, src_path)


def _import_app_main():
    try:
        from packing_app.__main__ import main as app_main
        return app_main
    except ImportError:
        _ensure_src_on_path()
        from packing_app.__main__ import main as app_main
        return app_main


def main() -> None:
    app_main = _import_app_main()
    app_main()


if __name__ == "__main__":
    main()
