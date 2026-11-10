"""
PC & Environment Telemetry Detector for Minion.

This module safely inspects the host hardware, operating system, display dimensions,
and environment specs to give Minion complete hardware context about the user's PC.
"""

import sys
import os
import platform
import psutil
from typing import Dict, Any


def get_system_telemetry() -> Dict[str, str]:
    """Gather non-invasive PC hardware and environment specifications."""
    # 1. Hostname and User
    try:
        user_name = os.getlogin()
    except Exception:
        user_name = os.environ.get("USERNAME", "User")
    hostname = platform.node() or "Unknown Host"

    # 2. Operating System
    os_info = f"{platform.system()} {platform.release()} (Build {platform.version()})"

    # 3. CPU Specs
    try:
        logical_cores = psutil.cpu_count(logical=True)
        physical_cores = psutil.cpu_count(logical=False)
        cpu_name = platform.processor() or "Multi-Core CPU"
        if "Family" in cpu_name and "Model" in cpu_name:
            brand = "Intel" if "Intel" in cpu_name else ("AMD" if "AMD" in cpu_name else "x86_64")
            cpu_name = f"{brand} Core Processor"
        cpu_info = f"{cpu_name} • {physical_cores or logical_cores} physical / {logical_cores} logical cores"
    except Exception:
        cpu_info = f"{platform.processor()} ({os.cpu_count()} Cores)"

    # 4. RAM
    try:
        total_ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        avail_ram_gb = round(psutil.virtual_memory().available / (1024 ** 3), 1)
        ram_info = f"{total_ram_gb} GB Total ({avail_ram_gb} GB Available)"
    except Exception:
        ram_info = "Memory info unavailable"

    # 5. Display Resolution (Windows Native)
    display_info = "Default Display"
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
            display_info = f"{width}x{height} Primary Display"
        except Exception:
            display_info = "Display resolution detection unavailable"

    # 6. Python Runtime
    if getattr(sys, "frozen", False):
        python_env = f"Embedded Python {sys.version.split()[0]} (Fused Standalone)"
    else:
        python_env = f"Python {sys.version.split()[0]} ({platform.python_implementation()})"

    return {
        "hostname": f"{hostname} ({user_name})",
        "os_info": os_info,
        "cpu_info": cpu_info,
        "ram_info": ram_info,
        "display_info": display_info,
        "python_env": python_env,
    }


def detect_and_save_pc_context(db_manager) -> Dict[str, str]:
    """Detect current system telemetry and save to the database."""
    specs = get_system_telemetry()
    db_manager.save_pc_context(specs)
    return specs
