from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
PYTHON_PATHS = [
    ROOT_DIR / "backend" / "api",
    ROOT_DIR / "backend" / "core",
    ROOT_DIR / "backend" / "models",
    ROOT_DIR / "backend" / "services",
    ROOT_DIR / "agent" / "collectors",
    ROOT_DIR / "agent" / "detectors",
    ROOT_DIR / "agent" / "windows",
]


def bootstrap_paths() -> Path:
    for path in reversed(PYTHON_PATHS):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)
    root_text = str(ROOT_DIR)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    return ROOT_DIR

