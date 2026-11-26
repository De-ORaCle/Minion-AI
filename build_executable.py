"""
Minion AI — Standalone Executable Packaging Engine (PyInstaller).

Builds a 100% self-contained, native desktop application:
- Windows: dist/Minion/Minion.exe + dist/Minion_AI_v1.0_Portable.zip
- macOS:   dist/Minion.app        + dist/Minion_AI_v1.0_macOS_Portable.zip

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
MACOS_BUNDLE_ID = "com.minionai.app"


def _ensure_macos_icns() -> Path:
    """Generate assets/icon.icns from assets/icon.png if needed on macOS."""
    icns_path = BASE_DIR / "assets" / "icon.icns"
    png_path = BASE_DIR / "assets" / "icon.png"
    if icns_path.exists():
        return icns_path
    if not png_path.exists():
        return icns_path

    # Prefer Pillow ICNS writer (works cross-platform)
    try:
        from PIL import Image
        img = Image.open(png_path).convert("RGBA")
        if img.size != (512, 512):
            img = img.resize((512, 512), Image.Resampling.LANCZOS)
        img.save(icns_path, format="ICNS")
        if icns_path.exists():
            print(f"[OK] Generated macOS icon bundle: {icns_path}")
            return icns_path
    except Exception as e:
        print(f"[!] Pillow ICNS generation note: {e}")

    # Fallback to macOS sips + iconutil if running on Darwin
    if sys.platform == "darwin" and shutil.which("sips") and shutil.which("iconutil"):
        iconset_dir = BASE_DIR / "build" / "Minion.iconset"
        iconset_dir.mkdir(parents=True, exist_ok=True)
        sizes = [16, 32, 128, 256, 512]
        try:
            for sz in sizes:
                subprocess.run(
                    ["sips", "-z", str(sz), str(sz), str(png_path), "--out", str(iconset_dir / f"icon_{sz}x{sz}.png")],
                    check=True,
                    capture_output=True,
                )
                sz2 = sz * 2
                subprocess.run(
                    ["sips", "-z", str(sz2), str(sz2), str(png_path), "--out", str(iconset_dir / f"icon_{sz}x{sz}@2x.png")],
                    check=True,
                    capture_output=True,
                )
            subprocess.run(
                ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
                check=True,
                capture_output=True,
            )
            print(f"[OK] Generated macOS icon bundle via iconutil: {icns_path}")
        except Exception as e:
            print(f"[!] iconutil generation warning: {e}")

    return icns_path


def _patch_macos_info_plist(app_bundle: Path) -> None:
    """Enrich Minion.app/Contents/Info.plist with Retina and permission descriptions."""
    plist_path = app_bundle / "Contents" / "Info.plist"
    if not plist_path.exists():
        return
    try:
        import plistlib
        with plist_path.open("rb") as fh:
            info = plistlib.load(fh)
        info["CFBundleDisplayName"] = "Minion AI"
        info["CFBundleName"] = "Minion"
        info["CFBundleShortVersionString"] = "1.0.0"
        info["CFBundleVersion"] = "1.0.0"
        info["NSHighResolutionCapable"] = True
        info["LSMinimumSystemVersion"] = "11.0"
        info["NSScreenCaptureUsageDescription"] = (
            "Minion AI uses Screen Recording permission strictly to read the active window title "
            "locally on your Mac for focus tracking. No screenshots or video are ever recorded or uploaded."
        )
        with plist_path.open("wb") as fh:
            plistlib.dump(info, fh)
        print(f"[OK] Updated macOS bundle metadata: {plist_path}")
    except Exception as e:
        print(f"[!] Warning updating Info.plist: {e}")


def _codesign_macos_bundle(app_bundle: Path) -> None:
    """Apply an ad-hoc code signature so Apple Silicon and Gatekeeper allow local execution."""
    if sys.platform != "darwin" or not shutil.which("codesign"):
        return
    identity = os.environ.get("MACOS_CODESIGN_IDENTITY", "-")
    print(f"[*] Signing {app_bundle.name} (identity: {identity})...")
    result = subprocess.run(
        ["codesign", "--force", "--deep", "--sign", identity, str(app_bundle)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"[OK] Code signature applied to {app_bundle.name}")
    else:
        print(f"[!] codesign warning: {result.stderr.strip()}")


def build_minion_executable() -> bool:
    is_macos = sys.platform == "darwin"
    is_windows = sys.platform == "win32"
    target_label = "macOS .app Bundle" if is_macos else "Windows Native App"

    print("=" * 65)
    print(f"[*] Minion AI - Fusing Python into Standalone {target_label}")
    print("=" * 65)

    # 1. Verify PyInstaller is available
    try:
        import PyInstaller
        print(f"[OK] PyInstaller version {PyInstaller.__version__} detected.")
    except ImportError:
        print("[*] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Clean previous build artifacts
    for d in ["build", "dist"]:
        p = BASE_DIR / d
        if p.exists():
            print(f"[*] Cleaning previous {d} directory...")
            try:
                shutil.rmtree(p)
            except Exception as e:
                print(f"[!] Warning cleaning {d}: {e}")

    # 3. Prepare platform icon & data separator
    data_sep = ";" if is_windows else ":"
    if is_macos:
        icon_path = _ensure_macos_icns()
        if not icon_path.exists():
            icon_path = BASE_DIR / "assets" / "icon.png"
    else:
        icon_path = BASE_DIR / "assets" / "icon.ico"

    # 4. Construct PyInstaller Command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--noupx",                              # Disable UPX decompression lag for instant startup
        "--windowed",                           # No console window (GUI / .app bundle mode)
        "--name=Minion",                        # Output name: Minion.exe or Minion.app
        f"--add-data=assets{data_sep}assets",   # Include custom Work Sans fonts, minion avatars & icon
        "--collect-all=customtkinter",          # Include all CustomTkinter json themes and font assets
        "--collect-all=psutil",                 # Include system telemetry hooks
        "--collect-all=pystray",                # Include system tray daemon engine
        "--hidden-import=pystray",
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

    if is_windows:
        cmd.extend([
            "--hidden-import=pystray._win32",
            "--hidden-import=winreg",
        ])
    elif is_macos:
        cmd.append(f"--osx-bundle-identifier={MACOS_BUNDLE_ID}")

    if icon_path.exists():
        cmd.append(f"--icon={str(icon_path)}")

    # Main application entry point
    cmd.append("app.py")

    print("\n[*] Executing PyInstaller packaging pipeline...")
    print("Command:", " ".join(cmd))
    print("-" * 65)

    result = subprocess.run(cmd, cwd=str(BASE_DIR))

    if result.returncode != 0:
        print(f"\n[ERROR] Build failed with return code: {result.returncode}")
        return False

    if is_macos:
        app_bundle = BASE_DIR / "dist" / "Minion.app"
        if not app_bundle.exists():
            print(f"\n[ERROR] Expected macOS app bundle not found at: {app_bundle}")
            return False

        _patch_macos_info_plist(app_bundle)
        _codesign_macos_bundle(app_bundle)

        # Create macOS Portable ZIP archive preserving symlinks inside .app
        zip_path = BASE_DIR / "dist" / "Minion_AI_v1.0_macOS_Portable.zip"
        print("\n[*] Compressing Minion.app into standalone macOS portable ZIP...")
        if shutil.which("ditto"):
            subprocess.run(
                ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app_bundle), str(zip_path)],
                check=True,
            )
        else:
            shutil.make_archive(
                str(zip_path.with_suffix("")),
                "zip",
                root_dir=str(BASE_DIR / "dist"),
                base_dir="Minion.app",
            )
        print(f"[OK] macOS Portable distribution ready: {zip_path}")

        print("\n" + "=" * 65)
        print("[SUCCESS] Standalone macOS Minion.app has been created!")
        print(f"App Bundle Location: {app_bundle}")
        print(f"Portable Archive:    {zip_path}")
        print("Tip: Run `python build_macos_dmg.py` to package Minion_AI_v1.0_macOS.dmg!")
        print("=" * 65)
        return True

    # Windows post-packaging helpers
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


if __name__ == "__main__":
    success = build_minion_executable()
    sys.exit(0 if success else 1)
