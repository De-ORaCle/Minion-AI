"""
Minion — On-Screen Productivity Intelligence Application.

Bello! Entry point for the Minion desktop application.
Initializes logging, system directories, single-instance IPC guards,
and launches the CustomTkinter GUI mainloop with background daemon & tray support.

Usage:
    python app.py
    python app.py --minimized   # Launches directly into System Tray without opening window
"""

import sys
import logging
from config import DATA_DIR
from core.single_instance import SingleInstanceManager
from gui.main_window import MainWindow

# Configure global application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Minion")


def main() -> None:
    """Initialize system resources, verify single instance, and launch Minion desktop GUI."""
    logger.info("🍌 Initializing Minion Productivity Intelligence...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Single Instance Guard & IPC Forwarding
    single_mgr = SingleInstanceManager()
    is_primary = single_mgr.acquire()
    if not is_primary:
        # A running instance was found; it has been signaled to restore its window.
        logger.info("Another Minion AI instance is active. Exiting secondary process.")
        sys.exit(0)

    # 2. Check for silent background launch flags (e.g. Windows autostart on boot)
    is_minimized = "--minimized" in sys.argv or "--background" in sys.argv
    if is_minimized:
        logger.info("Starting in silent background tray mode (--minimized)...")

    # 3. Instantiate GUI and assign callback for incoming show requests
    app = MainWindow(single_instance=single_mgr, is_minimized=is_minimized)
    single_mgr.set_on_show_callback(lambda: app.after(0, app.show_window))

    logger.info("Minion GUI initialized. Starting main loop.")
    app.mainloop()


if __name__ == "__main__":
    main()
