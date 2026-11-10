"""
Single Instance & IPC Communication for Minion AI.

Ensures that only one instance of Minion AI runs on the machine.
If another instance is launched (e.g., user clicks Desktop shortcut or Start Menu),
it connects to the primary instance's local socket, signals it to restore/show its window,
and exits immediately.
"""

import socket
import threading
import logging
import sys
from typing import Callable, Optional

logger = logging.getLogger("Minion.SingleInstance")

DEFAULT_IPC_PORTS = [45454, 45455, 45456]
HOST = "127.0.0.1"


class SingleInstanceManager:
    """Manages single-instance lifecycle via a local loopback socket."""

    def __init__(self, ports=None):
        self.ports = list(ports) if ports else DEFAULT_IPC_PORTS
        self.bound_port: Optional[int] = None
        self.server_socket: Optional[socket.socket] = None
        self.is_primary: bool = False
        self._listener_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self.on_show_callback: Optional[Callable[[], None]] = None

    def set_on_show_callback(self, callback: Callable[[], None]) -> None:
        """Update the callback function to invoke when a secondary launch occurs."""
        self.on_show_callback = callback

    def acquire(self, on_show_callback: Optional[Callable[[], None]] = None) -> bool:
        """
        Attempt to acquire primary instance ownership.

        1. Test existing instances across candidate ports. If an active Minion responds,
           signal it to SHOW and exit secondary process.
        2. If no instance responds, bind exclusively to the candidate port as primary.
        """
        # Step 1: Probe candidate ports for an existing active instance
        for port in self.ports:
            if self._try_signal_running_instance(port):
                logger.info(f"Existing active Minion instance found on port {port}. Signal sent.")
                return False

        # Step 2: No active instance found. Try binding to the first available candidate port
        for port in self.ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                except Exception:
                    pass
            try:
                sock.bind((HOST, port))
                sock.listen(5)
                self.server_socket = sock
                self.bound_port = port
                self.is_primary = True
                self._running = True

                self._listener_thread = threading.Thread(
                    target=self._listen_loop,
                    args=(on_show_callback,),
                    name="MinionIPCListener",
                    daemon=True,
                )
                self._listener_thread.start()
                logger.info(f"Primary instance acquired. IPC listening on {HOST}:{port}")
                return True
            except OSError as e:
                sock.close()
                logger.debug(f"Port {port} unavailable: {e}. Trying next candidate...")

        # If all probe & bind attempts fail, proceed as primary with fallback
        logger.warning("Could not bind exclusive IPC socket on candidate ports. Continuing safely.")
        self.is_primary = True
        return True

    def _try_signal_running_instance(self, port: int) -> bool:
        """Attempt to connect to a candidate port and signal SHOW if Minion is alive."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.settimeout(0.6)
                client.connect((HOST, port))
                client.sendall(b"SHOW\n")
            return True
        except (ConnectionRefusedError, TimeoutError, OSError):
            return False

    def _listen_loop(self, on_show_callback: Optional[Callable[[], None]]) -> None:
        """Background loop accepting IPC commands from subsequent app launches."""
        if not self.server_socket:
            return

        while self._running:
            try:
                conn, _ = self.server_socket.accept()
                with conn:
                    conn.settimeout(1.0)
                    data = conn.recv(1024)
                    if b"SHOW" in data:
                        logger.info("Received SHOW request from secondary launch. Restoring window.")
                        cb = self.on_show_callback or on_show_callback
                        if cb:
                            try:
                                cb()
                            except Exception as cb_err:
                                logger.error(f"Error in on_show_callback: {cb_err}")
            except OSError:
                break
            except Exception as e:
                if self._running:
                    logger.debug(f"IPC listener error: {e}")

    def close(self) -> None:
        """Close the socket and terminate listener."""
        self._running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None

    def release(self) -> None:
        """Alias for close()."""
        self.close()

