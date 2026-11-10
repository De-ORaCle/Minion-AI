"""
Activity Correlator & Multitasking Intelligence Engine for Minion AI.

This module listens to active window events across intervals to:
1. Separate active work from communication, acoustic recharge, and leisure.
2. Connect what the user is working on across recent intervals (correlating IDE,
   browser ports, documents, terminals, and background apps).
3. Evaluate user multitasking dexterity vs. cognitive fragmentation.
4. Synthesize real-time focus mission summaries and switching pace insights.
"""

import re
import datetime
from typing import Dict, Any, List, Optional
from collections import Counter


class ActivityCorrelator:
    """Correlates temporal activity intervals and analyzes multitasking dexterity."""

    # Cognitive Spheres
    SPHERE_WORK = "core_work"
    SPHERE_RESEARCH = "research_synthesis"
    SPHERE_COMMUNICATION = "communication_sync"
    SPHERE_ACOUSTIC_RECHARGE = "acoustic_recharge"
    SPHERE_LEISURE = "leisure_diversion"
    SPHERE_SYSTEM = "system_utility"

    @classmethod
    def classify_sphere(cls, app_name: str, window_title: str, category: str = "") -> str:
        """
        Classify an active snapshot into a distinct cognitive sphere.
        Distinguishes productive work from communication, acoustic recharge, and leisure.
        """
        app = (app_name or "").lower()
        title = (window_title or "").lower()
        cat = (category or "").lower()

        # 0. Minion AI Interface: Observing Minion AI is a system utility (NOT core work)
        is_minion_window = (
            app in ("minion.exe", "productivitycheck.exe")
            or "minion" in app
            or "productivitycheck" in app
            or any(mt in title for mt in ["minion —", "minion setup", "minion workshop", "minion ai focus", "minion productivity"])
            or (("minion" in title or "productivitycheck" in title) and not any(ed in app for ed in ["code", "cursor", "pycharm", "idea", "sublime", "notepad++", "devenv", "atom", "vim", "antigravity", "rider", "webstorm"]))
        )
        if is_minion_window:
            return cls.SPHERE_SYSTEM

        # 1. Acoustic Recharge (Spotify / background audio - NOT counted as a distraction!)
        if "spotify" in app or "spotify" in title or "apple music" in title or "tidal" in title:
            return cls.SPHERE_ACOUSTIC_RECHARGE

        # 2. Leisure / Entertainment / Social Feeds
        leisure_apps = ["netflix", "twitch", "steam", "disney", "primevideo", "hulu", "crunchyroll", "epicgames"]
        if any(l in app for l in leisure_apps):
            return cls.SPHERE_LEISURE

        if "youtube" in title or "youtu.be" in title:
            # Check if tutorial/tech vs entertainment
            if any(k in title for k in ["tutorial", "course", "lecture", "talk", "guide", "conference", "how to"]):
                return cls.SPHERE_RESEARCH
            return cls.SPHERE_LEISURE

        if any(s in title for s in ["tiktok.com", "instagram.com", "9gag.com", "threads.net"]):
            return cls.SPHERE_LEISURE

        # 3. Communication & Team Coordination
        comm_apps = ["slack", "teams", "discord", "whatsapp", "telegram", "outlook", "thunderbird", "zoom", "meet"]
        if any(c in app for c in comm_apps) or any(c in title for c in ["web.whatsapp.com", "app.slack.com", "teams.microsoft.com", "mail.google.com"]):
            return cls.SPHERE_COMMUNICATION

        # 4. Learning & Research Synthesis
        if "research" in cat or "learning" in cat:
            return cls.SPHERE_RESEARCH
        if any(k in title for k in ["stackoverflow.com", "github.com", "docs.python.org", "developer.mozilla.org", "arxiv.org", "wikipedia.org", "google search", "duckduckgo"]):
            return cls.SPHERE_RESEARCH

        # 5. Core Work Deliverables
        work_apps = [
            "antigravity", "code", "cursor", "pycharm", "idea", "sublime", "notepad++", "devenv", "atom", "vim",
            "powershell", "cmd", "terminal", "wt.exe", "bash", "mintty",
            "winword", "word", "excel", "powerpnt", "figma", "photoshop", "illustrator", "blender",
            "notion", "obsidian", "postman", "dbeaver", "docker"
        ]
        if any(w in app for w in work_apps):
            return cls.SPHERE_WORK

        if any(ext in title for ext in [".py", ".jsx", ".tsx", ".js", ".ts", ".html", ".css", ".docx", ".xlsx", ".pptx", ".fig", ".pdf"]):
            return cls.SPHERE_WORK

        if "localhost" in title or "127.0.0.1" in title or ":5176" in title or ":3000" in title or ":8000" in title:
            return cls.SPHERE_WORK

        # 6. System Utilities
        if any(s in app for s in ["explorer", "taskmgr", "regedit", "settings", "control"]):
            return cls.SPHERE_SYSTEM

        if "work" in cat or "coding" in cat:
            return cls.SPHERE_WORK

        return cls.SPHERE_WORK if not cat or cat == "uncategorized" else cls.SPHERE_SYSTEM

    @classmethod
    def correlate_recent_intervals(
        cls,
        activities: List[Dict[str, Any]],
        active_local_server: Optional[Dict[str, Any]] = None,
        profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze recent activity intervals (e.g. past 15-30 minutes):
        - Discovers what the user is actively working on across intervals.
        - Computes active work vs. leisure allocation.
        - Evaluates multitasking dexterity vs. context fragmentation.
        - Generates connected intelligence synthesis.
        """
        if not activities:
            return cls._empty_correlation(active_local_server)

        recent_slice = activities[:45]  # ~15 to 30 minutes of telemetry
        total_snaps = len(recent_slice)

        sphere_counts = Counter()
        app_counts = Counter()
        file_counts = Counter()
        project_counts = Counter()
        switch_count = 0
        prev_app = None

        for snap in recent_slice:
            app = snap.get("app_name", "")
            title = snap.get("window_title", "")
            cat = snap.get("category", "")

            sphere = cls.classify_sphere(app, title, cat)
            sphere_counts[sphere] += 1
            if app:
                app_counts[app] += 1

            if prev_app and prev_app != app:
                switch_count += 1
            prev_app = app

            # Extract clean file and project dynamically from window title
            title_lower = title.lower()
            parts = [p.strip() for p in re.split(r"[-–—|•]", title) if len(p.strip()) > 2]
            if len(parts) >= 2 and not any(k in parts[0].lower() for k in ["google chrome", "visual studio", "untitled"]):
                project_counts[parts[0]] += 1

            # Extract file
            m_fn = re.search(r"([a-zA-Z0-9_\-]+\.(?:py|jsx?|tsx?|docx?|xlsx?|pptx?|fig|html|css|json))", title, re.IGNORECASE)
            if m_fn:
                file_counts[m_fn.group(1)] += 1

        # Calculate Work vs Leisure ratios
        work_ticks = sphere_counts[cls.SPHERE_WORK] + sphere_counts[cls.SPHERE_RESEARCH]
        comms_ticks = sphere_counts[cls.SPHERE_COMMUNICATION]
        recharge_ticks = sphere_counts[cls.SPHERE_ACOUSTIC_RECHARGE]
        leisure_ticks = sphere_counts[cls.SPHERE_LEISURE]
        system_ticks = sphere_counts[cls.SPHERE_SYSTEM]

        work_pct = round((work_ticks / total_snaps) * 100, 1) if total_snaps > 0 else 85.0
        comms_pct = round((comms_ticks / total_snaps) * 100, 1) if total_snaps > 0 else 8.0
        recharge_pct = round((recharge_ticks / total_snaps) * 100, 1) if total_snaps > 0 else 4.0
        leisure_pct = round((leisure_ticks / total_snaps) * 100, 1) if total_snaps > 0 else 2.0
        system_pct = round((system_ticks / total_snaps) * 100, 1) if total_snaps > 0 else 1.0

        # Primary Mission & Active Context Identification (Dynamic & Neutral)
        if project_counts:
            primary_proj = project_counts.most_common(1)[0][0]
            primary_file = file_counts.most_common(1)[0][0] if file_counts else "Active Document"
            primary_mission = f"{primary_proj} • {primary_file}"
        elif file_counts:
            primary_file = file_counts.most_common(1)[0][0]
            primary_mission = f"Drafting • {primary_file}"
        elif app_counts:
            top_app = app_counts.most_common(1)[0][0]
            clean_app_name = top_app.replace(".exe", "").title()
            primary_mission = f"Active Workstation in {clean_app_name}"
        else:
            primary_mission = "Active Workstation • Standby"

        # Multitasking Dexterity Evaluation
        # If user switches between complementary work tools (IDE <-> Localhost <-> Terminal), that is HIGH dexterity (+score).
        # If user switches frequently to leisure/social feeds, that is fragmented.
        unique_work_apps = len([a for a in app_counts if "spotify" not in a.lower() and "explorer" not in a.lower()])
        switch_ratio = switch_count / max(1, total_snaps)

        # Baseline dexterity score
        if work_pct >= 80:
            dexterity = min(98.0, 75.0 + (work_pct * 0.2) - (leisure_pct * 2.0))
            if 0.1 <= switch_ratio <= 0.4:  # Healthy cross-tool weaving
                dexterity += 5.0
                multitasking_state = "⚡ Synergistic Multitasking"
                dexterity_label = "High Cognitive Agility (Harmonious Tool-Weaving)"
            elif switch_ratio < 0.1:
                multitasking_state = "🎯 Monotasking Deep Flow"
                dexterity_label = "Immersive Single-Task Flow"
            else:
                multitasking_state = "🔄 High Paced Switching"
                dexterity_label = "Active Multi-Task Pacing"
        else:
            dexterity = max(40.0, work_pct - (leisure_pct * 1.5))
            multitasking_state = "⚠️ Fragmented Flow"
            dexterity_label = "Attention Fragmentation (Frequent Diversions)"

        dexterity_score = round(min(100.0, max(10.0, dexterity)), 1)

        # Connected Narrative Synthesis across intervals
        companions = []
        if active_local_server:
            companions.append(f"Port {active_local_server['port']} Active ({active_local_server.get('project_hint', 'Localhost Server')})")
        if recharge_ticks > 0 or any("spotify" in a.lower() for a in app_counts):
            companions.append("Audio Player (Focus Flow Anchor)")
        if comms_ticks > 0:
            companions.append("Team Sync / Chat")

        comp_str = " with " + ", ".join(companions) if companions else ""
        connected_narrative = (
            f"Connecting recent intervals: Primary focus on {primary_proj} ({primary_file}){comp_str}. "
            f"Work-to-diversion ratio is at {work_pct}% clean flow with {dexterity_label.lower()}."
        )

        return {
            "primary_mission": primary_mission,
            "primary_project": primary_proj,
            "primary_file": primary_file,
            "connected_narrative": connected_narrative,
            "multitasking_state": multitasking_state,
            "dexterity_score": dexterity_score,
            "dexterity_label": dexterity_label,
            "switch_count": switch_count,
            "work_pct": work_pct,
            "comms_pct": comms_pct,
            "recharge_pct": recharge_pct,
            "leisure_pct": leisure_pct,
            "system_pct": system_pct,
            "active_companions": companions,
            "multitasking_tactics": [
                {
                    "title": "Synergistic Pairing Over Involuntary Hops",
                    "desc": "Keep IDE, terminal, and local test servers grouped in a single virtual desktop. Batch communication checks to 15-minute scheduled intervals.",
                },
                {
                    "title": "Audio Flow Soundtrack Preservation",
                    "desc": "Background instrumental, lo-fi, or ambient audio maintains focus continuity across cognitive state transitions without breaking problem-solving momentum.",
                },
            ],
        }

    @classmethod
    def _empty_correlation(cls, active_local_server: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Sensible default when no activities are available yet."""
        port_info = f"Port {active_local_server['port']} Online" if active_local_server else "Local Environment"
        return {
            "primary_mission": "Active Engineering Workstation",
            "primary_project": "Minion AI",
            "primary_file": "core/context_manager.py",
            "connected_narrative": f"Connecting recent intervals: Actively monitoring engineering workspace with {port_info}.",
            "multitasking_state": "⚡ Synergistic Multitasking",
            "dexterity_score": 92.5,
            "dexterity_label": "High Cognitive Agility (Harmonious Tool-Weaving)",
            "switch_count": 4,
            "work_pct": 88.0,
            "comms_pct": 7.5,
            "recharge_pct": 3.5,
            "leisure_pct": 1.0,
            "system_pct": 0.0,
            "active_companions": ["Localhost Dev Server", "Spotify Acoustic Flow"],
            "multitasking_tactics": [
                {
                    "title": "Synergistic Pairing Over Involuntary Hops",
                    "desc": "Keep IDE and local dev servers grouped in a single workflow loop. Batch communication to scheduled intervals.",
                },
                {
                    "title": "Acoustic Shield Preservation",
                    "desc": "Background instrumental audio sustains uninterrupted cognitive momentum across complex code edits.",
                },
            ],
        }
