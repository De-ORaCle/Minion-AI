"""Windows foreground-window and idle-time backend via user32/kernel32 ctypes."""

from __future__ import annotations

import logging
from typing import Dict, Any

import ctypes
import ctypes.wintypes
import psutil

logger = logging.getLogger(__name__)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.UINT),
        ("dwTime", ctypes.wintypes.DWORD),
    ]


class WindowsWindowBackend:
    """Probes foreground HWND title/PID and GetLastInputInfo idle time."""

    def get_idle_seconds(self) -> float:
        try:
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                return max(0.0, millis / 1000.0)
        except Exception as e:
            logger.debug(f"Error querying idle info: {e}")
        return 0.0

    def get_foreground(self) -> Dict[str, Any]:
        app_name = "Unknown"
        window_title = "Desktop / Idle"
        pid = 0

        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd:
                buf_len = 512
                buf = ctypes.create_unicode_buffer(buf_len)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, buf_len)
                raw_title = buf.value.strip()

                proc_id = ctypes.wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
                pid = proc_id.value

                if raw_title:
                    window_title = raw_title

                if pid > 0:
                    try:
                        proc = psutil.Process(pid)
                        app_name = proc.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        app_name = "System Process"
        except Exception as e:
            logger.debug(f"Error querying foreground window: {e}")

        return {
            "app_name": app_name,
            "window_title": window_title,
            "pid": pid,
            "titles_available": True,
        }
