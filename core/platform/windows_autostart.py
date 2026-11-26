"""Windows login autostart via HKCU Run registry."""

from __future__ import annotations

import logging
import winreg

from core.platform.launch import get_launch_command

logger = logging.getLogger("Minion.Autostart")

REG_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "MinionAI"


class WindowsAutostartBackend:
    """Registers Minion in HKCU\\...\\Run for boot/login start."""

    def is_enabled(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(value)
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.debug(f"Autostart check encountered exception: {e}")
            return False

    def enable(self, minimized: bool = True) -> bool:
        try:
            cmd = get_launch_command(minimized=minimized)
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            logger.info(f"Minion AI autostart successfully enabled: {cmd}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable Minion AI autostart: {e}")
            return False

    def disable(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, APP_NAME)
            logger.info("Minion AI autostart successfully disabled.")
            return True
        except FileNotFoundError:
            return True
        except Exception as e:
            logger.error(f"Failed to disable Minion AI autostart: {e}")
            return False
