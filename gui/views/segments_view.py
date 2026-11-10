"""
Work Sprints, Deep Insights & Context Timeline View for Minion.

This view elevates raw window transitions into goal-oriented "Sprints":
- Groups activities into 20-90m cohesive focus blocks.
- Compares snapshots to identify what the user achieved (milestones, files touched, research conducted).
- Computes Flow State & Focus Velocity scores.
- Synthesizes deep behavioural insights, cognitive friction loops, and accomplishments.
- Preserves raw micro-clustering for granular inspection.
"""

import json
import threading
from typing import Dict, Any, List, Optional
import customtkinter as ctk

from core.database import DatabaseManager
from core.segmenter import ContextSegmenter
from core.reporter import ProductivityReporter
from core.sprint_engine import SprintEngine
from config import THEME, CATEGORY_CONFIG, get_font


class SegmentsView(ctk.CTkFrame):
    """View rendering goal-oriented Sprints, Milestones, and Context Segments."""

    INTERVAL_OPTIONS = ["Today", "Yesterday", "Past 4 Hours", "Past 7 Days"]

    def __init__(
        self,
        master,
        db_manager: DatabaseManager,
        segmenter: ContextSegmenter,
        reporter: ProductivityReporter,
        sprint_engine: Optional[SprintEngine] = None,
        on_share_segment=None,
        **kwargs,
    ):
        """
        Initialize the Sprints & Insights View.
        """
        super().__init__(master, fg_color="transparent", **kwargs)

        self.db = db_manager
        self.segmenter = segmenter
        self.reporter = reporter
        self.sprint_engine = sprint_engine or SprintEngine(self.db)
        self.on_share_segment = on_share_segment

        self.current_interval = "Today"
        self.active_tab = "sprints"  # "sprints" or "segments"

        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        """Construct visual elements."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(20, 10))

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")

        title_label = ctk.CTkLabel(
            title_box,
            text="⚡ Work Sprints & Flow",
            font=get_font(size=24, weight="bold"),
            text_color=THEME["yellow_title"],
        )
        title_label.pack(anchor="w")

        sub_label = ctk.CTkLabel(
            title_box,
            text="Bello! Automatic sprint milestones, focus flow index, and context clusters",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
        )
        sub_label.pack(anchor="w", pady=(2, 0))

        # Controls Bar
        ctrl_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        ctrl_box.pack(side="right")

        self.combo_interval = ctk.CTkComboBox(
            ctrl_box,
            values=self.INTERVAL_OPTIONS,
            command=self._on_interval_changed,
            width=135,
            height=36,
            corner_radius=8,
            border_width=1,
            border_color=THEME["input_border"],
            fg_color=THEME["card_bg"],
            button_color=THEME["card_inner"],
            button_hover_color=THEME["border"],
            dropdown_fg_color=THEME["card_bg"],
            dropdown_hover_color=THEME["yellow_tint"],
            dropdown_text_color=THEME["text_primary"],
            text_color=THEME["text_primary"],
            font=get_font(size=13),
        )
        self.combo_interval.set(self.current_interval)
        self.combo_interval.pack(side="left", padx=(0, 10))

        self.btn_action = ctk.CTkButton(
            ctrl_box,
            text="⚡ Detect Sprints",
            command=self._generate_sprints_action,
            fg_color=THEME["denim_blue"],
            hover_color=THEME["denim_hover"],
            text_color="#ffffff",
            width=140,
            height=36,
            corner_radius=8,
            font=get_font(size=12, weight="bold"),
            cursor="hand2",
        )
        self.btn_action.pack(side="left")

        # Tab Navigation Switcher (Sprints vs Raw Segments)
        tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        tab_bar.pack(fill="x", padx=25, pady=(8, 4))

        self.btn_tab_sprints = ctk.CTkButton(
            tab_bar,
            text="⚡ Goal Sprints & Milestones",
            command=lambda: self._switch_tab("sprints"),
            fg_color=THEME["denim_blue"],
            hover_color=THEME["denim_hover"],
            text_color="#ffffff",
            height=34,
            corner_radius=8,
            font=get_font(size=12, weight="bold"),
            cursor="hand2",
        )
        self.btn_tab_sprints.pack(side="left", padx=(0, 8))

        self.btn_tab_segments = ctk.CTkButton(
            tab_bar,
            text="🧩 Raw Work Clusters",
            command=lambda: self._switch_tab("segments"),
            fg_color=THEME["card_bg"],
            hover_color=THEME["card_hover"],
            text_color=THEME["text_secondary"],
            border_width=1,
            border_color=THEME["border"],
            height=34,
            corner_radius=8,
            font=get_font(size=12, weight="bold"),
            cursor="hand2",
        )
        self.btn_tab_segments.pack(side="left")

        # Scrollable Content Container
        self.scroll_content = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
        )
        self.scroll_content.pack(fill="both", expand=True, padx=25, pady=(8, 20))

    def _switch_tab(self, tab: str) -> None:
        """Switch between Sprints view and Raw Segments view."""
        self.active_tab = tab
        if tab == "sprints":
            self.btn_tab_sprints.configure(
                fg_color=THEME["denim_blue"],
                hover_color=THEME["denim_hover"],
                text_color="#ffffff",
                border_width=0,
            )
            self.btn_tab_segments.configure(
                fg_color=THEME["card_bg"],
                hover_color=THEME["card_hover"],
                text_color=THEME["text_secondary"],
                border_width=1,
                border_color=THEME["border"],
            )
            self.btn_action.configure(text="⚡ Detect Sprints")
        else:
            self.btn_tab_sprints.configure(
                fg_color=THEME["card_bg"],
                hover_color=THEME["card_hover"],
                text_color=THEME["text_secondary"],
                border_width=1,
                border_color=THEME["border"],
            )
            self.btn_tab_segments.configure(
                fg_color=THEME["denim_blue"],
                hover_color=THEME["denim_hover"],
                text_color="#ffffff",
                border_width=0,
            )
            self.btn_action.configure(text="⟳ Cluster Sessions")

        self.refresh_data()

    def _on_interval_changed(self, choice: str) -> None:
        """Handle interval change."""
        self.current_interval = choice
        self.refresh_data()

    def _generate_sprints_action(self) -> None:
        """Trigger explicit sprint detection / clustering."""
        self.btn_action.configure(state="disabled", text="⏳ Processing...")
        start_iso, end_iso = self.reporter.get_time_interval_bounds(self.current_interval)

        def _worker():
            if self.active_tab == "sprints":
                self.sprint_engine.generate_sprints(start_iso, end_iso, save_to_db=True)
            self.after(0, self._on_action_done)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_action_done(self) -> None:
        """Re-enable action button and refresh view."""
        orig_text = "⚡ Detect Sprints" if self.active_tab == "sprints" else "⟳ Cluster Sessions"
        self.btn_action.configure(state="normal", text=orig_text)
        self.refresh_data()

    def refresh_data(self) -> None:
        """Reload and render current tab's items."""
        if self.active_tab == "sprints":
            self._render_sprints_view()
        else:
            self._render_segments_view()

    # -------------------------------------------------------------
    # Render Sprints View
    # -------------------------------------------------------------
    def _render_sprints_view(self) -> None:
        """Render high-level goal-oriented focus sprints."""
        for child in self.scroll_content.winfo_children():
            child.destroy()

        start_iso, end_iso = self.reporter.get_time_interval_bounds(self.current_interval)
        sprints = self.db.get_sprints(start_time=start_iso, end_time=end_iso)

        # If no saved sprints exist yet for interval, auto-generate them
        if not sprints:
            sprints = self.sprint_engine.generate_sprints(start_iso, end_iso, save_to_db=True)

        if not sprints:
            empty_card = ctk.CTkFrame(
                self.scroll_content,
                fg_color=THEME["card_bg"],
                corner_radius=12,
                border_width=1,
                border_color=THEME["border"],
            )
            empty_card.pack(fill="x", pady=20)

            lbl = ctk.CTkLabel(
                empty_card,
                text="No focus sprints detected for this interval yet.\nClick '⚡ Detect Sprints' after tracking screen activity to discover deep achievements.",
                font=get_font(size=14),
                text_color=THEME["text_secondary"],
                justify="center",
            )
            lbl.pack(pady=40)
            return

        for sprint in sprints:
            self._render_sprint_card(sprint)

    def _render_sprint_card(self, sprint: Dict[str, Any]) -> None:
        """Render a rich, comprehensive Sprint card."""
        card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        card.pack(fill="x", pady=8)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=18)

        # Top Bar: Sprint Name + Flow Score Badge + Time Info
        top_bar = ctk.CTkFrame(inner, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 6))

        flow_score = float(sprint.get("focus_score", 0.0))
        flow_color = "#059669" if flow_score >= 80 else ("#d97706" if flow_score >= 50 else "#ea580c")

        badge_flow = ctk.CTkLabel(
            top_bar,
            text=f"⚡ {int(flow_score)}% FLOW",
            font=get_font(size=11, weight="bold"),
            text_color="#ffffff",
            fg_color=flow_color,
            corner_radius=4,
            padx=8,
            pady=2,
        )
        badge_flow.pack(side="left")

        # Time range & Duration
        start_str = sprint.get("start_time", "")[11:16] if len(sprint.get("start_time", "")) >= 16 else sprint.get("start_time", "")
        end_str = sprint.get("end_time", "")[11:16] if len(sprint.get("end_time", "")) >= 16 else sprint.get("end_time", "")
        dur_mins = sprint.get("duration_seconds", 0) // 60
        dur_str = f"{dur_mins}m" if dur_mins > 0 else f"{sprint.get('duration_seconds', 0)}s"

        time_lbl = ctk.CTkLabel(
            top_bar,
            text=f"🕒 {start_str} - {end_str}  ({dur_str})",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_secondary"],
        )
        time_lbl.pack(side="left", padx=10)

        # Sprint Name
        name_lbl = ctk.CTkLabel(
            inner,
            text=sprint.get("sprint_name", "Focus Sprint"),
            font=get_font(size=17, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        name_lbl.pack(fill="x", pady=(4, 2))

        # Objective
        obj_lbl = ctk.CTkLabel(
            inner,
            text=f"🎯 Objective: {sprint.get('objective', 'Task execution')}",
            font=get_font(size=13, weight="bold"),
            text_color=THEME["text_secondary"],
            anchor="w",
        )
        obj_lbl.pack(fill="x", pady=(0, 8))

        # 1. Chronological Milestones Progression
        try:
            milestones = json.loads(sprint.get("milestones_json", "[]"))
        except Exception:
            milestones = []

        if milestones:
            ms_box = ctk.CTkFrame(
                inner,
                fg_color=THEME["card_inner"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            ms_box.pack(fill="x", pady=6)

            ms_inner = ctk.CTkFrame(ms_box, fg_color="transparent")
            ms_inner.pack(fill="x", padx=14, pady=10)

            lbl_ms_title = ctk.CTkLabel(
                ms_inner,
                text="📈 SPRINT PROGRESSION TIMELINE",
                font=get_font(size=11, weight="bold"),
                text_color=THEME["denim_blue"],
                anchor="w",
            )
            lbl_ms_title.pack(fill="x", pady=(0, 4))

            for m in milestones:
                row = ctk.CTkFrame(ms_inner, fg_color="transparent")
                row.pack(fill="x", pady=2)

                t_lbl = ctk.CTkLabel(
                    row,
                    text=f"• {m.get('time', '')}",
                    font=get_font(size=12, weight="bold"),
                    text_color=THEME["text_secondary"],
                    width=60,
                    anchor="w",
                )
                t_lbl.pack(side="left")

                phase_lbl = ctk.CTkLabel(
                    row,
                    text=f"[{m.get('phase', '')}]",
                    font=get_font(size=11, weight="bold"),
                    text_color=THEME["yellow_title"],
                    width=130,
                    anchor="w",
                )
                phase_lbl.pack(side="left")

                act_lbl = ctk.CTkLabel(
                    row,
                    text=f"{m.get('action', '')} ({m.get('tool', '')})",
                    font=get_font(size=12),
                    text_color=THEME["text_primary"],
                    anchor="w",
                )
                act_lbl.pack(side="left", fill="x", expand=True)

        # 2. Concrete Achievements
        try:
            achievements = json.loads(sprint.get("achievements_json", "[]"))
        except Exception:
            achievements = []

        if achievements:
            ach_box = ctk.CTkFrame(inner, fg_color="transparent")
            ach_box.pack(fill="x", pady=6)

            lbl_ach_title = ctk.CTkLabel(
                ach_box,
                text="🏆 Key Accomplishments:",
                font=get_font(size=12, weight="bold"),
                text_color="#059669",
                anchor="w",
            )
            lbl_ach_title.pack(fill="x", pady=(2, 2))

            for ach in achievements:
                ach_row = ctk.CTkLabel(
                    ach_box,
                    text=f"✓  {ach}",
                    font=get_font(size=12),
                    text_color=THEME["text_primary"],
                    anchor="w",
                    justify="left",
                    wraplength=700,
                )
                ach_row.pack(fill="x", pady=1)

        # 3. Files Touched Tags
        try:
            files = json.loads(sprint.get("files_touched_json", "[]"))
        except Exception:
            files = []

        if files:
            files_row = ctk.CTkFrame(inner, fg_color="transparent")
            files_row.pack(fill="x", pady=(6, 2))

            f_title = ctk.CTkLabel(
                files_row,
                text="Files Touched:",
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_secondary"],
            )
            f_title.pack(side="left", padx=(0, 6))

            for f in files[:5]:
                f_pill = ctk.CTkLabel(
                    files_row,
                    text=f,
                    font=get_font(size=11, weight="bold"),
                    text_color=THEME["text_primary"],
                    fg_color=THEME["card_inner"],
                    corner_radius=4,
                    padx=7,
                    pady=2,
                )
                f_pill.pack(side="left", padx=3)

        # 4. Behavioral Insight Card
        ai_insight = sprint.get("ai_insight", "")
        if ai_insight:
            insight_box = ctk.CTkFrame(
                inner,
                fg_color=THEME["card_inner"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            insight_box.pack(fill="x", pady=(8, 4))

            insight_lbl = ctk.CTkLabel(
                insight_box,
                text=f"💡 Minion Behavioral Insight:\n{ai_insight}",
                font=get_font(size=12),
                text_color=THEME["text_primary"],
                anchor="w",
                justify="left",
                wraplength=700,
            )
            insight_lbl.pack(fill="x", padx=12, pady=8)

        # 5. Friction Points Alert
        friction = sprint.get("friction_points", "")
        if friction and friction != "Seamless flow with zero notable roadblocks":
            frict_lbl = ctk.CTkLabel(
                inner,
                text=f"⚠️ Cognitive Friction: {friction}",
                font=get_font(size=11, weight="bold"),
                text_color="#dc2626",
                anchor="w",
            )
            frict_lbl.pack(fill="x", pady=(4, 0))

    # -------------------------------------------------------------
    # Render Raw Segments View (Legacy Clustering)
    # -------------------------------------------------------------
    def _render_segments_view(self) -> None:
        """Render raw cluster segments."""
        for child in self.scroll_content.winfo_children():
            child.destroy()

        start_iso, end_iso = self.reporter.get_time_interval_bounds(self.current_interval)
        activities = self.db.get_activities(start_iso, end_iso, limit=5000)

        if not activities:
            empty_card = ctk.CTkFrame(
                self.scroll_content,
                fg_color=THEME["card_bg"],
                corner_radius=12,
                border_width=1,
                border_color=THEME["border"],
            )
            empty_card.pack(fill="x", pady=20)

            lbl = ctk.CTkLabel(
                empty_card,
                text="No raw activities tracked for this interval.\nClick 'Start Tracking' on the Activity Watcher to log windows.",
                font=get_font(size=14),
                text_color=THEME["text_secondary"],
                justify="center",
            )
            lbl.pack(pady=40)
            return

        segments = self.segmenter.segment_activities(activities)
        for seg in segments:
            self._render_segment_card(seg)

    def _render_segment_card(self, seg: Dict[str, Any]) -> None:
        """Build an individual work session card."""
        card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        card.pack(fill="x", pady=7)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 6))

        cat = seg.get("primary_category", "Work / Coding")
        color = CATEGORY_CONFIG.get(cat, {}).get("color", "#059669")

        cat_badge = ctk.CTkLabel(
            top_row,
            text=cat,
            font=get_font(size=11, weight="bold"),
            text_color="#ffffff",
            fg_color=color,
            corner_radius=4,
            padx=8,
            pady=2,
        )
        cat_badge.pack(side="left")

        start_str = seg["start_time"][11:16] if len(seg["start_time"]) >= 16 else seg["start_time"]
        end_str = seg["end_time"][11:16] if len(seg["end_time"]) >= 16 else seg["end_time"]
        mins = seg["duration_seconds"] // 60
        secs = seg["duration_seconds"] % 60
        dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        time_lbl = ctk.CTkLabel(
            top_row,
            text=f"🕒 {start_str} - {end_str}  ({dur_str})",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_secondary"],
        )
        time_lbl.pack(side="left", padx=12)

        title_lbl = ctk.CTkLabel(
            inner,
            text=seg.get("context_title", "Work Session"),
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        title_lbl.pack(fill="x", pady=(4, 4))

        summary_lbl = ctk.CTkLabel(
            inner,
            text=seg.get("summary", ""),
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
            anchor="w",
            wraplength=720,
            justify="left",
        )
        summary_lbl.pack(fill="x", pady=(0, 4))
