"""
Platform adapter tests for Minion AI.

Verifies that autostart imports safely on non-Windows hosts, factory
backends resolve for the current OS, and window snapshots expose the
required keys.
"""

import sys
import unittest


class TestPlatformAdapters(unittest.TestCase):
    def test_autostart_import_safe(self):
        """core.autostart must import without winreg on non-Windows."""
        import core.autostart as autostart

        self.assertTrue(callable(autostart.is_autostart_enabled))
        self.assertTrue(callable(autostart.enable_autostart))
        self.assertTrue(callable(autostart.disable_autostart))
        # Must not raise
        enabled = autostart.is_autostart_enabled()
        self.assertIsInstance(enabled, bool)

    def test_factory_returns_backends(self):
        from core.platform import get_window_backend, get_autostart_backend
        from core.platform.base import WindowBackend, AutostartBackend

        window = get_window_backend()
        autostart = get_autostart_backend()

        self.assertIsInstance(window, WindowBackend)
        self.assertIsInstance(autostart, AutostartBackend)

        if sys.platform == "darwin":
            from core.platform.macos_window import MacOSWindowBackend
            from core.platform.macos_autostart import MacOSAutostartBackend

            self.assertIsInstance(window, MacOSWindowBackend)
            self.assertIsInstance(autostart, MacOSAutostartBackend)
        elif sys.platform == "win32":
            from core.platform.windows_window import WindowsWindowBackend
            from core.platform.windows_autostart import WindowsAutostartBackend

            self.assertIsInstance(window, WindowsWindowBackend)
            self.assertIsInstance(autostart, WindowsAutostartBackend)

    def test_window_backend_snapshot_shape(self):
        from core.platform import get_window_backend

        snapshot = get_window_backend().get_foreground()
        self.assertIn("app_name", snapshot)
        self.assertIn("window_title", snapshot)
        self.assertIn("pid", snapshot)
        self.assertIsInstance(snapshot["app_name"], str)
        self.assertIsInstance(snapshot["window_title"], str)
        self.assertIsInstance(snapshot["pid"], int)

        idle = get_window_backend().get_idle_seconds()
        self.assertIsInstance(idle, float)
        self.assertGreaterEqual(idle, 0.0)

    def test_launch_helpers(self):
        from core.platform.launch import get_launch_command, get_launch_parts

        parts = get_launch_parts(minimized=True)
        self.assertGreaterEqual(len(parts), 2)
        self.assertIn("--minimized", parts)

        cmd = get_launch_command(minimized=True)
        self.assertIn("--minimized", cmd)
        self.assertIn("app.py", cmd)


if __name__ == "__main__":
    unittest.main()
