# 🚀 Minion AI — Deployment & Release Guide

> **Official Repository**: [https://github.com/De-ORaCle/Minion-AI](https://github.com/De-ORaCle/Minion-AI)  
> **Maintainer & Author**: [@De-ORaCle](https://github.com/De-ORaCle)

This guide provides structured instructions for maintaining, building, and deploying **Minion AI** for both technical developers and non-technical end users.

---

## 👤 Maintainer Git Identity & Email Privacy

To protect your personal email from web-scraping spam bots, GitHub provides a private `users.noreply.github.com` email address for public commits. You can configure Git locally using either your GitHub username or privacy email:

```powershell
git config user.name "De-ORaCle"
git config user.email "De-ORaCle@users.noreply.github.com"
```

Or with your name:
```powershell
git config user.name "Bukola Olapade"
git config user.email "De-ORaCle@users.noreply.github.com"
```

Verify your configuration:

```powershell
git config user.name
git config user.email
```

---

## 📦 Distribution Packages Overview

Minion AI is distributed across Windows and macOS in the following formats:

| Format | Target Audience | Python Required? | Installation Process |
| :--- | :--- | :--- | :--- |
| **Windows Setup Installer** (`Minion_Setup_v1.0.exe`) | Everyday Windows users | ❌ No | Standard Windows Wizard (Desktop icon, Start Menu, System Tray autostart, uninstaller) |
| **Windows Portable ZIP** (`Minion_AI_v1.0_Portable.zip`) | Portable / USB / Non-admin Windows users | ❌ No | Unzip and double-click `Minion.exe` or `Launch_Minion.vbs` |
| **macOS Disk Image** (`Minion_AI_v1.0_macOS.dmg`) | Everyday macOS users | ❌ No | Open `.dmg` and drag `Minion.app` into `/Applications` |
| **macOS Portable ZIP** (`Minion_AI_v1.0_macOS_Portable.zip`) | Portable macOS users | ❌ No | Unzip and launch `Minion.app` |
| **Python Source Repository** | Developers, contributors, researchers | ✔ Yes (3.10+) | `git clone` + `pip install -r requirements.txt` |

---

## 🛠️ Building Standalone Binaries (For Releases)

### 1. Build Standalone Application & Portable Bundle (Windows or macOS)

This compiles Python, CustomTkinter, system hooks, and the mascot assets into a self-contained app bundle and automatically compresses it into a `.zip` archive:

```powershell
python build_executable.py
```
*Or on Windows, double-click:* `Build_Standalone_Minion.bat`

**Outputs on Windows:**
- `dist/Minion/` (Self-contained application folder with `Minion.exe`)
- `dist/Minion_AI_v1.0_Portable.zip` (Ready for GitHub Release upload)

**Outputs on macOS:**
- `dist/Minion.app` (Self-contained ad-hoc signed macOS application bundle)
- `dist/Minion_AI_v1.0_macOS_Portable.zip` (Ready for GitHub Release upload)

> [!NOTE]
> UPX compression is intentionally disabled (`--noupx`) to eliminate cold-decompression lag on user workstations and prevent false-positive antivirus warnings.

### 2. Build Windows Setup Installer (`.exe`)

This compiles an Inno Setup installer that gives users a guided installation wizard, Start Menu folder, desktop shortcut, optional autostart on boot, and a clean Windows uninstaller:

**Prerequisite:** Ensure Inno Setup 6 is installed on the build machine:
```powershell
winget install JRSoftware.InnoSetup
```

**Compile Installer:**
```powershell
python build_installer.py
```
*Or double-click:* `Build_Setup_Installer.bat`

**Output:**
- `dist/Minion_Setup_v1.0.exe` (Upload to GitHub Releases)

### 3. Build macOS Disk Image Installer (`.dmg`)

On a macOS host (or automatically via the GitHub Actions release workflow), compile the drag-and-drop `.dmg` installer containing `Minion.app`, an `/Applications` shortcut, and first-launch instructions:

```bash
python build_macos_dmg.py
```

**Output:**
- `dist/Minion_AI_v1.0_macOS.dmg` (Upload to GitHub Releases)

---

## 🌐 Publishing a Release on GitHub (Automated via GitHub Actions)

The repository includes `.github/workflows/release.yml`, which automatically builds both **macOS** (`.dmg` + `.zip` on `macos-latest`) and **Windows** (`.exe` + `.zip` on `windows-latest`) binaries and attaches all four artifacts directly to the GitHub Release!

### Option A: Push a Version Tag (Automatic Build & Release)
```powershell
git tag -a v1.0.1 -m "Release v1.0.1 — Windows & macOS Rollout"
git push origin v1.0.1
```
GitHub Actions will immediately spin up macOS and Windows runners, run the platform tests, compile the installers, and create/update the GitHub Release with:
- `Minion_Setup_v1.0.exe`
- `Minion_AI_v1.0_Portable.zip`
- `Minion_AI_v1.0_macOS.dmg`
- `Minion_AI_v1.0_macOS_Portable.zip`

### Option B: Attach macOS Builds to an Existing Release Tag (Manual Trigger)
1. Go to **GitHub -> Actions -> Build & Publish Releases (macOS & Windows)**.
2. Click **Run workflow**.
3. Enter your existing tag (e.g., `v1.0.0`) in the `tag_name` input (or leave blank to simply download the built `.dmg` and `.zip` from the workflow summary).

3. **Release Description Template**:
   ```markdown
   ## 🍌 What's New in v1.0.0
   - **Minion Lounge**: AI focus assistant with animated mascot crew (Kevin, Stuart, Bob).
   - **Work Insights & Memory**: Multi-project recognition, tech stack radar, and goal alignment.
   - **Activity Watcher**: Sub-second active window tracking with zero cloud leakage.
   - **Sprints & Analytics**: Chronological milestones and flow state velocity scoring.
   - **Standup & Share Generator**: Instant LinkedIn, X, and daily standup formatting.

   ### 📥 Downloads
   - **Windows Installer**: Download `Minion_Setup_v1.0.exe` and follow the setup wizard.
   - **Portable Version**: Download `Minion_AI_v1.0_Portable.zip`, extract, and launch `Minion.exe`.
   ```

---

## 🧪 Quality Assurance & Test Verification

Before pushing any commit or release tag, always run the automated test suite:

```powershell
python -m unittest tests/test_core.py
```

All 12 unit and integration tests must pass cleanly:
- Database schema and WAL concurrency
- Multi-tier categorization heuristics and custom rules
- Context segmentation and work sprint clustering
- Matplotlib report rendering and summary metrics
- Privacy exclusions and data anonymization
- Deep snapshot delta analysis and stuck loop detection

---

## 🔒 Security & Privacy Checklist

Minion is designed with a strict **Privacy-First, Local-First** guarantee:
1. **Never commit personal telemetry**: `data/*.db` and SQLite database files are excluded via `.gitignore`.
2. **Never expose API keys or cloud secrets**: Minion uses offline local LLMs via Ollama; no remote tokens or API keys are required.
3. **Sensitive Data Masking**: Windows titles matching password managers (`Bitwarden`, `1Password`), banking portals, and private browsing sessions are sanitized automatically before hitting the database.

