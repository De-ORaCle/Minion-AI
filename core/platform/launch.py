"""Shared launch-command helpers for autostart backends."""

import sys
from pathlib import Path
from typing import List


def get_launch_parts(minimized: bool = True) -> List[str]:
    """
    Return argv-style parts to launch Minion.

    Frozen builds use the executable alone; source runs use python + app.py.
    """
    if getattr(sys, "frozen", False):
        parts = [str(Path(sys.executable).resolve())]
    else:
        python_exe = str(Path(sys.executable).resolve())
        app_script = str(Path(__file__).resolve().parent.parent.parent / "app.py")
        parts = [python_exe, app_script]
    if minimized:
        parts.append("--minimized")
    return parts


def get_launch_command(minimized: bool = True) -> str:
    """Quoted command line string suitable for Windows registry Run keys."""
    flag = " --minimized" if minimized else ""
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable).resolve()
        return f'"{exe_path}"{flag}'
    python_exe = Path(sys.executable).resolve()
    app_script = Path(__file__).resolve().parent.parent.parent / "app.py"
    return f'"{python_exe}" "{app_script}"{flag}'
