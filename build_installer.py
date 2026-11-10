"""
Build script for Minion AI Windows Installer (Setup.exe).

This script:
1. Verifies/updates the standalone bundled executable in dist/Minion.
2. Locates Inno Setup Compiler (ISCC.exe).
3. Compiles installer/Minion_Installer.iss into dist/Minion_Setup_v1.0.exe.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Fix Windows console encoding for UTF-8 logs
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_DIR = Path(__file__).resolve().parent
DIST_DIR = PROJECT_DIR / "dist"
MINION_EXE = DIST_DIR / "Minion" / "Minion.exe"
ISS_FILE = PROJECT_DIR / "installer" / "Minion_Installer.iss"
OUTPUT_SETUP = DIST_DIR / "Minion_Setup_v1.0.exe"

POSSIBLE_ISCC_PATHS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
]


def find_iscc() -> Path:
    """Find the Inno Setup Compiler executable."""
    # Check PATH first
    iscc_path = shutil.which("ISCC.exe") or shutil.which("iscc")
    if iscc_path:
        return Path(iscc_path)

    # Check known filesystem paths
    for path in POSSIBLE_ISCC_PATHS:
        if path.is_file():
            return path

    raise FileNotFoundError(
        "Inno Setup Compiler (ISCC.exe) was not found.\n"
        "Please install Inno Setup via: winget install JRSoftware.InnoSetup"
    )


def build_app_if_needed():
    """Ensure the latest standalone Minion executable is built."""
    print("[*] Checking standalone executable bundle...")
    # Recompile to ensure newest Onboarding wizard is present
    build_script = PROJECT_DIR / "build_executable.py"
    if build_script.exists():
        print("[*] Recompiling latest standalone application bundle...")
        result = subprocess.run([sys.executable, str(build_script)], cwd=PROJECT_DIR)
        if result.returncode != 0:
            raise RuntimeError(f"Standalone executable build failed with code {result.returncode}")

    if not MINION_EXE.exists():
        raise FileNotFoundError(f"Expected executable not found at: {MINION_EXE}")


def build_installer():
    """Compile the Inno Setup installer script."""
    iscc = find_iscc()
    print(f"[OK] Found Inno Setup Compiler: {iscc}")

    if not ISS_FILE.exists():
        raise FileNotFoundError(f"Installer script not found: {ISS_FILE}")

    print(f"[*] Compiling installer script: {ISS_FILE}...")
    cmd = [str(iscc), str(ISS_FILE)]
    result = subprocess.run(cmd, cwd=PROJECT_DIR / "installer")

    if result.returncode != 0:
        raise RuntimeError(f"Inno Setup compilation failed with code {result.returncode}")

    if OUTPUT_SETUP.exists():
        size_mb = OUTPUT_SETUP.stat().st_size / (1024 * 1024)
        print("=" * 65)
        print("[SUCCESS] Windows Setup Installer created successfully!")
        print(f"Location: {OUTPUT_SETUP}")
        print(f"Size: {size_mb:.2f} MB")
        print("=" * 65)
        print("Users can double-click Minion_Setup_v1.0.exe to install Minion AI")
        print("with a desktop icon, start menu shortcut, and an uninstaller.")
        print("=" * 65)
    else:
        print("[WARNING] Build finished but output setup executable was not found.")


def main():
    print("=" * 65)
    print("[*] Minion AI - Standalone Windows Setup Installer Generator")
    print("=" * 65)
    try:
        build_app_if_needed()
        build_installer()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
