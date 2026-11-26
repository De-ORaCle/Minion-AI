"""
Build script for Minion AI macOS Disk Image Installer (.dmg).

This script (macOS counterpart to build_installer.py on Windows):
1. Verifies/builds the standalone macOS application bundle in dist/Minion.app.
2. Stages a drag-and-drop installer folder containing Minion.app, an /Applications
   symlink, and a Quick Start README (including Gatekeeper & Screen Recording tips).
3. Uses macOS's built-in `hdiutil` to compile compressed dist/Minion_AI_v1.0_macOS.dmg.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DIST_DIR = PROJECT_DIR / "dist"
APP_BUNDLE = DIST_DIR / "Minion.app"
DMG_STAGING = PROJECT_DIR / "build" / "dmg_staging"
OUTPUT_DMG = DIST_DIR / "Minion_AI_v1.0_macOS.dmg"
VOLUME_NAME = "Minion AI v1.0"


def ensure_macos() -> None:
    """Verify the host is macOS with hdiutil available."""
    if sys.platform != "darwin":
        raise RuntimeError(
            "macOS .dmg packaging requires a macOS host (or GitHub Actions macos-latest runner).\n"
            "Push a git tag (e.g. `git tag v1.0.1 && git push origin v1.0.1`) or trigger the\n"
            "'Build & Publish Releases' workflow on GitHub Actions to build macOS artifacts in the cloud."
        )
    if not shutil.which("hdiutil"):
        raise FileNotFoundError("macOS 'hdiutil' tool was not found on PATH.")


def build_app_if_needed() -> None:
    """Ensure dist/Minion.app is built."""
    print("[*] Checking standalone macOS application bundle...")
    if not APP_BUNDLE.exists():
        build_script = PROJECT_DIR / "build_executable.py"
        print("[*] Compiling standalone Minion.app bundle via PyInstaller...")
        result = subprocess.run([sys.executable, str(build_script)], cwd=str(PROJECT_DIR))
        if result.returncode != 0:
            raise RuntimeError(f"Standalone macOS bundle build failed with code {result.returncode}")

    if not APP_BUNDLE.exists():
        raise FileNotFoundError(f"Expected macOS app bundle not found at: {APP_BUNDLE}")


def prepare_staging() -> None:
    """Stage Minion.app, /Applications symlink, and macOS user instructions."""
    if DMG_STAGING.exists():
        shutil.rmtree(DMG_STAGING)
    DMG_STAGING.mkdir(parents=True, exist_ok=True)

    staged_app = DMG_STAGING / "Minion.app"
    print(f"[*] Staging {APP_BUNDLE.name} into DMG root...")
    if shutil.which("ditto"):
        subprocess.run(["ditto", str(APP_BUNDLE), str(staged_app)], check=True)
    else:
        shutil.copytree(APP_BUNDLE, staged_app, symlinks=True)

    # Create drag-to-install /Applications symlink
    apps_link = DMG_STAGING / "Applications"
    if not apps_link.exists():
        os.symlink("/Applications", apps_link)

    # Write helpful macOS Quick Start & First-Launch instructions
    readme_path = DMG_STAGING / "README — Install & First Launch.txt"
    readme_path.write_text(
        "===================================================\n"
        "     Minion AI — macOS Installation Guide\n"
        "===================================================\n\n"
        "Bello! Welcome to Minion AI for macOS.\n\n"
        "1. INSTALL:\n"
        "   Drag 'Minion.app' onto the 'Applications' folder shortcut in this window.\n\n"
        "2. FIRST LAUNCH (macOS Gatekeeper Notice):\n"
        "   Because Minion AI is open-source and community-distributed, macOS Gatekeeper\n"
        "   may display an 'unidentified developer' or 'damaged/quarantined' prompt on\n"
        "   first launch. To open it cleanly:\n"
        "   • Option A: Right-click (Control-click) Minion.app in /Applications -> click 'Open',\n"
        "     or open System Settings -> Privacy & Security -> scroll down and click 'Open Anyway'.\n"
        "   • Option B (Instant Terminal command):\n"
        "     xattr -cr /Applications/Minion.app\n\n"
        "3. OPTIONAL — ENABLE WINDOW TITLE TRACKING:\n"
        "   Minion tracks active application names and idle time out of the box.\n"
        "   To also capture window and browser tab titles:\n"
        "   • Open System Settings -> Privacy & Security -> Screen & System Audio Recording\n"
        "   • Toggle ON 'Minion', then quit and relaunch Minion.\n"
        "   (100% of data stays in ~/Library/Application Support/MinionAI/data — zero cloud uploads!)\n",
        encoding="utf-8",
    )


def build_dmg() -> None:
    """Create compressed read-only UDZO .dmg image using hdiutil."""
    if OUTPUT_DMG.exists():
        OUTPUT_DMG.unlink()

    print(f"[*] Building compressed macOS Disk Image: {OUTPUT_DMG.name}...")
    cmd = [
        "hdiutil",
        "create",
        "-volname",
        VOLUME_NAME,
        "-srcfolder",
        str(DMG_STAGING),
        "-ov",
        "-format",
        "UDZO",
        str(OUTPUT_DMG),
    ]
    result = subprocess.run(cmd, cwd=str(PROJECT_DIR))
    if result.returncode != 0:
        raise RuntimeError(f"hdiutil failed with return code {result.returncode}")

    if OUTPUT_DMG.exists():
        size_mb = OUTPUT_DMG.stat().st_size / (1024 * 1024)
        print("=" * 65)
        print("[SUCCESS] macOS Disk Image Installer (.dmg) created successfully!")
        print(f"Location: {OUTPUT_DMG}")
        print(f"Size:     {size_mb:.2f} MB")
        print("=" * 65)
    else:
        raise RuntimeError("hdiutil finished but output DMG file was not found.")


def main() -> None:
    print("=" * 65)
    print("[*] Minion AI - Standalone macOS DMG Installer Generator")
    print("=" * 65)
    try:
        ensure_macos()
        build_app_if_needed()
        prepare_staging()
        build_dmg()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
