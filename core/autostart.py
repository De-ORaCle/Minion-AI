"""
Login Autostart Integration for Minion AI.

Public API delegates to a platform backend:
- Windows: HKCU Run registry
- macOS: ~/Library/LaunchAgents plist
- Other: stub (unsupported)
"""

from core.platform import get_autostart_backend
from core.platform.launch import get_launch_command  # noqa: F401 — re-exported


def is_autostart_enabled() -> bool:
    """
    Check whether Minion AI is registered to run on login/boot.

    Returns:
        bool: True if an autostart entry exists, False otherwise.
    """
    return get_autostart_backend().is_enabled()


def enable_autostart(minimized: bool = True) -> bool:
    """
    Register Minion AI to start automatically on login/boot.

    Args:
        minimized: If True, app starts silently in the system tray without opening the window.

    Returns:
        bool: True if registration succeeded, False otherwise.
    """
    return get_autostart_backend().enable(minimized=minimized)


def disable_autostart() -> bool:
    """
    Remove Minion AI from login/boot autostart.

    Returns:
        bool: True if removed or already absent, False on unexpected error.
    """
    return get_autostart_backend().disable()
