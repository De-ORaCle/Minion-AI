"""
Context Management & Memory Engine for Minion.

This module coordinates:
1. User profile persistence (Name, Profession, Purpose/Why, Goals, Boundaries).
2. Importing and exporting context via Markdown (.md) or JSON (.json) files.
3. Telemetry synthesis into learned behavioral memory facts.
4. Formatting grounded prompt context for Minion AI and ghostwriting.
"""

import os
import json
import re
import datetime
from typing import Dict, Any, List, Optional
from core.database import DatabaseManager
from core.memory_synthesizer import MemorySynthesizer


class ContextManager:
    """Coordinates user profile, learned memory, and context ingestion/export."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.synthesizer = MemorySynthesizer(db_manager)

    def synthesize_deep_memory(self, force: bool = False) -> Dict[str, Any]:
        """
        Analyze historical screen telemetry and extract rich behavioral knowledge graph.
        Caches the synthesized graph in the database to allow instantaneous loading without blank screens.
        """
        if not force:
            cached_json = self.db.get_setting("cached_knowledge_graph", default="")
            if cached_json:
                try:
                    data = json.loads(cached_json)
                    if isinstance(data, dict) and data.get("focus_style"):
                        life = data.get("lifestyle_data", {})
                        tracks = life.get("music_tracks", [])
                        # Invalidate stale cache if it contains legacy mock keywords, lacks genre distribution, or has corrupted tracks
                        has_duplicates = len(tracks) > 1 and len(set(tracks)) < len(tracks)
                        has_generic_only = bool(tracks) and all("streaming (background audio)" in str(t).lower() for t in tracks)
                        has_legacy_mocks = any(k in cached_json for k in ["Dealroom", "35%", "Noah Kahan", "Vincent Lima", "Automation Theory and LLM"])
                        if not has_duplicates and not has_generic_only and not has_legacy_mocks and "genre_distribution" in life:
                            return data
                except Exception:
                    pass

        graph = self.synthesizer.synthesize_knowledge_graph()
        try:
            self.db.set_setting("cached_knowledge_graph", json.dumps(graph))
        except Exception:
            pass
        return graph

    def get_full_context_summary(self) -> Dict[str, Any]:
        """Aggregate user profile, PC context, and learned memory into a single bundle."""
        profile = self.db.get_user_profile()
        pc = self.db.get_pc_context()
        facts = self.db.get_learned_facts(limit=10)

        return {
            "profile": profile,
            "pc_context": pc,
            "learned_facts": facts,
        }

    def import_from_file(self, file_path: str) -> Dict[str, str]:
        """
        Parse and import user context from a .json or .md file.
        Returns the parsed dictionary.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".json":
            return self._import_json(file_path)
        elif ext in (".md", ".txt", ".markdown"):
            return self._import_markdown(file_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Please choose a .json or .md file.")

    def _import_json(self, file_path: str) -> Dict[str, str]:
        """Parse structured JSON context."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        profile = self.db.get_user_profile()

        # Map common keys
        mapping = {
            "full_name": ["full_name", "name", "user_name"],
            "profession_role": ["profession_role", "profession", "role", "what_i_do", "occupation"],
            "purpose_why": ["purpose_why", "purpose", "why", "motivation", "mission"],
            "short_term_goals": ["short_term_goals", "short_goals", "current_goals", "weekly_goals"],
            "long_term_goals": ["long_term_goals", "long_goals", "yearly_goals", "vision"],
            "things_to_avoid": ["things_to_avoid", "avoid", "distractions", "anti_goals", "boundaries"],
            "extra_context": ["extra_context", "notes", "context", "background", "instructions"],
        }

        for target_key, candidates in mapping.items():
            for c in candidates:
                if c in data and str(data[c]).strip():
                    val = data[c]
                    if isinstance(val, list):
                        profile[target_key] = "\n".join(f"• {item}" for item in val)
                    else:
                        profile[target_key] = str(val).strip()
                    break

        self.db.save_user_profile(profile)
        return profile

    def _import_markdown(self, file_path: str) -> Dict[str, str]:
        """Parse structured or free-form Markdown context."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        profile = self.db.get_user_profile()

        # Regex search for key sections
        def extract_section(keywords: List[str]) -> Optional[str]:
            for kw in keywords:
                pattern = rf"(?i)(?:^#{1,3}\s*|\*{1,2}){kw}(?:\*{1,2}|:)?\s*\n(.*?)(?=\n#{1,3}\s+|\n\*{1,2}[A-Z]|\Z)"
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    return match.group(1).strip()
            return None

        name = extract_section(["Name", "User", "Who am I", "Identity"])
        role = extract_section(["Role", "What I do", "Profession", "Occupation", "Job"])
        why = extract_section(["Why", "Purpose", "Motivation", "Mission"])
        short_goals = extract_section(["Short Term Goals", "Short-term Goals", "Current Goals", "Weekly Goals"])
        long_goals = extract_section(["Long Term Goals", "Long-term Goals", "Vision", "Milestones"])
        avoid = extract_section(["Things to Avoid", "Avoid", "Distractions", "Boundaries", "Anti-Goals"])

        if name:
            profile["full_name"] = name
        if role:
            profile["profession_role"] = role
        if why:
            profile["purpose_why"] = why
        if short_goals:
            profile["short_term_goals"] = short_goals
        if long_goals:
            profile["long_term_goals"] = long_goals
        if avoid:
            profile["things_to_avoid"] = avoid

        # Always save full markdown into extra_context
        profile["extra_context"] = content.strip()

        self.db.save_user_profile(profile)
        return profile

    def export_to_file(self, export_path: str) -> str:
        """Export current profile to JSON or Markdown based on extension."""
        ext = os.path.splitext(export_path)[1].lower()
        profile = self.db.get_user_profile()

        if ext == ".json":
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
        else:
            # Markdown export
            md_lines = [
                f"# Minion User Profile Context: {profile.get('full_name') or 'Boss'}",
                f"*Exported on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*",
                "",
                "## 👤 Identity & Role",
                f"**Name**: {profile.get('full_name') or 'Not specified'}",
                f"**Profession / What I do**:\n{profile.get('profession_role') or 'Not specified'}",
                "",
                "## 🎯 Purpose & Motivation",
                f"{profile.get('purpose_why') or 'Not specified'}",
                "",
                "## ⏱️ Short-Term Goals",
                f"{profile.get('short_term_goals') or 'Not specified'}",
                "",
                "## 🚀 Long-Term Goals",
                f"{profile.get('long_term_goals') or 'Not specified'}",
                "",
                "## 🛑 Things to Avoid & Distractions",
                f"{profile.get('things_to_avoid') or 'Not specified'}",
                "",
            ]
            if profile.get("extra_context"):
                md_lines.extend([
                    "## 📝 Additional Notes & Context",
                    profile["extra_context"],
                    "",
                ])

            with open(export_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_lines))

        return export_path

    def analyze_and_update_learned_habits(self) -> List[str]:
        """
        Analyze recent telemetry to automatically synthesize and learn user habits,
        storing them into Minion's memory.
        """
        now = datetime.datetime.now()
        start = (now - datetime.timedelta(days=7)).isoformat()
        end = now.isoformat()

        top_apps = self.db.get_top_apps(start, end, limit=5)
        categories = self.db.get_category_summary(start, end)

        learned = []
        if top_apps:
            primary_app = top_apps[0]
            hrs = round(primary_app["total_seconds"] / 3600, 1)
            fact1 = f"Primary software tool: {primary_app['app_name']} ({hrs} hrs logged in past 7 days)"
            self.db.add_learned_fact("work_habit", fact1, confidence=0.95)
            learned.append(fact1)

        # Distraction observation
        distract_cats = [c for c in categories if "Entertainment" in c["category"] or "Social" in c["category"]]
        if distract_cats:
            distract_time = sum(c["total_seconds"] for c in distract_cats) // 60
            if distract_time > 30:
                fact2 = f"Observed {distract_time} mins in media/entertainment platforms over past 7 days"
                self.db.add_learned_fact("distraction_pattern", fact2, confidence=0.85)
                learned.append(fact2)

        return learned

    def format_prompt_context(self) -> str:
        """Construct the prompt grounding text containing user identity, goals, PC specs, and learned facts."""
        profile = self.db.get_user_profile()
        pc = self.db.get_pc_context()
        facts = self.db.get_learned_facts(limit=12)

        user_name = profile.get("full_name") or "Boss"
        role = profile.get("profession_role") or "Knowledge Worker / Developer"
        why = profile.get("purpose_why") or "Building meaningful work and maximizing productivity"
        short_goals = profile.get("short_term_goals") or "Focusing on current daily tasks"
        long_goals = profile.get("long_term_goals") or "Continuous professional mastery"
        avoid = profile.get("things_to_avoid") or "Context switching and unapproved distractions"
        extra = profile.get("extra_context") or "No custom instructions."

        facts_text = "\n".join(f"  • {f['fact_text']}" for f in facts) if facts else "  • Observational memory active."

        pc_summary = (
            f"{pc.get('hostname', 'PC')} | {pc.get('os_info', 'Windows')} | "
            f"{pc.get('cpu_info', 'CPU')} | {pc.get('ram_info', 'RAM')} | {pc.get('display_info', 'Display')}"
        )

        return (
            f"=== USER IDENTITY & WORK CONTEXT ===\n"
            f"• User Name: {user_name}\n"
            f"• What they do: {role}\n"
            f"• Motivation & Why: {why}\n"
            f"• Short-term Goals: {short_goals}\n"
            f"• Long-term Goals: {long_goals}\n"
            f"• Things to Avoid: {avoid}\n"
            f"• PC Hardware & Environment: {pc_summary}\n"
            f"• Minion's Learned Memory of User:\n{facts_text}\n"
            f"• Custom Instructions / Context:\n{extra[:400]}\n"
        )
