"""
Windows Autostart Integration for Minion AI.

Provides utilities to register Minion AI in the Windows Current User Run Registry
(HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run) so that it starts automatically
upon system boot/restart in background tray mode (--minimized).
"""

import sys
import winreg
import logging
from pathlib import Path

logger = logging.getLogger("Minion.Autostart")

REG_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "MinionAI"


def get_launch_command(minimized: bool = True) -> str:
    """
    Construct the command line to launch Minion AI on Windows boot.

    If frozen (PyInstaller executable bundle), uses Minion.exe directly.
    Otherwise (development environment), uses the active Python interpreter and app.py.
    """
    flag = " --minimized" if minimized else ""
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable).resolve()
        return f'"{exe_path}"{flag}'
    else:
        python_exe = Path(sys.executable).resolve()
        app_script = Path(__file__).resolve().parent.parent / "app.py"
        return f'"{python_exe}" "{app_script}"{flag}'


def is_autostart_enabled() -> bool:
    """
    Check whether Minion AI is currently registered to run on Windows startup.

    Returns:
        bool: True if registry entry exists and has a value, False otherwise.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.debug(f"Autostart check encountered exception: {e}")
        return False


def enable_autostart(minimized: bool = True) -> bool:
    """
    Register Minion AI in HKCU Run registry to start automatically on boot.

    Args:
        minimized: If True, app starts silently in the system tray without opening the window.

    Returns:
        bool: True if registry was updated successfully, False otherwise.
    """
    try:
        cmd = get_launch_command(minimized=minimized)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        logger.info(f"Minion AI autostart successfully enabled: {cmd}")
        return True
    except Exception as e:
        logger.error(f"Failed to enable Minion AI autostart: {e}")
        return False


def disable_autostart() -> bool:
    """
    Remove Minion AI from HKCU Run registry so it no longer starts on boot.

    Returns:
        bool: True if removed or already absent, False on unexpected error.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        logger.info("Minion AI autostart successfully disabled.")
        return True
    except FileNotFoundError:
        return True  # Already not registered
    except Exception as e:
        logger.error(f"Failed to disable Minion AI autostart: {e}")
        return False
