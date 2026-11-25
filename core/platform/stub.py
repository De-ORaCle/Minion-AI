"""Safe no-op backends for unsupported platforms."""

from typing import Dict, Any


class StubWindowBackend:
    """Returns placeholder foreground info and zero idle time."""

    def get_idle_seconds(self) -> float:
        return 0.0

    def get_foreground(self) -> Dict[str, Any]:
        return {
            "app_name": "Unknown",
            "window_title": "Desktop / Idle",
            "pid": 0,
            "titles_available": False,
        }


class StubAutostartBackend:
    """Autostart is unsupported; all operations are no-ops."""

    def is_enabled(self) -> bool:
        return False

    def enable(self, minimized: bool = True) -> bool:
        return False

    def disable(self) -> bool:
        return True
