"""
System Tray Manager for Minion AI.

Integrates Minion AI into the Windows System Tray (Taskbar Notification Area)
using pystray. Allows the application to work continuously in the background
even when the window is closed, providing quick-action menus for pausing/resuming
tracking, toggling Windows startup, restoring the window, and exiting.
"""

import threading
import logging
from typing import Callable, Optional
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item, Menu

from config import ICON_PNG_PATH
from core.autostart import is_autostart_enabled, enable_autostart, disable_autostart

logger = logging.getLogger("Minion.Tray")


class TrayManager:
    """Manages the Windows System Tray icon, menu, and background notifications."""

    def __init__(
        self,
        on_show: Callable[[], None],
        on_toggle_tracking: Callable[[bool], None],
        on_quit: Callable[[], None],
        initial_tracking_active: bool = True,
    ):
        """
        Initialize the system tray manager.

        Args:
            on_show: Callback to unminimize and show the main window.
            on_toggle_tracking: Callback receiving (should_track: bool) to pause/resume tracking.
            on_quit: Callback to completely shut down and terminate the application.
            initial_tracking_active: Initial state of activity tracking.
        """
        self.on_show = on_show
        self.on_toggle_tracking = on_toggle_tracking
        self.on_quit = on_quit
        self.is_tracking_active = initial_tracking_active

        self.icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

        self._init_icon()

    def _get_icon_image(self) -> Image.Image:
        """Load the high-resolution Minion PNG icon or generate a fallback icon in memory."""
        if ICON_PNG_PATH.exists():
            try:
                img = Image.open(ICON_PNG_PATH).convert("RGBA")
                # Resize smoothly to 64x64 for tray rasterization
                return img.resize((64, 64), Image.Resampling.LANCZOS)
            except Exception as e:
                logger.debug(f"Could not load ICON_PNG_PATH for tray: {e}")

        # Fallback: Yellow Minion-themed circular badge
        img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((4, 4, 60, 60), fill="#f59e0b", outline="#b45309", width=2)
        # Inner eye / goggle hint
        draw.ellipse((20, 20, 44, 44), fill="#ffffff", outline="#334155", width=2)
        draw.ellipse((28, 28, 36, 36), fill="#1e293b")
        return img

    def _build_menu(self) -> Menu:
        """Generate dynamic context menu for the system tray icon."""
        status_text = "● Tracking: Active" if self.is_tracking_active else "⏸ Tracking: Paused"
        toggle_action_text = "⏸ Pause Tracking" if self.is_tracking_active else "▶ Resume Tracking"

        def _handle_open(icon, _item):
            self.on_show()

        def _handle_toggle(icon, _item):
            new_state = not self.is_tracking_active
            self.on_toggle_tracking(new_state)

        def _handle_autostart(icon, _item):
            if is_autostart_enabled():
                disable_autostart()
            else:
                enable_autostart(minimized=True)
            icon.update_menu()

        def _handle_quit(icon, _item):
            self.stop()
            self.on_quit()

        menu_items = [
            item("🍌 Open Minion AI", _handle_open, default=True),
            Menu.SEPARATOR,
            item(status_text, None, enabled=False),
            item(toggle_action_text, _handle_toggle),
            Menu.SEPARATOR,
            item(
                "⚙️ Start on Windows Boot",
                _handle_autostart,
                checked=lambda _item: is_autostart_enabled(),
            ),
            Menu.SEPARATOR,
            item("❌ Exit Minion Completely", _handle_quit),
        ]
        return Menu(*menu_items)

    def _init_icon(self) -> None:
        """Construct the pystray Icon instance."""
        icon_img = self._get_icon_image()
        self.icon = pystray.Icon(
            name="MinionAI",
            icon=icon_img,
            title="Minion AI — Productivity Intelligence",
            menu=self._build_menu(),
        )

    def start(self) -> None:
        """Launch the system tray icon in a dedicated background daemon thread."""
        if not self.icon:
            self._init_icon()

        def _run_tray():
            try:
                logger.info("Starting Minion system tray icon...")
                self.icon.run()
            except Exception as e:
                logger.debug(f"Tray icon loop exception: {e}")

        self._thread = threading.Thread(target=_run_tray, name="MinionTrayThread", daemon=True)
        self._thread.start()

    def update_tracking_state(self, is_active: bool) -> None:
        """
        Update the tray menu to reflect active or paused monitoring.

        Args:
            is_active: Current tracking status.
        """
        self.is_tracking_active = is_active
        if self.icon:
            try:
                self.icon.menu = self._build_menu()
                self.icon.update_menu()
            except Exception as e:
                logger.debug(f"Failed to update tray menu: {e}")

    def notify(self, title: str, message: str) -> None:
        """
        Display a native Windows notification balloon from the system tray.

        Args:
            title: Notification heading.
            message: Descriptive body text.
        """
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception as e:
                logger.debug(f"Could not dispatch tray notification: {e}")

    def stop(self) -> None:
        """Stop and remove the system tray icon."""
        if self.icon:
            try:
                self.icon.stop()
            except Exception as e:
                logger.debug(f"Error stopping tray icon: {e}")
            self.icon = None
