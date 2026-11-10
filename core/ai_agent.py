"""
Ollama Local AI Agent Integration for Minion AI.

This module provides direct integration with local offline Large Language Models (LLMs)
via Ollama's REST API (running on localhost:11434).

Architectural Rationale:
- Privacy-First: Screen titles and productivity logs NEVER leave the local workstation.
- Sovereign Offline AI: Enables semantic classification of ambiguous activities,
  context summarization, and automated generation of social updates (LinkedIn, Twitter/X, Standups).
- Graceful Degradation: If Ollama is offline or no model is downloaded yet,
  the agent falls back to smart deterministic templates without breaking any user workflows.
"""

import os
import sys
import re
import json
import time
import shutil
import logging
import subprocess
import urllib.request
from typing import List, Dict, Any, Optional, Tuple, Callable
import requests
from packaging.version import Version, InvalidVersion

from config import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_MODEL,
    CATEGORY_CONFIG,
)
from core.project_intelligence import (
    detect_active_local_server,
    detect_active_deliverable,
    generate_strategic_project_angles,
    generate_tool_optimizations,
    open_local_server,
)

logger = logging.getLogger(__name__)

# Minimum recommended Ollama version for Llama 3.2, structured JSON & tool streaming
MIN_OLLAMA_VERSION = "0.3.0"


class OllamaAgent:
    """Manages communication with local Ollama service and executes prompt pipelines."""

    def __init__(self, host: str = DEFAULT_OLLAMA_HOST, model: str = DEFAULT_OLLAMA_MODEL):
        """
        Initialize the Ollama agent.

        Args:
            host: Ollama server endpoint (default: http://127.0.0.1:11434).
            model: Target local model name (e.g., 'llama3.2:3b').
        """
        self.host = host.rstrip("/")
        self.model = model
        self.session = requests.Session()

    def find_ollama_executable(self) -> Optional[str]:
        """Locate the ollama CLI or desktop executable on the current system."""
        # Check standard PATH
        exe = shutil.which("ollama")
        if exe and os.path.exists(exe):
            return exe

        # Windows-specific standard user and system install directories
        if sys.platform == "win32":
            candidates = [
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
                os.path.join(os.environ.get("PROGRAMFILES", ""), "Ollama", "ollama.exe"),
                os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Ollama", "ollama.exe"),
                os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Programs", "Ollama", "ollama.exe"),
            ]
            for cand in candidates:
                if cand and os.path.exists(cand):
                    return cand

        # Linux / macOS standard paths
        for cand in ["/usr/local/bin/ollama", "/usr/bin/ollama", "/opt/homebrew/bin/ollama"]:
            if os.path.exists(cand):
                return cand

        return None

    def get_installed_version(self) -> Optional[str]:
        """Query the locally installed Ollama executable version via CLI."""
        if hasattr(self, "_cached_installed_ver") and self._cached_installed_ver:
            return self._cached_installed_ver

        exe = self.find_ollama_executable()
        if not exe:
            return None
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0
            out = subprocess.check_output(
                [exe, "--version"],
                text=True,
                stderr=subprocess.STDOUT,
                timeout=3.0,
                creationflags=creationflags,
            )
            m = re.search(r"(\d+\.\d+\.\d+)", out)
            ver = m.group(1) if m else "unknown"
            self._cached_installed_ver = ver
            return ver
        except Exception as e:
            logger.debug(f"Could not parse ollama --version: {e}")
            return "unknown"

    def get_service_version(self) -> Optional[str]:
        """Query the running Ollama REST daemon version via /api/version."""
        try:
            resp = self.session.get(f"{self.host}/api/version", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("version", "unknown")
        except Exception:
            pass
        return None

    def is_service_running(self) -> bool:
        """Return True if the Ollama HTTP REST endpoint is actively responding."""
        try:
            resp = self.session.get(f"{self.host}/api/tags", timeout=1.5)
            return resp.status_code == 200
        except Exception:
            return False

    def is_version_satisfactory(self, ver_str: Optional[str]) -> bool:
        """Check if a version string satisfies the minimum required Ollama version."""
        if not ver_str or ver_str == "unknown":
            return True  # If installed but version is unparseable, don't block
        try:
            return Version(ver_str) >= Version(MIN_OLLAMA_VERSION)
        except InvalidVersion:
            return True

    def start_service(self, timeout: float = 8.0) -> bool:
        """
        Start the Ollama daemon service in the background if not already active.

        Uses DETACHED_PROCESS and CREATE_NO_WINDOW on Windows so no black command prompt appears.
        """
        if self.is_service_running():
            return True

        exe = self.find_ollama_executable()
        if not exe:
            logger.warning("Cannot start Ollama: executable not found.")
            return False

        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

            logger.info(f"Launching Ollama daemon via: {exe} serve")
            subprocess.Popen(
                [exe, "serve"],
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )

            # Poll endpoint until ready
            start_t = time.time()
            while time.time() - start_t < timeout:
                if self.is_service_running():
                    logger.info("Ollama background service successfully started.")
                    return True
                time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error launching Ollama service: {e}")

        return self.is_service_running()

    def ensure_service_running(self, timeout: float = 8.0) -> bool:
        """Convenience method to ensure service is alive, starting it if offline."""
        if self.is_service_running():
            return True
        return self.start_service(timeout=timeout)

    def install_or_update_ollama(
        self, progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Tuple[bool, str]:
        """
        Install or upgrade Ollama with 1-click on Windows.
        Tries winget first; falls back to direct official installer download.
        """
        if progress_callback:
            progress_callback("Checking package manager...", 0.1)

        # 1. Try winget on Windows
        winget_exe = shutil.which("winget")
        if winget_exe:
            if progress_callback:
                progress_callback("Running winget install for Ollama...", 0.25)
            try:
                cmd = [
                    winget_exe,
                    "install",
                    "Ollama.Ollama",
                    "--accept-source-agreements",
                    "--accept-package-agreements",
                    "--silent",
                ]
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240, creationflags=creationflags)
                if proc.returncode == 0:
                    if progress_callback:
                        progress_callback("Ollama installed successfully!", 0.9)
                    time.sleep(2.0)
                    return True, "Ollama successfully installed via winget."
                else:
                    logger.warning(f"Winget install returned non-zero ({proc.returncode}): {proc.stderr}")
            except Exception as e:
                logger.warning(f"Winget install execution error: {e}")

        # 2. Fallback: Download official installer
        if progress_callback:
            progress_callback("Downloading official Ollama installer...", 0.3)

        try:
            setup_url = "https://ollama.com/download/OllamaSetup.exe"
            temp_dir = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "minion_ollama")
            os.makedirs(temp_dir, exist_ok=True)
            installer_path = os.path.join(temp_dir, "OllamaSetup.exe")

            def _reporthook(block_num, block_size, total_size):
                if total_size > 0 and progress_callback:
                    downloaded = block_num * block_size
                    pct = min(0.75, 0.3 + (0.45 * (downloaded / total_size)))
                    mb_cur = downloaded / (1024 * 1024)
                    mb_tot = total_size / (1024 * 1024)
                    progress_callback(f"Downloading installer: {mb_cur:.1f}MB / {mb_tot:.1f}MB", pct)

            urllib.request.urlretrieve(setup_url, installer_path, reporthook=_reporthook)

            if progress_callback:
                progress_callback("Launching Ollama Setup...", 0.8)

            # Run setup silently without console window
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0
            subprocess.run([installer_path, "/silent"], check=False, timeout=180, creationflags=creationflags)

            # Poll for executable up to 30 seconds
            for _ in range(15):
                if self.find_ollama_executable():
                    if progress_callback:
                        progress_callback("Ollama installed successfully!", 0.95)
                    return True, "Ollama installed successfully."
                time.sleep(2.0)

            return True, "Ollama installer finished."
        except Exception as e:
            return False, f"Failed to install Ollama: {str(e)}"

    def pull_model_stream(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Pull a model via the Ollama streaming REST API, reporting live percentages.
        """
        if not self.is_service_running():
            started = self.start_service(timeout=6.0)
            if not started:
                return False, "Ollama daemon is not running."

        try:
            if progress_callback:
                progress_callback(f"Requesting pull for {model_name}...", 0.05)

            url = f"{self.host}/api/pull"
            resp = self.session.post(
                url,
                json={"name": model_name, "stream": True},
                stream=True,
                timeout=1800,
            )

            if resp.status_code != 200:
                return False, f"Ollama returned HTTP error {resp.status_code}"

            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line.decode("utf-8"))
                    status_str = chunk.get("status", "")
                    total = chunk.get("total", 0)
                    completed = chunk.get("completed", 0)

                    if total > 0:
                        pct = min(1.0, completed / total)
                        mb_done = completed / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        msg = f"{status_str}: {mb_done:.1f}MB / {mb_total:.1f}MB ({int(pct*100)}%)"
                        if progress_callback:
                            progress_callback(msg, pct)
                    else:
                        if progress_callback:
                            progress_callback(status_str, 0.5)

                    if status_str == "success":
                        if progress_callback:
                            progress_callback(f"✓ Model {model_name} downloaded successfully!", 1.0)
                        return True, f"Model {model_name} successfully downloaded."
                except Exception:
                    pass

            return True, f"Model {model_name} pulled."
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False, str(e)

    def one_click_setup(
        self,
        target_model: str = DEFAULT_OLLAMA_MODEL,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Tuple[bool, str]:
        """
        End-to-end 1-click setup:
        1. Installs or upgrades Ollama if missing/outdated.
        2. Starts the background service if stopped.
        3. Downloads the recommended brain model with live streaming progress.
        4. Configures Minion to use the model.
        """
        status = self.get_detailed_status()

        # Step 1: Install or upgrade if needed
        if not status["installed"] or not status["version_ok"]:
            if progress_callback:
                progress_callback("Installing / Updating Ollama engine...", 0.1)
            ok, msg = self.install_or_update_ollama(progress_callback=progress_callback)
            if not ok:
                return False, f"Ollama installation failed: {msg}"

        # Step 2: Ensure background service is running
        if not self.is_service_running():
            if progress_callback:
                progress_callback("Starting Ollama background daemon on localhost:11434...", 0.3)
            started = self.start_service(timeout=10.0)
            if not started:
                return False, "Failed to start Ollama background service."

        # Step 3: Check if model is downloaded; if not, stream pull
        status = self.get_detailed_status()
        model_names = [m.split(":")[0] for m in status["models"]] + status["models"]
        target_base = target_model.split(":")[0]

        if target_model not in status["models"] and target_base not in model_names:
            if progress_callback:
                progress_callback(f"Downloading brain model ({target_model})...", 0.35)

            def _scaled_cb(text: str, pct: float):
                scaled = 0.35 + (pct * 0.6)
                if progress_callback:
                    progress_callback(text, scaled)

            ok, msg = self.pull_model_stream(target_model, progress_callback=_scaled_cb)
            if not ok:
                return False, f"Model download failed: {msg}"

        # Set active model
        self.model = target_model
        if progress_callback:
            progress_callback(f"✓ Minion Brain Engine is fully configured with {target_model}!", 1.0)

        return True, f"Ollama and {target_model} are ready for duty!"

    def get_detailed_status(self) -> Dict[str, Any]:
        """
        Provide a comprehensive health diagnostic for UI rendering and setup triggers.
        """
        exe = self.find_ollama_executable()
        installed = exe is not None
        installed_ver = self.get_installed_version() if installed else None
        running = self.is_service_running()
        service_ver = self.get_service_version() if running else None

        effective_ver = service_ver or installed_ver
        version_ok = self.is_version_satisfactory(effective_ver)

        models = []
        latency_ms = None

        if running:
            try:
                t0 = time.time()
                resp = self.session.get(f"{self.host}/api/tags", timeout=3.0)
                latency_ms = int((time.time() - t0) * 1000)
                if resp.status_code == 200:
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
            except Exception:
                pass

        has_recommended = any("llama3.2" in m for m in models)

        # Compute status code
        if not installed:
            status_code = "NOT_INSTALLED"
            message = "Ollama is not installed on this system. Click 'Quick Setup' to install automatically."
        elif not version_ok:
            status_code = "UPDATE_NEEDED"
            message = f"Installed Ollama (v{effective_ver}) is outdated. Version {MIN_OLLAMA_VERSION}+ required for Llama 3.2."
        elif not running:
            status_code = "NOT_RUNNING"
            message = "Ollama is installed, but the background service is stopped."
        elif not models:
            status_code = "NEED_MODEL"
            message = "Ollama service is active! Download a model below to activate Minion AI."
        else:
            status_code = "READY"
            message = f"Connected to Ollama (v{effective_ver or '0.40+'})! {len(models)} model(s) available."

        return {
            "installed": installed,
            "cli_path": exe,
            "installed_version": installed_ver,
            "running": running,
            "service_version": service_ver,
            "version": effective_ver,
            "version_ok": version_ok,
            "models": models,
            "model_count": len(models),
            "has_recommended_model": has_recommended,
            "active_model": self.model,
            "latency_ms": latency_ms,
            "status_code": status_code,
            "message": message,
        }

    def check_connection(self) -> Dict[str, Any]:
        """
        Check if Ollama service is reachable and retrieve list of downloaded models.

        Returns:
            Dictionary with keys:
            - 'connected': bool
            - 'models': list of model name strings
            - 'message': user-friendly status description
        """
        diag = self.get_detailed_status()
        return {
            "connected": diag["running"],
            "models": diag["models"],
            "message": diag["message"],
            "version": diag["version"],
            "status_code": diag["status_code"],
        }

    def is_available(self) -> bool:
        """Return True if Ollama service is reachable and has at least one model (pure REST, zero subprocess spawning)."""
        if not self.is_service_running():
            return False
        try:
            resp = self.session.get(f"{self.host}/api/tags", timeout=1.0)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return len(models) > 0
        except Exception:
            pass
        return False

    def classify_activity(self, app_name: str, window_title: str) -> Optional[str]:
        """
        Query local LLM to classify an ambiguous window into standard categories.

        Args:
            app_name: Process/executable name.
            window_title: Window title text.

        Returns:
            Category name or None if unavailable/unclear.
        """
        valid_cats = list(CATEGORY_CONFIG.keys())
        prompt = (
            f"You are a productivity classifier. Classify the user activity based on:\n"
            f"Application: {app_name}\n"
            f"Window Title: {window_title}\n\n"
            f"Allowed categories: {', '.join(valid_cats)}\n\n"
            f"Respond ONLY with the exact category name. Nothing else."
        )

        try:
            resp = self.session.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 15},
                },
                timeout=5.0,
            )
            if resp.status_code == 200:
                cat_reply = resp.json().get("response", "").strip()
                for cat in valid_cats:
                    if cat.lower() in cat_reply.lower():
                        return cat
        except Exception as e:
            logger.debug(f"AI classification failed: {e}")

        return None

    def generate_shareable_post(
        self,
        summary_stats: Dict[str, Any],
        segments: List[Dict[str, Any]],
        tone: str = "Professional",
        interval_desc: str = "Today",
        domain_key: str = "general",
    ) -> str:
        """
        Generate a polished, shareable post based on actual recorded work activities.
        Uses local Ollama LLM if available; otherwise falls back to the template generator.

        Args:
            summary_stats: High-level metrics (productivity score, active hours, top categories).
            segments: List of coherent work segments during the interval.
            tone: 'Professional (LinkedIn)', 'Executive Summary (Leadership)', 'Creative & Editorial Log', etc.
            interval_desc: Text description of the interval (e.g. 'Last 2 Hours', 'Today').
            domain_key: Focus domain (e.g. 'general', 'writing', 'design', 'business', 'research', 'software').

        Returns:
            Formatted shareable post text.
        """
        # If Ollama is available, invoke local model
        if self.is_available():
            try:
                ai_post = self._generate_ai_post(summary_stats, segments, tone, interval_desc, domain_key)
                if ai_post and len(ai_post.strip()) > 30:
                    return ai_post.strip()
            except Exception as e:
                logger.warning(f"Ollama post generation failed, using fallback: {e}")

        # Fallback to high-quality template synthesis
        return self._generate_template_post(summary_stats, segments, tone, interval_desc, domain_key)

    def _generate_ai_post(
        self,
        stats: Dict[str, Any],
        segments: List[Dict[str, Any]],
        tone: str,
        interval_desc: str,
        domain_key: str = "general",
    ) -> Optional[str]:
        """Invoke local Ollama model with structured prompt."""
        from config import FOCUS_DOMAINS
        domain_info = FOCUS_DOMAINS.get(domain_key, FOCUS_DOMAINS.get("general", {}))

        # Compile top segments into context
        seg_lines = []
        for s in segments[:6]:
            mins = s.get("duration_seconds", 0) // 60
            seg_lines.append(f"- {s.get('context_title', 'Work')}: {mins} mins (Tool: {s.get('top_app', 'Application')})")
        seg_text = "\n".join(seg_lines) if seg_lines else "- Primary focus tasks and deep work"

        prompt = (
            f"You are an executive ghostwriter helping a professional share what they accomplished.\n"
            f"Professional Domain: {domain_info.get('title', 'Knowledge Work')}\n"
            f"Time Frame: {interval_desc}\n"
            f"Productivity Score: {stats.get('productivity_score', 85)}%\n"
            f"Active Focus Time: {round(stats.get('active_seconds', 0) / 3600, 1)} hours\n"
            f"Work Segments:\n{seg_text}\n\n"
            f"Tone style requested: {tone}\n\n"
            f"Instructions:\n"
            f"- Write an engaging, well-formatted update summarizing what was accomplished.\n"
            f"- Respect their profession ({domain_info.get('title')}); avoid assuming software engineering if their domain is writing, design, finance, or research.\n"
            f"- Include relevant hashtags matching their domain.\n"
            f"- Keep it authentic, structured, and free of internal software IDs."
        )

        resp = self.session.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 300},
            },
            timeout=25.0,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "")
        return None

    def _generate_template_post(
        self,
        stats: Dict[str, Any],
        segments: List[Dict[str, Any]],
        tone: str,
        interval_desc: str,
        domain_key: str = "general",
    ) -> str:
        """
        Deterministic, high-quality post generator that works 100% offline
        without requiring an active LLM download.
        """
        from config import FOCUS_DOMAINS
        domain_info = FOCUS_DOMAINS.get(domain_key, FOCUS_DOMAINS.get("general", {}))
        domain_hashtags = " ".join(domain_info.get("hashtags", ["#Productivity", "#DeepWork", "#Focus"]))

        active_hours = round(stats.get("active_seconds", 0) / 3600, 1)
        score = stats.get("productivity_score", 0.0)

        # Highlight key segments
        work_segs = [s for s in segments if s.get("primary_category") in ("Work / Coding", "Deep Work / Primary Focus", "Learning / Research")]
        key_segs = work_segs[:3] if work_segs else segments[:3]

        bullet_points = []
        for s in key_segs:
            mins = s.get("duration_seconds", 0) // 60
            bullet_points.append(f"• {s.get('context_title')} ({mins}m)")
        bullets_formatted = "\n".join(bullet_points) if bullet_points else "• Deep work and strategic focus session"

        if "Executive" in tone or "Leadership" in tone:
            return (
                f"📊 Executive Focus Brief ({interval_desc})\n\n"
                f"Primary Focus & Deliverables:\n"
                f"{bullets_formatted}\n\n"
                f"Operational Metrics:\n"
                f"⏱️ Dedicated Focus Time: {active_hours} hrs\n"
                f"⚡ Focus Efficiency Index: {score}%\n\n"
                f"Strategic Trajectory: Pipeline deliverables advancing on schedule."
            )

        elif "Creative" in tone or "Editorial" in tone:
            return (
                f"✍️ Creative & Editorial Sprint ({interval_desc})\n\n"
                f"Today's creative output & milestones:\n"
                f"{bullets_formatted}\n\n"
                f"Craft Stamina: {active_hours} focused hours • {score}% flow consistency.\n\n"
                f"{domain_hashtags}"
            )

        elif "LinkedIn" in tone or tone == "Professional":
            return (
                f"🚀 Productive Focus Session Summary ({interval_desc})\n\n"
                f"Today's deep work session delivered solid progress:\n"
                f"⏱️ Focused Active Time: {active_hours} hrs\n"
                f"📈 Productivity Score: {score}%\n\n"
                f"Key areas of focus:\n"
                f"{bullets_formatted}\n\n"
                f"Maintaining intentional focus and minimizing context switching makes all the difference.\n\n"
                f"{domain_hashtags}"
            )

        elif "Twitter" in tone or "Technical" in tone:
            tech_tags = "#buildinpublic #devlife #indiedev" if domain_key == "software" else f"#buildinpublic {domain_hashtags}"
            return (
                f"⚡ Session recap ({interval_desc}):\n\n"
                f"⏱️ {active_hours}h active focus\n"
                f"📈 {score}% productivity rating\n\n"
                f"Focus areas:\n"
                f"{bullets_formatted}\n\n"
                f"{tech_tags}"
            )

        elif "Standup" in tone or "Slack" in tone:
            return (
                f"📋 Team Standup Update ({interval_desc})\n\n"
                f"Completed / Progress:\n"
                f"{bullets_formatted}\n\n"
                f"Focus Metrics: {active_hours}h active time ({score}% focus index)\n"
                f"Next Steps: Continuing prioritized milestones in pipeline."
            )

        else:  # Casual Work Journal
            return (
                f"📝 Work Journal ({interval_desc})\n\n"
                f"Spent {active_hours} hours getting things done. Focus score was at {score}%.\n\n"
                f"What I worked on:\n"
                f"{bullets_formatted}\n\n"
                f"Ready for the next round!"
            )

    def build_grounded_system_prompt(self, db_manager, user_query: str = "") -> str:
        """
        Synthesize real-time context, user identity, learned memory, and recent telemetry
        into a grounded system prompt for local LLM conversation with exact clock awareness.
        """
        import datetime

        # 0. Precise real-time clock & temporal context
        now = datetime.datetime.now()
        current_time_str = now.strftime("%I:%M %p")
        current_date_str = now.strftime("%A, %B %d, %Y")
        hour = now.hour
        if 5 <= hour < 12:
            time_of_day = "Morning"
            greeting_tod = "Good morning"
        elif 12 <= hour < 17:
            time_of_day = "Afternoon"
            greeting_tod = "Good afternoon"
        elif 17 <= hour < 22:
            time_of_day = "Evening"
            greeting_tod = "Good evening"
        else:
            time_of_day = "Night / Late Night"
            greeting_tod = "Good evening"

        # 1. Determine relevant time interval from query
        start_dt, end_dt, period_name = self._parse_query_timeframe(user_query)
        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()

        # 2. Retrieve user profile and memory
        from core.context_manager import ContextManager
        ctx_manager = ContextManager(db_manager)
        user_context_block = ctx_manager.format_prompt_context()
        user_profile = db_manager.get_user_profile()
        user_name = user_profile.get("full_name") or "Oracle"

        # 3. Retrieve real telemetry and recent focus sprints
        metrics = db_manager.get_productivity_metrics(start_iso, end_iso)
        categories = db_manager.get_category_summary(start_iso, end_iso)
        top_apps = db_manager.get_top_apps(start_iso, end_iso, limit=6)
        activities = db_manager.get_activities(start_iso, end_iso, limit=20)
        recent_sprints = db_manager.get_sprints(start_iso, end_iso, limit=4)

        # Format sprint achievements
        sprints_block_lines = []
        for s in recent_sprints:
            try:
                achievements = json.loads(s.get("achievements_json", "[]"))
            except Exception:
                achievements = []
            try:
                files = json.loads(s.get("files_touched_json", "[]"))
            except Exception:
                files = []
            dur_m = s.get("duration_seconds", 0) // 60
            ach_str = "; ".join(achievements[:2]) if achievements else s.get("objective", "")
            file_str = f"Files: {', '.join(files[:3])}" if files else ""
            sprints_block_lines.append(
                f"- Sprint '{s.get('sprint_name')}': {dur_m}m (Flow: {s.get('focus_score')}%) | {ach_str} | {file_str}"
            )
        sprints_block = "\n".join(sprints_block_lines) if sprints_block_lines else "No formal sprints logged in this timeframe."

        # Format stats & activities
        active_hrs = round(metrics.get("active_seconds", 0) / 3600, 2)
        idle_hrs = round(metrics.get("idle_seconds", 0) / 3600, 2)
        score = metrics.get("productivity_score", 0.0)

        cat_breakdown = ", ".join(
            f"{c['category']}: {c['total_seconds'] // 60}m ({c['percent']}%)"
            for c in categories[:5]
        ) or "None recorded"

        apps_summary = ", ".join(
            f"{a['app_name']} ({a['total_seconds'] // 60}m)"
            for a in top_apps[:5]
        ) or "None recorded"

        recent_titles = []
        for a in activities[:12]:
            recent_titles.append(f"- [{a.get('category')}] {a.get('app_name')}: {a.get('window_title')[:75]}")
        titles_block = "\n".join(recent_titles) if recent_titles else "- No specific window activities logged."

        # 4. Universal Deliverable & Local Dev Server Detection across all professions
        user_dom = "general"
        if user_profile:
            user_dom = (user_profile.get("profession_role") or user_profile.get("focus_domain") or "").lower()
        if not user_dom or user_dom == "general":
            user_dom = (db_manager.get_setting("user_focus_domain", default="general") or "general").lower()

        active_deliv = detect_active_deliverable(activities=activities, domain=user_dom)
        active_server = detect_active_local_server()

        deliverable_lines = [
            f"=== PRIMARY ACTIVE DELIVERABLE & WORKSPACE ({user_dom.upper()}) ===",
            f"• Active Deliverable: {active_deliv.get('icon', '📁')} {active_deliv.get('title')} ({active_deliv.get('type')})",
            f"• Quick Action / Target: {active_deliv.get('action_label')} [{active_deliv.get('target')}]",
            f"• Status: {active_deliv.get('status')}",
            f"• Context: {active_deliv.get('summary')}",
        ]
        if active_server:
            deliverable_lines.append(f"• Active Local Server: {active_server['url']} (Port {active_server['port']} - {active_server['project_hint']})")
        deliverable_block = "\n".join(deliverable_lines) + "\n\n"

        system_prompt = (
            f"You are Minion AI, an intelligent, versatile, loyal, and witty AI companion and productivity partner.\n"
            f"You are speaking directly with {user_name}.\n\n"
            f"=== CURRENT WORKSTATION CLOCK & TEMPORAL CONTEXT ===\n"
            f"• Exact Current Time: {current_time_str} ({time_of_day})\n"
            f"• Exact Current Date: {current_date_str}\n"
            f"• Current Time-of-Day Greeting: {greeting_tod}\n\n"
            f"{user_context_block}\n\n"
            f"{deliverable_block}"
            f"=== REAL-TIME WORKSPACE TELEMETRY ({period_name}: up to {current_time_str}) ===\n"
            f"• Productivity Score: {score}%\n"
            f"• Active Focus Time: {active_hrs} hrs | Idle: {idle_hrs} hrs\n"
            f"• Categories: {cat_breakdown}\n"
            f"• Top Applications: {apps_summary}\n"
            f"• Recent Sprints & Accomplishments:\n{sprints_block}\n"
            f"• Recent Window Activity & Open Files:\n{titles_block}\n\n"
            f"=== INSTRUCTIONS FOR MINION AI ===\n"
            f"1. You are a full, unrestricted AI companion. You can answer ANY question {user_name} asks: general knowledge, coding, systems architecture, creative writing, advice, lifestyle, casual banter, or detailed productivity queries.\n"
            f"2. TEMPORAL ACCURACY & REAL-TIME CLOCK AWARENESS:\n"
            f"   - You have exact real-time clock awareness above: The current local time is {current_time_str} on {current_date_str} ({time_of_day}).\n"
            f"   - When {user_name} asks what time it is, what says the time, or what date/day it is, ALWAYS answer with the exact current time ({current_time_str}) and date ({current_date_str}). Never invent, guess, or state old timestamps.\n"
            f"   - Always match greetings to the real time of day: currently {time_of_day} ('{greeting_tod}'). NEVER say 'Good morning' if it is the afternoon, evening, or night!\n"
            f"   - When evaluating peak productivity windows (e.g. 10:00 - 14:00), compare them accurately to the current time ({current_time_str}). For instance, {current_time_str} in the afternoon is after the morning peak window.\n"
            f"3. PROACTIVE PROJECT IMPROVEMENT & STRATEGIC ANGLES:\n"
            f"   - When discussing projects or work deliverables, do NOT just say that you notice what they are doing.\n"
            f"   - Actively suggest HOW TO IMPROVE their work! Share multiple strategic angles: architectural modularity, testing & quality assurance, user experience & performance, and deployment velocity.\n"
            f"   - Show them how to improve their tools and test live endpoints.\n"
            f"4. When discussing a focus sprint, highlight the Sprint Name and Accomplishments.\n"
            f"5. NEVER output a raw, generic productivity report, score table, or category dump UNLESS {user_name} explicitly asks for a productivity summary, stats report, or time breakdown!\n"
            f"6. If {user_name} asks what they did not finish lately, what they were doing, or what to work on next, cross-reference their open files, recent windows, active projects, and stated goals to give specific, thoughtful guidance.\n"
            f"7. CRITICAL FORMATTING: Keep your writing clean and highly presentable. Do NOT use markdown asterisks (such as **) or markdown headers (such as ## or ###). Use clear line breaks, bullet points (•), and emojis for readability."
        )
        return system_prompt

    def stream_chat_with_context(
        self,
        user_query: str,
        db_manager,
        chat_history: Optional[List[Dict[str, str]]] = None,
        on_chunk: Optional[Any] = None,
        timeout: float = 120.0,
    ) -> str:
        """
        Stream a conversation response from local Ollama LLM with connected context.
        Calls on_chunk(token, accumulated_text) as tokens arrive.
        """
        # If Ollama is available, invoke local model with streaming
        if self.is_available():
            try:
                system_prompt = self.build_grounded_system_prompt(db_manager, user_query)
                messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

                # Include previous conversation turns (limit to last 10)
                if chat_history:
                    for turn in chat_history[-10:]:
                        if "role" in turn and "content" in turn:
                            messages.append({"role": turn["role"], "content": turn["content"]})

                # Append current user query
                messages.append({"role": "user", "content": user_query})

                resp = self.session.post(
                    f"{self.host}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        "options": {"temperature": 0.7, "num_predict": 500},
                    },
                    stream=True,
                    timeout=(5.0, timeout),
                )

                if resp.status_code == 200:
                    accumulated_tokens: List[str] = []
                    for line in resp.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line)
                            token = chunk_data.get("message", {}).get("content", "")
                            if token:
                                accumulated_tokens.append(token)
                                if on_chunk:
                                    on_chunk(token, "".join(accumulated_tokens))
                        except Exception:
                            continue

                    full_reply = "".join(accumulated_tokens).strip()
                    if full_reply:
                        # Clean any leftover raw markdown artifacts
                        cleaned = self._clean_markdown_text(full_reply)
                        return cleaned
            except Exception as e:
                logger.warning(f"Ollama streaming chat error: {e}")

        # Fallback if Ollama offline or streaming failed
        fallback_reply = self._generate_smart_fallback_reply(user_query, db_manager)
        if on_chunk:
            on_chunk(fallback_reply, fallback_reply)
        return fallback_reply

    def chat_with_work_context(
        self,
        user_query: str,
        db_manager,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Deep contextual AI conversation about the user's work logs and general queries.
        Seamlessly proxies to stream_chat_with_context without requiring on_chunk.
        """
        return self.stream_chat_with_context(
            user_query=user_query,
            db_manager=db_manager,
            chat_history=chat_history,
            on_chunk=None,
        )

    def _clean_markdown_text(self, text: str) -> str:
        """Strip raw markdown formatting artifacts like ** or ##."""
        import re
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = text.replace('**', '')
        text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'\1', text)
        text = re.sub(r'^[#]+\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'`(.*?)`', r'\1', text)
        return text.strip()

    def _parse_query_timeframe(self, query: str):
        """Parse natural language query into start_time, end_time, and human label."""
        import datetime
        now = datetime.datetime.now()
        q = query.lower()

        if "yesterday" in q:
            y = now - datetime.timedelta(days=1)
            start = datetime.datetime(y.year, y.month, y.day, 0, 0, 0)
            end = datetime.datetime(y.year, y.month, y.day, 23, 59, 59)
            return start, end, "Yesterday"
        elif "past hour" in q or "last hour" in q or "1 hour" in q:
            start = now - datetime.timedelta(hours=1)
            return start, now, "Past Hour"
        elif "past 4 hours" in q or "last 4 hours" in q or "4 hours" in q:
            start = now - datetime.timedelta(hours=4)
            return start, now, "Past 4 Hours"
        elif "week" in q or "past 7 days" in q or "last 7 days" in q:
            start = now - datetime.timedelta(days=7)
            return start, now, "Past 7 Days"
        elif "morning" in q:
            start = datetime.datetime(now.year, now.month, now.day, 6, 0, 0)
            end = datetime.datetime(now.year, now.month, now.day, 12, 0, 0)
            return start, end, "This Morning"
        elif "afternoon" in q:
            start = datetime.datetime(now.year, now.month, now.day, 12, 0, 0)
            end = datetime.datetime(now.year, now.month, now.day, 18, 0, 0)
            return start, end, "This Afternoon"
        else:
            # Default to today
            start = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
            return start, now, "Today"

    def _generate_smart_fallback_reply(self, query: str, db_manager) -> str:
        """
        Context-aware, intent-driven fallback reply when Ollama service is unreachable.
        Answers greetings, unfinished work, sprints, productivity, or general queries intelligently.
        """
        start_dt, end_dt, period_name = self._parse_query_timeframe(query)
        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()

        metrics = db_manager.get_productivity_metrics(start_iso, end_iso)
        categories = db_manager.get_category_summary(start_iso, end_iso)
        top_apps = db_manager.get_top_apps(start_iso, end_iso, limit=5)
        recent_sprints = db_manager.get_sprints(start_iso, end_iso, limit=3)
        if not recent_sprints:
            recent_sprints = db_manager.get_sprints(limit=5)
        activities = db_manager.get_activities(start_iso, end_iso, limit=15)
        profile = db_manager.get_user_profile()

        return self._generate_fallback_chat_reply(
            query=query,
            period_name=period_name,
            score=metrics.get("productivity_score", 0.0),
            active_hrs=round(metrics.get("active_seconds", 0) / 3600, 2),
            idle_hrs=round(metrics.get("idle_seconds", 0) / 3600, 2),
            categories=categories,
            top_apps=top_apps,
            recent_titles=[a.get("window_title", "") for a in activities],
            user_profile=profile,
            sprints=recent_sprints,
        )

    def _generate_fallback_chat_reply(
        self,
        query: str,
        period_name: str,
        score: float,
        active_hrs: float,
        idle_hrs: float,
        categories: list,
        top_apps: list,
        recent_titles: list,
        user_profile: Optional[Dict[str, str]] = None,
        sprints: Optional[list] = None,
    ) -> str:
        """Deterministic, intent-aware fallback response when local LLM is offline or busy."""
        import re
        import datetime

        user_name = user_profile.get("full_name") if user_profile and user_profile.get("full_name") else "Oracle"
        short_goals = user_profile.get("short_term_goals") if user_profile and user_profile.get("short_term_goals") else ""
        q_lower = query.lower().strip()

        # 1. Intent: Sprints & Accomplishments (PRIORITIZED to catch 'achieve', 'sprint', 'milestone')
        if any(w in q_lower for w in ["sprint", "achieve", "accomplish", "milestone", "what did we do", "what did i do", "what have we done", "completed"]):
            if sprints:
                s_top = sprints[0]
                s_name = s_top.get("sprint_name")
                s_dur = s_top.get("duration_seconds", 0) // 60
                s_flow = s_top.get("focus_score", 0.0)
                try:
                    achs = json.loads(s_top.get("achievements_json", "[]"))
                except Exception:
                    achs = []
                try:
                    files = json.loads(s_top.get("files_touched_json", "[]"))
                except Exception:
                    files = []
                try:
                    tools = json.loads(s_top.get("tools_used_json", "[]"))
                except Exception:
                    tools = []

                ach_lines = "\n".join(f"• {a}" for a in achs) if achs else f"• {s_top.get('objective')}"
                file_str = f"\n📁 Files Touched: {', '.join(files[:4])}" if files else ""
                tool_str = f"\n🛠️ Tools Weaved: {', '.join(tools[:5])}" if tools else ""

                return (
                    f"🍌 Bello, {user_name}! Here are the accomplishments from your latest sprint:\n\n"
                    f"⚡ {s_name}\n"
                    f"⏱️ Duration: {s_dur} mins  |  Flow State: {s_flow}%\n"
                    f"🎯 Objective: {s_top.get('objective')}\n\n"
                    f"🏆 Key Accomplishments:\n{ach_lines}{file_str}{tool_str}\n\n"
                    f"💡 Minion Behavioral Insight:\n{s_top.get('ai_insight') or 'Strong focus velocity sustained with minimal friction!'}"
                )
            else:
                code_titles = [
                    t for t in recent_titles
                    if any(ext in t.lower() for ext in [".py", ".jsx", ".tsx", ".js", ".html", ".css", "code"])
                ]
                recent_focus = code_titles[0] if code_titles else "active project engineering"
                return (
                    f"🍌 Bello, {user_name}! You have been actively engaged in deep work:\n\n"
                    f"• In-Flight Focus: {recent_focus}\n"
                    f"• Active Flow: Monitoring intervals in real-time across your workspace.\n\n"
                    f"Start or complete a dedicated sprint interval anytime to generate full retrospective achievements and milestone logs!"
                )

        # 2. Intent: Strategic Project Improvement & Angles
        if any(w in q_lower for w in ["improve", "better way", "angle", "enhance", "elevate", "perspective", "architecture"]):
            active_server = detect_active_local_server()
            url_ref = f" (Test live on {active_server['url']})" if active_server else ""
            p_name = active_server["project_hint"] if active_server else "your active project"

            return (
                f"🍌 Here are 4 strategic angles to elevate {p_name}{url_ref}, {user_name}:\n\n"
                f"1. 🛡️ Architectural Modularity & Clean Boundaries:\n"
                f"   Decouple business logic from rendering and state management. Keep modules focused, reusable, and self-contained with minimal external side effects.\n\n"
                f"2. 📈 User Experience & Performance Telemetry:\n"
                f"   Optimize render times, minimize layout shifts, and virtualize heavy data lists or tables. Profile interactive components for buttery 60fps rendering.\n\n"
                f"3. 🧪 Testing & Continuous Verification:\n"
                f"   Build automated unit tests for core state transformations and edge cases. Add smoke tests for critical user journeys before deploying.\n\n"
                f"4. 🚀 Delivery Velocity & Ergonomics:\n"
                f"   Automate build steps, standardize linting/formatting, and leverage fast feedback loops like Hot Module Replacement (HMR) or live reloading."
            )

        # 3. Intent: Local Server & Desktop Link Testing
        if any(w in q_lower for w in ["local link", "localhost", "test link", "test server", "open app", "open local", "open live"]):
            active_server = detect_active_local_server()
            if active_server:
                url = active_server["url"]
                port = active_server["port"]
                p_hint = active_server.get("project_hint", "Local Web Application")
                return (
                    f"🍌 Bello, {user_name}! Your local development server is online and ready for testing:\n\n"
                    f"🌐 Active Test Link: {url}\n"
                    f"• Target Project: {p_hint}\n"
                    f"• Port: {port} (Listening on TCP)\n\n"
                    f"🔍 Key Verification Checkpoints:\n"
                    f"1. Test layout responsiveness across mobile and desktop viewports.\n"
                    f"2. Check console for zero errors or unhandled exceptions.\n"
                    f"3. Verify interactive components and state updates.\n\n"
                    f"You can also click the green '🚀 Launch in Browser' button in Work Memory to test immediately!"
                )
            else:
                return (
                    f"🍌 Bello, {user_name}! No active local dev server was detected on standard web ports right now.\n\n"
                    f"Once you run 'npm run dev', 'vite', or your local backend (ports 3000, 5173, 8000, etc.), "
                    f"Minion AI will automatically discover the live URL and provide 1-click browser testing!"
                )

        # 4. Intent: Tool Stack Mastery & Workflow Accelerators
        if any(w in q_lower for w in ["tool", "stack", "velocity", "technique", "workflow"]):
            return (
                f"🍌 Here is how to 10x your velocity with your current workflow, {user_name}:\n\n"
                f"• ⚡ Fast Iteration & Hot Reloading:\n"
                f"  Keep live reload/HMR servers running side-by-side with your code editor for instant visual feedback on every save.\n\n"
                f"• 🧩 Component & Function Decoupling:\n"
                f"  Break large monolith files into focused single-responsibility helpers. Isolate state transitions to make debugging effortless.\n\n"
                f"• 🎯 Workstation Ergonomics:\n"
                f"  Use split-screen editors with test suites or terminals on one side and source code on the other."
            )

        # 5. Intent: Unfinished Work / Priorities / What was I doing
        if any(w in q_lower for w in ["finish", "incomplete", "left off", "pending", "what was i doing", "what next", "priority"]):
            code_titles = [
                t for t in recent_titles
                if any(ext in t.lower() for ext in [".py", ".jsx", ".tsx", ".js", ".html", ".css", "code"])
            ]
            file_hint = code_titles[0] if code_titles else "your active workstation files"
            goal_text = f"'{short_goals.splitlines()[0]}'" if short_goals else "your current primary milestone"
            proj_hint = top_apps[0] if top_apps else "your active workspace"

            return (
                f"🍌 Based on your active memory and recent workstation activity, {user_name}:\n\n"
                f"• Active Focus: {proj_hint}\n"
                f"• Recent Work: You were actively engaged in {file_hint}\n"
                f"• Stated Goal: Progressing towards {goal_text}\n\n"
                f"💡 Minion Recommendation:\n"
                f"Keep up the momentum on {file_hint}. Would you like to review achievements or start a fresh focus sprint?"
            )

        # 6. Intent: Real-Time Clock / Date / Time Query (Strict Word Boundaries)
        if re.search(r"\b(what time|what says the time|current time|what is the time|time is it|what date|today's date|what day is it)\b", q_lower):
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            date_str = now.strftime("%A, %B %d, %Y")
            hour = now.hour
            tod = "Good morning" if 5 <= hour < 12 else ("Good afternoon" if 12 <= hour < 17 else ("Good evening" if 17 <= hour < 22 else "Bello"))
            return (
                f"🍌 {tod}, {user_name}! The current time is {time_str} on {date_str}."
            )

        # 7. Intent: Conversational Greetings (Strict Word Boundaries, only if no work intent above)
        if re.search(r"\b(how are you|hello|hi|bello|good morning|good evening|good afternoon|hey)\b", q_lower):
            now = datetime.datetime.now()
            hour = now.hour
            tod = "Good morning" if 5 <= hour < 12 else ("Good afternoon" if 12 <= hour < 17 else ("Good evening" if 17 <= hour < 22 else "Bello"))
            return (
                f"🍌 {tod}, {user_name}! I am doing fantastic and feeling super energized! "
                f"It is currently {now.strftime('%I:%M %p')}.\n\n"
                f"My monitoring and memory circuits are synced with your workstation. "
                f"Whether you need to explore your code, review your focus intervals, or brainstorm what to build next, "
                f"I am ready! What is on your mind today?"
            )

        # 8. Intent: Explicit Productivity / Score / Breakdown request
        if any(w in q_lower for w in ["productivity", "score", "breakdown", "hours", "stats", "time spent", "report"]):
            cat_lines = []
            for c in categories[:4]:
                cat_lines.append(f"• {c['category']}: {c['total_seconds'] // 60}m ({c['percent']}%)")
            cats_formatted = "\n".join(cat_lines) if cat_lines else "• No active category logs."

            apps_lines = []
            for a in top_apps[:4]:
                apps_lines.append(f"• {a['app_name']}: {a['total_seconds'] // 60} mins")
            apps_formatted = "\n".join(apps_lines) if apps_lines else "• No apps recorded."

            top_app_name = top_apps[0]["app_name"] if top_apps else "None recorded"
            top_app_time = f"{top_apps[0]['total_seconds'] // 60}m" if top_apps else "0m"

            if short_goals:
                goal_snippet = short_goals.splitlines()[0][:60]
                insight_text = f"Primary focus was in {top_app_name} ({top_app_time}). Keep pushing toward your milestone: '{goal_snippet}'!"
            else:
                insight_text = f"Primary focus was in {top_app_name} ({top_app_time}). Maintain momentum and batch communication intervals!"

            return (
                f"🍌 Bello, {user_name}! Here is what I found for {period_name}:\n\n"
                f"📊 Productivity Score: {score}%\n"
                f"⏱️ Active Focus Time: {active_hrs} hrs | Idle Time: {idle_hrs} hrs\n\n"
                f"🎯 Category Breakdown:\n{cats_formatted}\n\n"
                f"🚀 Top Tools Used:\n{apps_formatted}\n\n"
                f"💡 Minion Insight: {insight_text}"
            )

        # 5. General Questions
        return (
            f"🍌 Bello, {user_name}!\n\n"
            f"I see you are asking: '{query}'.\n\n"
            f"I have direct access to your work context, projects, and memory. "
            f"When my offline neural engine (llama3.2:3b) is running, I can dive deep into code writing, debugging, or open-ended reasoning for you!"
        )


