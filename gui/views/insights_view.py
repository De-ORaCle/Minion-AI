"""
Minion AI — Work Insights & Strategic Project Memory Center.

A premier, front-facing command center that shows the user deep insights
the AI is actively deriving about their work, their active deliverables,
time-based progress horizons (Real-Time, Today, This Week, All-Time),
multi-perspective strategic improvement angles, interactive execution tracking,
and persistent insight memory of recommendations that have been worked on.
"""

import os
import re
import datetime
import logging
from typing import Dict, Any, List, Optional
import customtkinter as ctk

from config import THEME, get_font
from core.database import DatabaseManager
from core.context_manager import ContextManager
from core.project_intelligence import (
    detect_active_deliverable,
    generate_strategic_project_angles,
    generate_tool_optimizations,
    generate_actionable_milestones,
    activate_deliverable,
)

logger = logging.getLogger(__name__)


class WorkInsightsView(ctk.CTkFrame):
    """Front-facing command center for time-based AI work insights and executed insight memory."""

    def __init__(
        self,
        master,
        db_manager: DatabaseManager,
        context_manager: Optional[ContextManager] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.db = db_manager
        self.ctx = context_manager
        self.active_deliverable: Optional[Dict[str, Any]] = None
        self.user_domain = "general"
        self.current_scope = "realtime"  # 'realtime', 'today', 'week', 'alltime'
        self.scope_buttons: Dict[str, ctk.CTkButton] = {}

        self._build_ui()
        self.refresh_insights()

    def _build_ui(self) -> None:
        """Construct the visual components."""
        # Top Header Bar
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(20, 10))

        top_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_row.pack(fill="x")

        title_label = ctk.CTkLabel(
            top_row,
            text="Work Insights",
            font=get_font(size=24, weight="bold"),
            text_color=THEME["yellow_title"],
        )
        title_label.pack(side="left")

        # Top Right Controls: Refresh Button
        self.btn_refresh = ctk.CTkButton(
            top_row,
            text="⚡ Refresh Insights",
            command=self.refresh_insights,
            fg_color=THEME["denim_blue"],
            hover_color=THEME["denim_hover"],
            text_color="#ffffff",
            font=get_font(size=12, weight="bold"),
            height=34,
            corner_radius=8,
            cursor="hand2",
        )
        self.btn_refresh.pack(side="right")

        # Domain Badge & Time Scope Row
        sub_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        sub_row.pack(fill="x", pady=(6, 0))

        self.lbl_domain_badge = ctk.CTkLabel(
            sub_row,
            text="🎯 FOCUS DOMAIN: GENERAL",
            font=get_font(size=11, weight="bold"),
            text_color=THEME["yellow_text"],
            fg_color=THEME["yellow_tint"],
            corner_radius=6,
            padx=10,
            pady=3,
        )
        self.lbl_domain_badge.pack(side="left", padx=(0, 14))

        # Time Scope Segmented Selector
        scope_pill_box = ctk.CTkFrame(
            sub_row,
            fg_color=THEME["card_inner"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border"],
        )
        scope_pill_box.pack(side="left")

        scopes = [
            ("realtime", "⚡ Real-Time"),
            ("today", "📅 Today"),
            ("week", "🗓️ This Week"),
            ("alltime", "📈 All-Time"),
        ]

        for s_key, s_label in scopes:
            btn = ctk.CTkButton(
                scope_pill_box,
                text=s_label,
                command=lambda k=s_key: self._set_time_scope(k),
                font=get_font(size=11, weight="bold"),
                height=28,
                corner_radius=6,
                cursor="hand2",
                fg_color="transparent",
                text_color=THEME["text_secondary"],
                hover_color=THEME["card_hover"],
            )
            btn.pack(side="left", padx=2, pady=2)
            self.scope_buttons[s_key] = btn

        # Main Scrollable Content Container
        self.scroll_content = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
        )
        self.scroll_content.pack(fill="both", expand=True, padx=25, pady=(0, 20))

    def _set_time_scope(self, scope_key: str) -> None:
        """Handle user changing the time horizon filter."""
        self.current_scope = scope_key
        self.refresh_insights()

    def _update_scope_pill_styles(self) -> None:
        """Highlight the currently active time horizon pill."""
        for s_key, btn in self.scope_buttons.items():
            if s_key == self.current_scope:
                btn.configure(
                    fg_color=THEME["yellow_tint"],
                    text_color=THEME["yellow_title"],
                    hover_color=THEME["yellow_tint"],
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=THEME["text_secondary"],
                    hover_color=THEME["card_hover"],
                )

    def refresh_insights(self) -> None:
        """Analyze database telemetry for the selected time scope and regenerate all insight cards."""
        self._update_scope_pill_styles()

        # Clear existing dynamic cards
        for widget in self.scroll_content.winfo_children():
            widget.destroy()

        # 1. Resolve Focus Domain
        self.user_domain = "general"
        if self.db:
            self.user_domain = (self.db.get_setting("user_focus_domain", default="general") or "general").lower()
            try:
                profile = self.db.get_user_profile() or {}
                if profile.get("profession_role"):
                    self.user_domain = profile.get("profession_role", "").lower()
            except Exception:
                pass

        domain_display = self.user_domain.upper()
        self.lbl_domain_badge.configure(text=f"🎯 FOCUS DOMAIN: {domain_display}")

        # 2. Fetch Time-Scoped Activities from SQLite
        now = datetime.datetime.now()
        start_time_iso = None
        limit_count = 500

        if self.current_scope == "realtime":
            # Last 30 minutes or recent 30 activities
            start_time_iso = (now - datetime.timedelta(minutes=30)).isoformat()
            limit_count = 35
        elif self.current_scope == "today":
            start_time_iso = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            limit_count = 1000
        elif self.current_scope == "week":
            start_time_iso = (now - datetime.timedelta(days=7)).replace(hour=0, minute=0, second=0).isoformat()
            limit_count = 3000
        elif self.current_scope == "alltime":
            start_time_iso = None
            limit_count = 5000

        activities: List[Dict[str, Any]] = []
        if self.db:
            try:
                activities = self.db.get_activities(start_time=start_time_iso, limit=limit_count)
            except Exception as e:
                logger.debug(f"Error fetching activities for scope {self.current_scope}: {e}")

        # 3. Detect Active Deliverable
        self.active_deliverable = detect_active_deliverable(
            activities=activities[:25] if activities else None,
            domain=self.user_domain,
            project_hint="",
        )

        # 4. Generate Strategic Improvement Angles for this Time Horizon
        active_proj_name = "Core Software Application"
        active_cat = "Software & System Architecture"
        active_stack = ["Python", "React", "SQL"]

        d_clean = self.user_domain.lower()
        if any(k in d_clean for k in ["write", "writer", "writing", "author", "editorial"]):
            active_proj_name = "Editorial Manuscript & Narrative"
            active_cat = "Document & Manuscript Authoring"
            active_stack = ["Microsoft Word", "Editorial Draft"]
        elif any(k in d_clean for k in ["business", "finance", "analyst", "bank"]):
            active_proj_name = "Financial Model & Executive Strategy"
            active_cat = "Financial Modeling & Strategy"
            active_stack = ["Microsoft Excel", "PowerPoint", "Financial Model"]
        elif any(k in d_clean for k in ["design", "creative", "ui", "ux"]):
            active_proj_name = "Design System & Visual Canvas"
            active_cat = "UI/UX & Visual Design Canvas"
            active_stack = ["Figma", "Design Tokens", "Design System"]
        elif any(k in d_clean for k in ["research", "academic", "scholar"]):
            active_proj_name = "Literature & Evidence Review"
            active_cat = "Academic Literature & Systematic Review"
            active_stack = ["PDF Literature", "Research Study"]
        else:
            if activities:
                for act in activities:
                    title = act.get("window_title", "")
                    parts = [p.strip() for p in re.split(r"[-–—|•]", title) if len(p.strip()) > 2]
                    if len(parts) >= 2 and not any(k in parts[0].lower() for k in ["google chrome", "visual studio", "untitled"]):
                        active_proj_name = parts[0]
                        break

        strategic_angles = generate_strategic_project_angles(
            project_name=active_proj_name,
            category=active_cat,
            stack=active_stack,
            domain=self.user_domain,
            time_scope=self.current_scope,
        )

        tool_improvements = generate_tool_optimizations(active_stack, domain=self.user_domain)
        actionable_milestones = generate_actionable_milestones(active_proj_name)

        # 5. Load Insight Memory / Statuses from SQLite
        insight_statuses: Dict[str, Dict[str, Any]] = {}
        insight_history: List[Dict[str, Any]] = []
        if self.db:
            try:
                insight_statuses = self.db.get_insight_statuses(active_proj_name)
                insight_history = self.db.get_insight_history(limit=50)
            except Exception as e:
                logger.debug(f"Error fetching insight memory: {e}")

        # -----------------------------------------------------------------
        # SECTION 1: Time Horizon Metrics Strip
        # -----------------------------------------------------------------
        self._render_time_metrics_strip(activities, strategic_angles, insight_statuses)

        # -----------------------------------------------------------------
        # SECTION 2: Active Deliverable Hero Card
        # -----------------------------------------------------------------
        self._render_deliverable_hero(self.active_deliverable)

        # -----------------------------------------------------------------
        # SECTION 3: Multi-Perspective Strategic Improvement Angles
        # -----------------------------------------------------------------
        self._render_strategic_angles(strategic_angles, active_proj_name, insight_statuses)

        # -----------------------------------------------------------------
        # SECTION 4: Insights History & Executed Memory
        # -----------------------------------------------------------------
        self._render_insight_history_section(insight_history, active_proj_name)

        # -----------------------------------------------------------------
        # SECTION 5: Tool Stack Velocity & Workflow Accelerators
        # -----------------------------------------------------------------
        self._render_tool_accelerators(tool_improvements)

        # -----------------------------------------------------------------
        # SECTION 6: Actionable Project Milestones
        # -----------------------------------------------------------------
        self._render_actionable_milestones(actionable_milestones)

        # -----------------------------------------------------------------
        # SECTION 7: Screen Observation Stream
        # -----------------------------------------------------------------
        self._render_recent_insights_stream(activities)

    def _render_time_metrics_strip(
        self,
        activities: List[Dict[str, Any]],
        angles: List[Dict[str, Any]],
        insight_statuses: Dict[str, Dict[str, Any]],
    ) -> None:
        """Render studio-grade metric cards reflecting the chosen time scope."""
        strip_frame = ctk.CTkFrame(self.scroll_content, fg_color="transparent")
        strip_frame.pack(fill="x", pady=(4, 12))
        strip_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Calculate Focus / Deep Work Duration
        total_seconds = sum(
            a.get("duration_seconds", 0)
            for a in activities
            if a.get("category") in ("Work / Coding", "Deep Work", "Planning", "Learning / Research")
        )
        hours = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        if hours > 0:
            duration_text = f"{hours}h {mins}m"
        else:
            duration_text = f"{max(mins, 1)}m"

        # Calculate Average Productivity Score
        scores = [a.get("productivity_score", 0.0) for a in activities if a.get("productivity_score") is not None]
        avg_score = (sum(scores) / len(scores)) if scores else 0.85
        pct_score = int(min(100, max(20, (avg_score * 40 + 60))))

        # Calculate Executed Insights Ratio in this project
        total_angles = len(angles)
        worked_on_count = sum(
            1 for ang in angles
            if insight_statuses.get(ang.get("key", ""), {}).get("status") == "completed"
        )
        in_progress_count = sum(
            1 for ang in angles
            if insight_statuses.get(ang.get("key", ""), {}).get("status") == "in_progress"
        )

        scope_titles = {
            "realtime": "Current Window (30m)",
            "today": "Today's Workload",
            "week": "Past 7 Days",
            "alltime": "All-Time Aggregate",
        }
        scope_label = scope_titles.get(self.current_scope, "Active Window")

        # Metric cards data
        metrics = [
            {
                "icon": "⚡",
                "title": "Velocity Score",
                "val": f"{pct_score}%",
                "sub": f"{scope_label} • High Focus",
                "color": THEME["yellow_title"],
            },
            {
                "icon": "🕒",
                "title": "Deep Work Time",
                "val": duration_text,
                "sub": f"Tracked in {scope_label}",
                "color": THEME["denim_blue"],
            },
            {
                "icon": "🎯",
                "title": "Active Deliverable",
                "val": self.active_deliverable.get("title", "Active Workspace") if self.active_deliverable else "Primary Workspace",
                "sub": self.active_deliverable.get("status", "Active Sprints") if self.active_deliverable else "Ready for tracking",
                "color": "#16a34a",
            },
            {
                "icon": "✨",
                "title": "Insights Executed",
                "val": f"{worked_on_count} / {total_angles}",
                "sub": f"{in_progress_count} In Progress • Stored",
                "color": "#9333ea",
            },
        ]

        for idx, m in enumerate(metrics):
            card = ctk.CTkFrame(
                strip_frame,
                fg_color=THEME["card_bg"],
                border_width=1,
                border_color=THEME["border"],
                corner_radius=10,
            )
            card.grid(row=0, column=idx, padx=4, sticky="nsew")

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=14, pady=12)

            # Header row
            h_row = ctk.CTkFrame(inner, fg_color="transparent")
            h_row.pack(fill="x")

            lbl_title = ctk.CTkLabel(
                h_row,
                text=f"{m['icon']} {m['title']}",
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_secondary"],
            )
            lbl_title.pack(side="left")

            # Value
            lbl_val = ctk.CTkLabel(
                inner,
                text=m["val"],
                font=get_font(size=20, weight="bold"),
                text_color=m["color"],
                anchor="w",
            )
            lbl_val.pack(fill="x", pady=(4, 2))

            # Subtitle
            lbl_sub = ctk.CTkLabel(
                inner,
                text=m["sub"],
                font=get_font(size=10),
                text_color=THEME["text_muted"],
                anchor="w",
            )
            lbl_sub.pack(fill="x")

    def _render_deliverable_hero(self, deliv: Optional[Dict[str, Any]]) -> None:
        """Render the primary active deliverable hero banner."""
        if not deliv:
            return

        d_type = str(deliv.get("type", "")).lower()
        act_type = deliv.get("action_type", "focus")

        # Color theme tailored to craft
        if "web" in d_type or act_type == "url":
            b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#f0fdf4", "#86efac", "#166534", "#15803d", "#16a34a", "#15803d"
        elif "financial" in d_type or "spreadsheet" in d_type:
            b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#eff6ff", "#bfdbfe", "#1e40af", "#1d4ed8", "#2563eb", "#1d4ed8"
        elif "manuscript" in d_type or "document" in d_type or "authoring" in d_type:
            b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#fffbeb", "#fde68a", "#92400e", "#b45309", "#d97706", "#b45309"
        elif "design" in d_type or "canvas" in d_type:
            b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#faf5ff", "#e9d5ff", "#6b21a8", "#7e22ce", "#9333ea", "#7e22ce"
        elif "scholarly" in d_type or "literature" in d_type:
            b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#ecfeff", "#a5f3fc", "#155e75", "#0e7490", "#0891b2", "#0e7490"
        else:
            b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#f8fafc", "#cbd5e1", "#334155", "#475569", "#475569", "#334155"

        hero_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=b_bg,
            border_width=1,
            border_color=b_border,
            corner_radius=12,
        )
        hero_card.pack(fill="x", pady=(2, 14))

        hero_inner = ctk.CTkFrame(hero_card, fg_color="transparent")
        hero_inner.pack(fill="x", padx=20, pady=16)

        # Header tag
        tag_lbl = ctk.CTkLabel(
            hero_inner,
            text="PRIMARY ACTIVE WORK DELIVERABLE",
            font=get_font(size=10, weight="bold"),
            text_color=b_text,
        )
        tag_lbl.pack(anchor="w")

        # Title & Action row
        top_row = ctk.CTkFrame(hero_inner, fg_color="transparent")
        top_row.pack(fill="x", pady=(3, 6))

        lbl_title = ctk.CTkLabel(
            top_row,
            text=f"{deliv.get('icon', '📁')} {deliv.get('title')}",
            font=get_font(size=18, weight="bold"),
            text_color=b_text,
            anchor="w",
        )
        lbl_title.pack(side="left")

        btn_action = ctk.CTkButton(
            top_row,
            text=deliv.get("action_label", "⚡ Focus Deliverable"),
            font=get_font(size=12, weight="bold"),
            fg_color=btn_bg,
            hover_color=btn_hover,
            text_color="#ffffff",
            height=34,
            corner_radius=7,
            cursor="hand2",
            command=lambda d=deliv: activate_deliverable(d),
        )
        btn_action.pack(side="right")

        # Context summary
        lbl_summary = ctk.CTkLabel(
            hero_inner,
            text=f"Status: {deliv.get('status')}  •  {deliv.get('summary')}",
            font=get_font(size=12),
            text_color=b_sub,
            anchor="w",
            wraplength=850,
            justify="left",
        )
        lbl_summary.pack(fill="x")

    def _render_strategic_angles(
        self,
        angles: List[Dict[str, str]],
        project_name: str,
        insight_statuses: Dict[str, Dict[str, Any]],
    ) -> None:
        """Render multi-perspective strategic recommendations with interactive execution memory toggles."""
        scope_badges = {
            "realtime": "⚡ Real-Time Tactical",
            "today": "📅 Today's Sprint Focus",
            "week": "🗓️ Weekly Release Health",
            "alltime": "📈 Long-Term Scalability",
        }
        scope_badge = scope_badges.get(self.current_scope, "Strategic Angle")

        sec_hdr = ctk.CTkFrame(self.scroll_content, fg_color="transparent")
        sec_hdr.pack(fill="x", pady=(6, 8))

        lbl_sec = ctk.CTkLabel(
            sec_hdr,
            text=f"💡 Strategic Improvement Angles for {project_name}",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_sec.pack(side="left")

        lbl_scope_tag = ctk.CTkLabel(
            sec_hdr,
            text=scope_badge,
            font=get_font(size=11, weight="bold"),
            text_color=THEME["yellow_text"],
            fg_color=THEME["yellow_tint"],
            corner_radius=6,
            padx=8,
            pady=2,
        )
        lbl_scope_tag.pack(side="right")

        angles_grid = ctk.CTkFrame(self.scroll_content, fg_color="transparent")
        angles_grid.pack(fill="x", pady=(0, 14))
        angles_grid.grid_columnconfigure((0, 1), weight=1)

        for i, ang in enumerate(angles):
            r = i // 2
            c = i % 2

            card = ctk.CTkFrame(
                angles_grid,
                fg_color=THEME["card_bg"],
                border_width=1,
                border_color=THEME["border"],
                corner_radius=10,
            )
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

            card_inner = ctk.CTkFrame(card, fg_color="transparent")
            card_inner.pack(fill="both", expand=True, padx=16, pady=14)

            # Retrieve memory status for this angle
            ang_key = ang.get("key") or f"{project_name}::{ang.get('summary', ang.get('angle'))}"
            mem_record = insight_statuses.get(ang_key, {})
            status = mem_record.get("status", "pending")
            completed_at = mem_record.get("completed_at", "")

            # Header row with title & status button
            h_row = ctk.CTkFrame(card_inner, fg_color="transparent")
            h_row.pack(fill="x", pady=(0, 4))

            lbl_ang_name = ctk.CTkLabel(
                h_row,
                text=ang.get("angle", "Strategic Angle"),
                font=get_font(size=13, weight="bold"),
                text_color=THEME["yellow_title"],
                anchor="w",
            )
            lbl_ang_name.pack(side="left", fill="x", expand=True)

            # Interactive Status Toggle Button
            if status == "completed":
                comp_date = completed_at[:10] if completed_at else "Done"
                btn_status = ctk.CTkButton(
                    h_row,
                    text=f"✅ Worked On ({comp_date})",
                    font=get_font(size=10, weight="bold"),
                    fg_color="#dcfce7",
                    hover_color="#bbf7d0",
                    text_color="#166534",
                    border_width=1,
                    border_color="#86efac",
                    height=24,
                    corner_radius=6,
                    cursor="hand2",
                    command=lambda a=ang: self._cycle_insight_status(a, project_name),
                )
            elif status == "in_progress":
                btn_status = ctk.CTkButton(
                    h_row,
                    text="⚡ In Progress",
                    font=get_font(size=10, weight="bold"),
                    fg_color="#fef3c7",
                    hover_color="#fde68a",
                    text_color="#b45309",
                    border_width=1,
                    border_color="#fde047",
                    height=24,
                    corner_radius=6,
                    cursor="hand2",
                    command=lambda a=ang: self._cycle_insight_status(a, project_name),
                )
            else:
                btn_status = ctk.CTkButton(
                    h_row,
                    text="○ Mark In Progress",
                    font=get_font(size=10, weight="bold"),
                    fg_color=THEME["card_inner"],
                    hover_color=THEME["card_hover"],
                    text_color=THEME["text_secondary"],
                    border_width=1,
                    border_color=THEME["input_border"],
                    height=24,
                    corner_radius=6,
                    cursor="hand2",
                    command=lambda a=ang: self._cycle_insight_status(a, project_name),
                )
            btn_status.pack(side="right")

            # Summary takeaway
            lbl_ang_sum = ctk.CTkLabel(
                card_inner,
                text=ang.get("summary", ""),
                font=get_font(size=11, weight="bold"),
                text_color=THEME["denim_blue"],
                anchor="w",
            )
            lbl_ang_sum.pack(fill="x", pady=(0, 6))

            # Full recommendation
            lbl_ang_rec = ctk.CTkLabel(
                card_inner,
                text=ang.get("recommendation", ""),
                font=get_font(size=11),
                text_color=THEME["text_secondary"],
                anchor="w",
                wraplength=390,
                justify="left",
            )
            lbl_ang_rec.pack(fill="x")

    def _cycle_insight_status(self, angle: Dict[str, str], project_name: str) -> None:
        """Cycle insight status through pending -> in_progress -> completed -> pending and persist."""
        if not self.db:
            return

        ang_key = angle.get("key") or f"{project_name}::{angle.get('summary', angle.get('angle'))}"
        current_statuses = self.db.get_insight_statuses(project_name)
        current = current_statuses.get(ang_key, {}).get("status", "pending")

        if current == "pending":
            next_status = "in_progress"
        elif current == "in_progress":
            next_status = "completed"
        else:
            next_status = "pending"

        self.db.save_insight_status(
            insight_key=ang_key,
            project_name=project_name,
            angle_title=angle.get("angle", ""),
            summary=angle.get("summary", ""),
            recommendation=angle.get("recommendation", ""),
            status=next_status,
            time_scope=self.current_scope,
        )

        # Refresh immediately to update metric strip, badges, and history log
        self.refresh_insights()

    def _render_insight_history_section(
        self,
        history: List[Dict[str, Any]],
        project_name: str,
    ) -> None:
        """Render dedicated section showcasing executed insights and historical memory."""
        lbl_sec = ctk.CTkLabel(
            self.scroll_content,
            text=f"📜 Insights Memory & Execution History ({len(history)} Stored)",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_sec.pack(fill="x", pady=(10, 8))

        history_box = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            border_width=1,
            border_color=THEME["border"],
            corner_radius=10,
        )
        history_box.pack(fill="x", pady=(0, 14))

        hb_inner = ctk.CTkFrame(history_box, fg_color="transparent")
        hb_inner.pack(fill="x", padx=16, pady=14)

        if not history:
            lbl_empty = ctk.CTkLabel(
                hb_inner,
                text="No insights executed yet. Click 'Mark In Progress' or 'Worked On' on any strategic angle above to record your improvements in permanent memory.",
                font=get_font(size=12),
                text_color=THEME["text_muted"],
            )
            lbl_empty.pack(pady=12)
            return

        for item in history[:6]:
            row = ctk.CTkFrame(
                hb_inner,
                fg_color=THEME["card_inner"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            row.pack(fill="x", pady=4)

            ri = ctk.CTkFrame(row, fg_color="transparent")
            ri.pack(fill="x", padx=14, pady=10)

            # Left Info
            left_info = ctk.CTkFrame(ri, fg_color="transparent")
            left_info.pack(side="left", fill="x", expand=True)

            status = item.get("status", "pending")
            status_text = "✅ Worked On" if status == "completed" else ("⚡ In Progress" if status == "in_progress" else "○ Open")
            status_color = "#166534" if status == "completed" else ("#b45309" if status == "in_progress" else THEME["text_secondary"])
            status_bg = "#dcfce7" if status == "completed" else ("#fef3c7" if status == "in_progress" else THEME["card_bg"])

            h_line = ctk.CTkFrame(left_info, fg_color="transparent")
            h_line.pack(fill="x")

            lbl_h_title = ctk.CTkLabel(
                h_line,
                text=item.get("angle_title", "Strategic Insight"),
                font=get_font(size=12, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_h_title.pack(side="left")

            lbl_h_status = ctk.CTkLabel(
                h_line,
                text=status_text,
                font=get_font(size=10, weight="bold"),
                text_color=status_color,
                fg_color=status_bg,
                corner_radius=5,
                padx=6,
                pady=1,
            )
            lbl_h_status.pack(side="left", padx=8)

            date_str = item.get("updated_at", "")[:16].replace("T", " ")
            lbl_h_date = ctk.CTkLabel(
                h_line,
                text=f"Updated: {date_str}",
                font=get_font(size=10),
                text_color=THEME["text_muted"],
            )
            lbl_h_date.pack(side="right")

            lbl_h_sum = ctk.CTkLabel(
                left_info,
                text=f"{item.get('project_name', '')} • {item.get('summary', '')}",
                font=get_font(size=11),
                text_color=THEME["denim_blue"],
                anchor="w",
            )
            lbl_h_sum.pack(fill="x", pady=(2, 0))

    def _render_tool_accelerators(self, tools: List[Dict[str, Any]]) -> None:
        """Render actionable velocity shortcuts and tool mastery accelerators."""
        if not tools:
            return

        lbl_sec = ctk.CTkLabel(
            self.scroll_content,
            text="🚀 Tool Velocity & Workflow Accelerators",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_sec.pack(fill="x", pady=(10, 8))

        tool_box = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            border_width=1,
            border_color=THEME["border"],
            corner_radius=10,
        )
        tool_box.pack(fill="x", pady=(0, 14))

        tb_inner = ctk.CTkFrame(tool_box, fg_color="transparent")
        tb_inner.pack(fill="x", padx=16, pady=14)

        for t in tools:
            t_row = ctk.CTkFrame(
                tb_inner,
                fg_color=THEME["card_inner"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            t_row.pack(fill="x", pady=4)

            tr_inner = ctk.CTkFrame(t_row, fg_color="transparent")
            tr_inner.pack(fill="x", padx=14, pady=10)

            lbl_t_name = ctk.CTkLabel(
                tr_inner,
                text=f"{t.get('icon', '⚡')} {t.get('tool')}",
                font=get_font(size=12, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_t_name.pack(fill="x", pady=(0, 2))

            lbl_t_tip = ctk.CTkLabel(
                tr_inner,
                text=t.get("tip", ""),
                font=get_font(size=11),
                text_color=THEME["text_secondary"],
                anchor="w",
                wraplength=830,
                justify="left",
            )
            lbl_t_tip.pack(fill="x")

    def _render_actionable_milestones(self, milestones: List[Dict[str, str]]) -> None:
        """Render step-by-step milestone execution checklist."""
        if not milestones:
            return

        lbl_sec = ctk.CTkLabel(
            self.scroll_content,
            text="🎯 Actionable Strategic Milestones Checklist",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_sec.pack(fill="x", pady=(10, 8))

        ms_box = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            border_width=1,
            border_color=THEME["border"],
            corner_radius=10,
        )
        ms_box.pack(fill="x", pady=(0, 14))

        mb_inner = ctk.CTkFrame(ms_box, fg_color="transparent")
        mb_inner.pack(fill="x", padx=16, pady=14)

        for ms in milestones:
            row = ctk.CTkFrame(mb_inner, fg_color="transparent")
            row.pack(fill="x", pady=5)

            chk = ctk.CTkCheckBox(
                row,
                text="",
                width=24,
                checkbox_height=18,
                checkbox_width=18,
                corner_radius=4,
                border_width=1,
                border_color=THEME["input_border"],
                fg_color=THEME["denim_blue"],
                hover_color=THEME["denim_hover"],
            )
            chk.pack(side="left", padx=(0, 10))

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)

            ms_text = ms if isinstance(ms, str) else str(ms.get("milestone", ""))
            lbl_m_title = ctk.CTkLabel(
                info,
                text=ms_text,
                font=get_font(size=12, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
                wraplength=800,
                justify="left",
            )
            lbl_m_title.pack(anchor="w")

    def _render_recent_insights_stream(self, activities: List[Dict[str, Any]]) -> None:
        """Render recent high-level screen observation insights derived by Minion."""
        lbl_sec = ctk.CTkLabel(
            self.scroll_content,
            text="👁️ Screen Observation & Activity Stream",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_sec.pack(fill="x", pady=(10, 8))

        stream_box = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            border_width=1,
            border_color=THEME["border"],
            corner_radius=10,
        )
        stream_box.pack(fill="x", pady=(0, 20))

        sb_inner = ctk.CTkFrame(stream_box, fg_color="transparent")
        sb_inner.pack(fill="x", padx=16, pady=14)

        if not activities:
            lbl_empty = ctk.CTkLabel(
                sb_inner,
                text="No recent observations in this time horizon. Click 'Start Tracking' in Activity Watcher to log snapshots.",
                font=get_font(size=12),
                text_color=THEME["text_muted"],
            )
            lbl_empty.pack(pady=10)
            return

        for act in activities[:8]:
            row = ctk.CTkFrame(
                sb_inner,
                fg_color=THEME["card_inner"],
                corner_radius=6,
                border_width=1,
                border_color=THEME["border"],
            )
            row.pack(fill="x", pady=3)

            ri = ctk.CTkFrame(row, fg_color="transparent")
            ri.pack(fill="x", padx=12, pady=6)

            time_str = act.get("timestamp", "")[-8:]
            app = act.get("app_name", "Unknown")
            action = act.get("action_verb") or f"Active in {app}"
            title = act.get("window_title", "")
            title_clean = title[:60] + "..." if len(title) > 60 else title

            lbl_time = ctk.CTkLabel(
                ri,
                text=time_str,
                font=get_font(size=11),
                text_color=THEME["text_muted"],
                width=65,
            )
            lbl_time.pack(side="left")

            lbl_act = ctk.CTkLabel(
                ri,
                text=f"🎯 {action} • {title_clean}",
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_act.pack(side="left", fill="x", expand=True, padx=6)
