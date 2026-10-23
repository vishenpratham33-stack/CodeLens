"""Where do the program's own files live?

When you run from source, they are next to the code. When CodeLens is
packed into a single .exe, PyInstaller unpacks them into a temporary
folder and tells us where in sys._MEIPASS.
"""

import sys
from pathlib import Path

def resource_dir() -> Path:
    frozen_base = getattr(sys, "_MEIPASS", None)
    if frozen_base:
        return Path(frozen_base)
    return Path(__file__).resolve().parent.parent

def web_dir() -> Path:
    return resource_dir() / "web"