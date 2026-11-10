"""
Screen & Active Window Monitor for ProductivityCheck.

This module provides real-time tracking of:
1. The currently focused application (executable name).
2. The active window title.
3. User idle detection (seconds elapsed since last keyboard/mouse event).
4. Privacy masking for sensitive/confidential titles.

Architectural Rationale:
- Windows Native APIs (`user32.dll` and `kernel32.dll`) via `ctypes` are chosen because
  they incur practically zero CPU overhead (<0.01%) and require no heavyweight external screen capture drivers.
- Polling runs in a dedicated background `threading.Thread` with cooperative cancellation
  via `threading.Event`, ensuring seamless responsiveness in the GUI.
"""

import sys
import time
import logging
import threading
from typing import Dict, Any, Optional, Callable
import psutil

# Windows CTypes definition for GetLastInputInfo
if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.wintypes.UINT),
            ("dwTime", ctypes.wintypes.DWORD),
        ]

from config import (
    DEFAULT_POLL_INTERVAL,
    DEFAULT_IDLE_THRESHOLD_SECONDS,
    DEFAULT_PRIVACY_EXCLUSIONS,
)
from core.deep_analyzer import DeepSnapshotAnalyzer

logger = logging.getLogger(__name__)


class ScreenMonitor:
    """Monitors foreground window activities and user presence at configurable intervals."""

    def __init__(
        self,
        interval: int = DEFAULT_POLL_INTERVAL,
        idle_threshold: int = DEFAULT_IDLE_THRESHOLD_SECONDS,
        privacy_exclusions: Optional[list] = None,
        on_activity_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize the monitor with customizable interval and callbacks.

        Args:
            interval: Polling frequency in seconds (e.g. 5, 10, 30).
            idle_threshold: Seconds of inactivity before user is deemed 'Idle'.
            privacy_exclusions: List of lowercase substrings to sanitize.
            on_activity_callback: Invoked upon each tick with the activity snapshot dict.
        """
        self.interval = max(1, interval)
        self.idle_threshold = idle_threshold
        self.privacy_exclusions = privacy_exclusions or DEFAULT_PRIVACY_EXCLUSIONS
        self.on_activity_callback = on_activity_callback

        self.deep_analyzer = DeepSnapshotAnalyzer()
        self._prev_snapshot: Optional[Dict[str, Any]] = None

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    def get_idle_time_seconds(self) -> float:
        """
        Query Windows API for milliseconds since the last keyboard or mouse input.
        Returns idle time in seconds.
        """
        if sys.platform != "win32":
            return 0.0

        try:
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                return max(0.0, millis / 1000.0)
        except Exception as e:
            logger.debug(f"Error querying idle info: {e}")

        return 0.0

    def get_active_window_info(self) -> Dict[str, Any]:
        """
        Capture the current foreground window title, process ID, and application name.
        Applies privacy sanitization if matched against exclusion keywords.
        """
        app_name = "Unknown"
        window_title = "Desktop / Idle"
        pid = 0

        if sys.platform == "win32":
            try:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                if hwnd:
                    # Retrieve window title text
                    buf_len = 512
                    buf = ctypes.create_unicode_buffer(buf_len)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, buf_len)
                    raw_title = buf.value.strip()

                    # Retrieve Process ID
                    proc_id = ctypes.wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
                    pid = proc_id.value

                    if raw_title:
                        window_title = raw_title

                    # Resolve executable name via psutil
                    if pid > 0:
                        try:
                            proc = psutil.Process(pid)
                            app_name = proc.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            app_name = "System Process"
            except Exception as e:
                logger.debug(f"Error querying foreground window: {e}")

        # Check Idle status
        idle_seconds = self.get_idle_time_seconds()
        is_idle = idle_seconds >= self.idle_threshold

        # Privacy Sanitization: Mask sensitive window titles
        title_lower = window_title.lower()
        app_lower = app_name.lower()
        for exclusion in self.privacy_exclusions:
            if exclusion in title_lower or exclusion in app_lower:
                window_title = "[Private / Confidential Activity]"
                break

        return {
            "app_name": app_name,
            "window_title": window_title,
            "pid": pid,
            "is_idle": is_idle,
            "idle_seconds": round(idle_seconds, 1),
            "interval_seconds": self.interval,
        }

    def start(self) -> None:
        """Start the background monitoring thread."""
        if self._is_running:
            return

        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Screen monitor started with interval: {self.interval}s")

    def stop(self) -> None:
        """Gracefully stop the background monitoring thread."""
        if not self._is_running:
            return

        self._stop_event.set()
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Screen monitor stopped.")

    def set_interval(self, new_interval: int) -> None:
        """Dynamically update polling frequency without restarting the thread."""
        self.interval = max(1, new_interval)
        logger.info(f"Monitoring interval updated to {self.interval}s")

    def is_running(self) -> bool:
        """Return True if background tracker is actively ticking."""
        return self._is_running

    def _monitor_loop(self) -> None:
        """Main loop executing at the configured interval."""
        while not self._stop_event.is_set():
            start_tick = time.time()

            try:
                raw_snapshot = self.get_active_window_info()
                deep_snapshot = self.deep_analyzer.analyze_and_compare(
                    raw_snapshot, self._prev_snapshot
                )
                self._prev_snapshot = deep_snapshot

                if self.on_activity_callback:
                    self.on_activity_callback(deep_snapshot)
            except Exception as e:
                logger.error(f"Error in monitor tick: {e}", exc_info=True)

            # Sleep remainder of interval, checking stop event every 200ms
            # to remain immediately responsive when the user clicks 'Stop'.
            elapsed = time.time() - start_tick
            sleep_needed = max(0.1, self.interval - elapsed)
            end_sleep = time.time() + sleep_needed

            while time.time() < end_sleep:
                if self._stop_event.is_set():
                    break
                time.sleep(0.2)
