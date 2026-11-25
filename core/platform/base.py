"""
Platform backend protocols for window tracking and login autostart.
"""

from typing import Dict, Any, Protocol, runtime_checkable


@runtime_checkable
class WindowBackend(Protocol):
    """OS-specific foreground window and idle-time probing."""

    def get_idle_seconds(self) -> float:
        """Seconds since last keyboard/mouse (HID) input."""
        ...

    def get_foreground(self) -> Dict[str, Any]:
        """
        Return foreground app snapshot keys:
        app_name (str), window_title (str), pid (int).
        """
        ...


@runtime_checkable
class AutostartBackend(Protocol):
    """OS-specific start-at-login registration."""

    def is_enabled(self) -> bool:
        ...

    def enable(self, minimized: bool = True) -> bool:
        ...

    def disable(self) -> bool:
        ...
