"""
Minion AI — Standalone Executable Packaging Engine (PyInstaller).

Builds a 100% self-contained, native Windows desktop executable (Minion.exe)
with Python runtime, CustomTkinter themes, typography, and assets completely fused inside.
End-users do NOT need Python installed on their machine to run Minion!
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

# Force UTF-8 for console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

def build_minion_executable():
    print("=" * 65)
    print("[*] Minion AI - Fusing Python into Standalone Native Windows App")
    print("=" * 65)

    # 1. Verify PyInstaller is available
    try:
        import PyInstaller
        print(f"[OK] PyInstaller version {PyInstaller.__version__} detected.")
    except ImportError:
        print("[*] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Prepare paths and icon
    icon_path = BASE_DIR / "assets" / "icon.ico"

    # Clean previous build artifacts
    for d in ["build", "dist"]:
        p = BASE_DIR / d
        if p.exists():
            print(f"[*] Cleaning previous {d} directory...")
            try:
                shutil.rmtree(p)
            except Exception as e:
                print(f"[!] Warning cleaning {d}: {e}")

    # 3. Construct PyInstaller Command
    # We bundle the entire assets directory and collect all customtkinter resources
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--noupx",                    # Disable UPX decompression lag for blazing-fast instant startup
        "--windowed",                 # No black console window (GUI mode)
        "--name=Minion",              # Output name: Minion.exe
        "--add-data=assets;assets",   # Include custom Work Sans fonts, minion avatars & icon
        "--collect-all=customtkinter",# Include all CustomTkinter json themes and font assets
        "--collect-all=psutil",       # Include system telemetry hooks
        "--collect-all=pystray",      # Include system tray daemon engine
        "--hidden-import=pystray",
        "--hidden-import=pystray._win32",
        "--hidden-import=winreg",
        "--hidden-import=PIL",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=requests",
        "--hidden-import=packaging",
        "--hidden-import=sqlite3",
        "--hidden-import=ctypes",
        # Strip heavy unused transitives to maximize cold-start speed and minimize RAM footprint
        "--exclude-module=scipy",
        "--exclude-module=pandas",
        "--exclude-module=pyarrow",
        "--exclude-module=pytest",
        "--exclude-module=IPython",
        "--exclude-module=tornado",
        "--exclude-module=pygments",
        "--exclude-module=zmq",
    ]

    if icon_path.exists():
        cmd.append(f"--icon={str(icon_path)}")

    # Main application entry point
    cmd.append("app.py")

    print("\n[*] Executing PyInstaller packaging pipeline...")
    print("Command:", " ".join(cmd))
    print("-" * 65)

    result = subprocess.run(cmd, cwd=str(BASE_DIR))

    if result.returncode == 0:
        dist_dir = BASE_DIR / "dist" / "Minion"
        exe_path = dist_dir / "Minion.exe"

        # 1. Create Launch_Minion.vbs (100% silent launcher with zero black console window)
        vbs_path = dist_dir / "Launch_Minion.vbs"
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(
                'Set WshShell = CreateObject("WScript.Shell")\n'
                'WshShell.Run chr(34) & Replace(WScript.ScriptFullName, WScript.ScriptName, "") & "Minion.exe" & chr(34), 0\n'
                'Set WshShell = Nothing\n'
            )

        # 2. Create README_PORTABLE.txt helper
        readme_path = dist_dir / "README_PORTABLE.txt"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(
                "===================================================\n"
                "       Minion AI — Productivity Intelligence\n"
                "===================================================\n\n"
                "Bello! This is the portable standalone edition of Minion AI.\n"
                "No installation and no Python runtime required.\n\n"
                "HOW TO RUN:\n"
                '1. Double-click "Minion.exe" directly (or "Launch_Minion.vbs").\n'
                "2. The dashboard will launch immediately with zero command prompt windows.\n"
                "3. When you close the window, Minion stays active in your System Tray (taskbar corner).\n\n"
                "HOW TO UNINSTALL / DELETE:\n"
                '1. Right-click the Minion icon in your taskbar System Tray -> "Exit Minion Completely".\n'
                "2. (Optional) In Task Manager -> Startup apps, disable Minion if Windows autostart was enabled.\n"
                "3. Delete this extracted Minion folder. That's it! Everything is self-contained.\n\n"
                "NOTE FOR WINDOWS 11 USERS:\n"
                "If you downloaded this ZIP from the web or Google Drive:\n"
                '- Right-click "Minion_AI_v1.0_Portable.zip" -> Properties -> check "Unblock" -> click OK.\n'
                "- Then extract and run!\n"
            )

        # 3. Create standalone Portable ZIP archive
        zip_base = BASE_DIR / "dist" / "Minion_AI_v1.0_Portable"
        print("\n[*] Compressing into standalone portable ZIP distribution...")
        shutil.make_archive(str(zip_base), "zip", root_dir=str(BASE_DIR / "dist"), base_dir="Minion")
        print(f"[OK] Portable distribution ready: {zip_base}.zip")

        print("\n" + "=" * 65)
        print("[SUCCESS] Standalone Minion AI has been created!")
        print(f"Executable Location: {exe_path}")
        print(f"Portable Archive:    {zip_base}.zip")
        print("This folder is 100% portable: Python is fused inside.")
        print("Any user can now run Minion without having Python installed.")
        print("=" * 65)
        return True
    else:
        print(f"\n[ERROR] Build failed with return code: {result.returncode}")
        return False

if __name__ == "__main__":
    success = build_minion_executable()
    sys.exit(0 if success else 1)
