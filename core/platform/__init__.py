"""
Platform backend factory for window tracking and login autostart.

Selects Windows, macOS, or stub implementations based on sys.platform.
"""

from __future__ import annotations

import sys
from typing import Optional

from core.platform.base import WindowBackend, AutostartBackend
from core.platform.stub import StubWindowBackend, StubAutostartBackend

_window_backend: Optional[WindowBackend] = None
_autostart_backend: Optional[AutostartBackend] = None


def get_window_backend() -> WindowBackend:
    """Return a process-wide window/idle backend for the current OS."""
    global _window_backend
    if _window_backend is not None:
        return _window_backend

    if sys.platform == "win32":
        from core.platform.windows_window import WindowsWindowBackend

        _window_backend = WindowsWindowBackend()
    elif sys.platform == "darwin":
        from core.platform.macos_window import MacOSWindowBackend

        _window_backend = MacOSWindowBackend()
    else:
        _window_backend = StubWindowBackend()
    return _window_backend


def get_autostart_backend() -> AutostartBackend:
    """Return a process-wide login-autostart backend for the current OS."""
    global _autostart_backend
    if _autostart_backend is not None:
        return _autostart_backend

    if sys.platform == "win32":
        from core.platform.windows_autostart import WindowsAutostartBackend

        _autostart_backend = WindowsAutostartBackend()
    elif sys.platform == "darwin":
        from core.platform.macos_autostart import MacOSAutostartBackend

        _autostart_backend = MacOSAutostartBackend()
    else:
        _autostart_backend = StubAutostartBackend()
    return _autostart_backend


__all__ = [
    "WindowBackend",
    "AutostartBackend",
    "get_window_backend",
    "get_autostart_backend",
]
