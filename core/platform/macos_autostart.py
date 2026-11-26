"""macOS login autostart via LaunchAgents plist."""

from __future__ import annotations

import logging
import plistlib
from pathlib import Path

from core.platform.launch import get_launch_parts

logger = logging.getLogger("Minion.Autostart")

LABEL = "com.minionai.app"
PLIST_NAME = f"{LABEL}.plist"


def _plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / PLIST_NAME


class MacOSAutostartBackend:
    """Writes ~/Library/LaunchAgents/com.minionai.app.plist for login start."""

    def is_enabled(self) -> bool:
        path = _plist_path()
        if not path.exists():
            return False
        try:
            with path.open("rb") as fh:
                data = plistlib.load(fh)
            return bool(data.get("RunAtLoad")) and data.get("Label") == LABEL
        except Exception as e:
            logger.debug(f"Autostart check encountered exception: {e}")
            return False

    def enable(self, minimized: bool = True) -> bool:
        try:
            agents_dir = _plist_path().parent
            agents_dir.mkdir(parents=True, exist_ok=True)

            program_args = get_launch_parts(minimized=minimized)
            payload = {
                "Label": LABEL,
                "ProgramArguments": program_args,
                "RunAtLoad": True,
                "KeepAlive": False,
            }
            with _plist_path().open("wb") as fh:
                plistlib.dump(payload, fh)
            logger.info(f"Minion AI macOS autostart enabled: {program_args}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable Minion AI autostart: {e}")
            return False

    def disable(self) -> bool:
        try:
            path = _plist_path()
            if path.exists():
                path.unlink()
            logger.info("Minion AI macOS autostart successfully disabled.")
            return True
        except FileNotFoundError:
            return True
        except Exception as e:
            logger.error(f"Failed to disable Minion AI autostart: {e}")
            return False
