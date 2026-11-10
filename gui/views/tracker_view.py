"""
Tracker & Live Monitor View for ProductivityCheck.

This view provides the primary control interface for the user:
1. Start/Stop screen tracking toggle.
2. Dynamic polling interval selection (3s, 5s, 10s, 15s, 30s, 60s).
3. Live status card showing the current foreground application, window title, and category badge.
4. Real-time chronological activity feed showing recent snapshots.

Architectural Rationale:
- Thread-safe UI updates: The monitor runs in a separate thread. UI updates are scheduled
  via `widget.after()` to guarantee safety on the Tkinter mainloop.
- Responsive layout: Adapts cleanly to varying window dimensions.
"""

import datetime
from typing import Dict, Any, Callable
import customtkinter as ctk

from config import THEME, SUPPORTED_INTERVALS, DEFAULT_POLL_INTERVAL, CATEGORY_CONFIG, get_font
from core.project_intelligence import open_local_server, activate_deliverable, detect_active_deliverable, detect_active_local_server
from core.activity_correlator import ActivityCorrelator


class TrackerView(ctk.CTkFrame):
    """View presenting real-time tracking controls, active window inspection, and activity feed."""

    def __init__(
        self,
        master,
        on_toggle_tracking: Callable[[bool], None],
        on_change_interval: Callable[[int], None],
        db_manager=None,
        **kwargs,
    ):
        """
        Initialize the Tracker View.

        Args:
            master: Parent container frame.
            on_toggle_tracking: Callback receiving bool (True to start, False to stop).
            on_change_interval: Callback receiving new interval integer in seconds.
            db_manager: Optional DatabaseManager to restore persistent tracking history.
        """
        super().__init__(master, fg_color="transparent", **kwargs)

        self.on_toggle_tracking = on_toggle_tracking
        self.on_change_interval = on_change_interval
        self.db = db_manager
        self.is_tracking = False

        self._build_ui()
        self._load_persisted_history()

    def _build_ui(self) -> None:
        """Construct the visual components."""
        # View Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(20, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="Activity Watcher",
            font=get_font(size=24, weight="bold"),
            text_color=THEME["yellow_title"],
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Bello! Real-time on-screen focus monitoring and activity telemetry",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

        # Control Panel Card
        control_card = ctk.CTkFrame(
            self,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        control_card.pack(fill="x", padx=25, pady=10)

        ctrl_inner = ctk.CTkFrame(control_card, fg_color="transparent")
        ctrl_inner.pack(fill="x", padx=20, pady=18)

        # Left controls: Toggle button & Status badge
        left_ctrl = ctk.CTkFrame(ctrl_inner, fg_color="transparent")
        left_ctrl.pack(side="left", fill="y")

        self.btn_toggle = ctk.CTkButton(
            left_ctrl,
            text="▶ Start Tracking",
            command=self._handle_toggle,
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            font=get_font(size=14, weight="bold"),
            height=40,
            width=160,
            corner_radius=8,
            cursor="hand2",
        )
        self.btn_toggle.pack(side="left", padx=(0, 15))

        self.status_badge = ctk.CTkLabel(
            left_ctrl,
            text="○ MINION RESTING",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_secondary"],
            fg_color=THEME["card_inner"],
            corner_radius=6,
            padx=12,
            pady=6,
        )
        self.status_badge.pack(side="left")

        # Right controls: Interval selector
        right_ctrl = ctk.CTkFrame(ctrl_inner, fg_color="transparent")
        right_ctrl.pack(side="right", fill="y")

        interval_label = ctk.CTkLabel(
            right_ctrl,
            text="Interval:",
            font=get_font(size=13, weight="bold"),
            text_color=THEME["text_primary"],
        )
        interval_label.pack(side="left", padx=(0, 8))

        self.interval_combo = ctk.CTkComboBox(
            right_ctrl,
            values=[f"{sec} seconds" for sec in SUPPORTED_INTERVALS],
            command=self._handle_interval_change,
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
        self.interval_combo.set(f"{DEFAULT_POLL_INTERVAL} seconds")
        self.interval_combo.pack(side="left")

        # Active Window Live Card
        self.active_card = ctk.CTkFrame(
            self,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        self.active_card.pack(fill="x", padx=25, pady=10)

        active_inner = ctk.CTkFrame(self.active_card, fg_color="transparent")
        active_inner.pack(fill="x", padx=20, pady=18)

        active_header = ctk.CTkFrame(active_inner, fg_color="transparent")
        active_header.pack(fill="x", pady=(0, 6))

        live_tag = ctk.CTkLabel(
            active_header,
            text="CURRENT ACTIVE WINDOW",
            font=get_font(size=11, weight="bold"),
            text_color=THEME["denim_blue"],
        )
        live_tag.pack(side="left")

        self.category_badge = ctk.CTkLabel(
            active_header,
            text="Ready",
            font=get_font(size=11, weight="bold"),
            text_color="#ffffff",
            fg_color=THEME["card_inner"],
            corner_radius=6,
            padx=10,
            pady=3,
        )
        self.category_badge.pack(side="right")

        self.sphere_badge = ctk.CTkLabel(
            active_header,
            text="💼 Sphere: Ready",
            font=get_font(size=11, weight="bold"),
            text_color="#ffffff",
            fg_color="#2563eb",
            corner_radius=6,
            padx=10,
            pady=3,
        )
        self.sphere_badge.pack(side="right", padx=(0, 6))

        self.lbl_app_name = ctk.CTkLabel(
            active_inner,
            text="Tracker Inactive",
            font=get_font(size=20, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        self.lbl_app_name.pack(fill="x", pady=(2, 2))

        self.lbl_window_title = ctk.CTkLabel(
            active_inner,
            text="Click 'Start Tracking' to begin monitoring active screen time.",
            font=get_font(size=12),
            text_color=THEME["text_secondary"],
            anchor="w",
            wraplength=700,
            justify="left",
        )
        self.lbl_window_title.pack(fill="x")

        # Deep Insight & Action Row
        self.insight_row = ctk.CTkFrame(active_inner, fg_color="transparent")
        self.insight_row.pack(fill="x", pady=(8, 0))

        self.lbl_deep_action = ctk.CTkLabel(
            self.insight_row,
            text="🎯 Action: Ready to observe activity",
            font=get_font(size=13, weight="bold"),
            text_color=THEME["yellow_title"],
            anchor="w",
        )
        self.lbl_deep_action.pack(side="left")

        self.lbl_transition = ctk.CTkLabel(
            self.insight_row,
            text="• Transition: Standing by",
            font=get_font(size=12),
            text_color=THEME["denim_blue"],
            anchor="w",
        )
        self.lbl_transition.pack(side="left", padx=(10, 0))

        # Multitasking & Interval Intelligence Row
        self.multitask_row = ctk.CTkFrame(active_inner, fg_color="transparent")
        self.multitask_row.pack(fill="x", pady=(6, 0))

        self.lbl_multitask_badge = ctk.CTkLabel(
            self.multitask_row,
            text="⚡ Multitasking Agility: Observing flow",
            font=get_font(size=12, weight="bold"),
            text_color="#059669",
            anchor="w",
        )
        self.lbl_multitask_badge.pack(side="left")

        self.lbl_allocation_ratio = ctk.CTkLabel(
            self.multitask_row,
            text="• Work Focus: --%",
            font=get_font(size=12),
            text_color=THEME["text_secondary"],
            anchor="w",
        )
        self.lbl_allocation_ratio.pack(side="left", padx=(10, 0))

        # Stuck / Friction alert badge (hidden by default)
        self.lbl_stuck_alert = ctk.CTkLabel(
            active_inner,
            text="",
            font=get_font(size=11, weight="bold"),
            text_color="#dc2626",
            anchor="w",
        )

        # Universal Deliverable Quick Action Button (Localhost, Word, Excel, Figma, PDF)
        self.current_deliverable = None
        self.local_link_container = ctk.CTkFrame(active_inner, fg_color="transparent")
        self.btn_open_local_live = ctk.CTkButton(
            self.local_link_container,
            text="🚀 Test Live Web App (http://localhost:5176/)",
            font=get_font(size=11, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            text_color="#ffffff",
            height=28,
            corner_radius=6,
            cursor="hand2",
            command=self._handle_deliverable_action,
        )
        self.btn_open_local_live.pack(side="left")

        # Activity Feed Section
        feed_header = ctk.CTkFrame(self, fg_color="transparent")
        feed_header.pack(fill="x", padx=25, pady=(15, 6))

        feed_title = ctk.CTkLabel(
            feed_header,
            text="Recent Activity Stream",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
        )
        feed_title.pack(side="left")

        btn_clear = ctk.CTkButton(
            feed_header,
            text="Clear Stream View",
            command=self._clear_feed,
            fg_color=THEME["card_bg"],
            hover_color=THEME["card_hover"],
            text_color=THEME["text_secondary"],
            border_width=1,
            border_color=THEME["border"],
            font=get_font(size=11, weight="bold"),
            width=120,
            height=28,
            corner_radius=6,
            cursor="hand2",
        )
        btn_clear.pack(side="right")

        # Scrollable Feed Container
        self.feed_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=THEME["card_inner"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["border"],
        )
        self.feed_scroll.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        self._feed_rows = []

        # Empty State Placeholder (Visible when feed has no items)
        self.empty_state_frame = ctk.CTkFrame(self.feed_scroll, fg_color="transparent")
        lbl_empty_icon = ctk.CTkLabel(
            self.empty_state_frame,
            text="🟡",
            font=get_font(size=36),
        )
        lbl_empty_icon.pack(pady=(45, 6))

        lbl_empty_title = ctk.CTkLabel(
            self.empty_state_frame,
            text="No Activity Stream Recorded Yet",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_empty_title.pack(pady=(0, 4))

        lbl_empty_desc = ctk.CTkLabel(
            self.empty_state_frame,
            text="Click '▶ Start Tracking' above or focus any work application.\nMinion will log active windows, detect deliverables, and analyze focus velocity.",
            font=get_font(size=12),
            text_color=THEME["text_secondary"],
            justify="center",
        )
        lbl_empty_desc.pack(pady=(0, 16))

    def _handle_toggle(self) -> None:
        """Handle Start/Stop tracking click."""
        self.is_tracking = not self.is_tracking
        if self.is_tracking:
            self.btn_toggle.configure(
                text="⏹ Pause Minion",
                fg_color=THEME["denim_blue"],
                hover_color=THEME["denim_hover"],
                text_color="#ffffff",
            )
            self.status_badge.configure(
                text="● MINION ON DUTY",
                text_color=THEME["badge_success_text"],
                fg_color=THEME["badge_success_bg"],
            )
        else:
            self.btn_toggle.configure(
                text="▶ Start Tracking",
                fg_color=THEME["yellow"],
                hover_color=THEME["yellow_hover"],
                text_color=THEME["yellow_text"],
            )
            self.status_badge.configure(
                text="○ MINION RESTING",
                text_color=THEME["text_secondary"],
                fg_color=THEME["card_inner"],
            )

        self.on_toggle_tracking(self.is_tracking)

    def _handle_interval_change(self, choice: str) -> None:
        """Handle interval dropdown selection."""
        try:
            seconds = int(choice.split()[0])
            self.on_change_interval(seconds)
        except Exception:
            pass

    def update_live_snapshot(self, snapshot: Dict[str, Any], category: str) -> None:
        """
        Thread-safe update of current active window and prepend to activity feed.
        """
        app_name = snapshot.get("app_name", "Unknown")
        window_title = snapshot.get("window_title", "Desktop / Idle")
        is_idle = snapshot.get("is_idle", False)
        idle_sec = snapshot.get("idle_seconds", 0)

        action_verb = snapshot.get("action_verb") or f"Using {app_name}"
        transition = snapshot.get("transition_type") or "Active"
        is_stuck = snapshot.get("is_stuck", False)
        stuck_reason = snapshot.get("stuck_reason", "")

        # Update active window card
        self.lbl_app_name.configure(text=app_name)
        idle_info = f" [Idle: {int(idle_sec)}s]" if is_idle else ""
        self.lbl_window_title.configure(text=f"{window_title}{idle_info}")

        # Update deep action & transition
        self.lbl_deep_action.configure(text=f"🎯 {action_verb}")
        self.lbl_transition.configure(text=f"• Transition: {transition}")

        if is_stuck:
            self.lbl_stuck_alert.configure(
                text=f"⚠️ Cognitive Friction: {stuck_reason}"
            )
            self.lbl_stuck_alert.pack(fill="x", pady=(4, 0))
        else:
            self.lbl_stuck_alert.pack_forget()

        cat_color = CATEGORY_CONFIG.get(category, {}).get("color", "#64748b")
        self.category_badge.configure(
            text=category,
            fg_color=cat_color,
        )

        # Update cognitive sphere separation (Work vs Leisure vs Flow Shield)
        sphere = ActivityCorrelator.classify_sphere(app_name, window_title, category)
        sphere_meta = {
            ActivityCorrelator.SPHERE_WORK: ("💼 Core Work", "#2563eb"),
            ActivityCorrelator.SPHERE_RESEARCH: ("🔬 Research / Learning", "#0284c7"),
            ActivityCorrelator.SPHERE_COMMUNICATION: ("💬 Team Sync", "#7c3aed"),
            ActivityCorrelator.SPHERE_ACOUSTIC_RECHARGE: ("🎧 Flow Shield", "#10b981"),
            ActivityCorrelator.SPHERE_LEISURE: ("☕ Leisure / Break", "#f59e0b"),
            ActivityCorrelator.SPHERE_SYSTEM: ("⚙️ System", "#64748b"),
        }
        sp_text, sp_color = sphere_meta.get(sphere, ("💼 Core Work", "#2563eb"))
        self.sphere_badge.configure(text=sp_text, fg_color=sp_color)

        # Periodic interval correlation & multitasking evaluation
        if not hasattr(self, "_tick_count"):
            self._tick_count = 0
        self._tick_count += 1
        if self.db and (self._tick_count % 3 == 0 or self._tick_count == 1):
            try:
                recent_acts = self.db.get_activities(limit=30)
                corr = ActivityCorrelator.correlate_recent_intervals(recent_acts)
                st = corr.get("multitasking_state", "🎯 Monotasking Deep Flow")
                score = corr.get("dexterity_score", 95.0)
                w_pct = corr.get("work_pct", 95.0)
                self.lbl_multitask_badge.configure(text=f"{st} ({score}% Dexterity)")
                self.lbl_allocation_ratio.configure(text=f"• Work Allocation: {w_pct}% clean flow")
            except Exception:
                pass

        # Update active deliverable card
        self._update_deliverable_card(app_name, window_title, snapshot.get("local_url", ""))

        # Add item to activity feed
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        self._add_feed_row(now_str, app_name, category, window_title, cat_color, is_idle, sphere=sphere)

    def _update_deliverable_card(self, app_name: str, window_title: str, local_url: str = "") -> None:
        """Update active deliverable quick action across all professions."""
        user_dom = "general"
        if self.db:
            user_dom = self.db.get_setting("user_focus_domain", default="general")

        deliv = detect_active_deliverable(
            [{"window_title": window_title, "app_name": app_name}],
            domain=user_dom,
        )

        w_lower = window_title.lower()
        if not local_url and ("localhost" in w_lower or "127.0.0.1" in w_lower or ":3000" in w_lower or ":5173" in w_lower or ":5176" in w_lower or ":8000" in w_lower):
            active_srv = detect_active_local_server()
            if active_srv:
                local_url = active_srv.get("url", "")

        if local_url and (user_dom in ("software", "general") or "localhost" in w_lower):
            self.current_deliverable = {
                "title": "Live Web App",
                "action_type": "url",
                "target": local_url,
            }
            self.btn_open_local_live.configure(
                text=f"🚀 Test Live App ({local_url})",
                fg_color="#059669",
                hover_color="#047857",
            )
            self.local_link_container.pack(fill="x", pady=(6, 0))
        elif deliv and deliv.get("status") != "Tracking Focused Work":
            self.current_deliverable = deliv
            is_url = deliv.get("action_type") == "url"
            self.btn_open_local_live.configure(
                text=deliv.get("action_label", "⚡ Focus Deliverable"),
                fg_color="#059669" if is_url else "#2563eb",
                hover_color="#047857" if is_url else "#1d4ed8",
            )
            self.local_link_container.pack(fill="x", pady=(6, 0))
        else:
            self.current_deliverable = None
            self.local_link_container.pack_forget()

    def _handle_deliverable_action(self) -> None:
        """Execute quick action for the active deliverable across any craft."""
        if self.current_deliverable:
            activate_deliverable(self.current_deliverable)

    def _add_feed_row(
        self,
        timestamp: str,
        app: str,
        category: str,
        title: str,
        cat_color: str,
        is_idle: bool,
        sphere: str = "",
    ) -> None:
        """Prepend a single record to the activity stream scrollable frame."""
        row_frame = ctk.CTkFrame(
            self.feed_scroll,
            fg_color=THEME["card_bg"],
            corner_radius=6,
            height=38,
            border_width=1,
            border_color=THEME["border"],
        )
        row_frame.pack(fill="x", padx=4, pady=3, anchor="n")

        # Time tag
        lbl_time = ctk.CTkLabel(
            row_frame,
            text=timestamp,
            font=get_font(size=11),
            text_color=THEME["text_muted"],
            width=65,
        )
        lbl_time.pack(side="left", padx=(8, 4))

        # Sphere pill (Differentiating Core Work, Research, Audio, and Leisure)
        if not sphere:
            sphere = ActivityCorrelator.classify_sphere(app, title, category)
        sphere_labels = {
            ActivityCorrelator.SPHERE_WORK: ("💼 Work", "#2563eb"),
            ActivityCorrelator.SPHERE_RESEARCH: ("🔬 Research", "#0284c7"),
            ActivityCorrelator.SPHERE_COMMUNICATION: ("💬 Sync", "#7c3aed"),
            ActivityCorrelator.SPHERE_ACOUSTIC_RECHARGE: ("🎧 Audio", "#10b981"),
            ActivityCorrelator.SPHERE_LEISURE: ("☕ Leisure", "#f59e0b"),
            ActivityCorrelator.SPHERE_SYSTEM: ("⚙️ System", "#64748b"),
        }
        sp_text, sp_c = sphere_labels.get(sphere, ("💼 Work", "#2563eb"))
        lbl_sp = ctk.CTkLabel(
            row_frame,
            text=sp_text,
            font=get_font(size=10, weight="bold"),
            text_color="#ffffff",
            fg_color=sp_c,
            corner_radius=4,
            padx=6,
            pady=2,
        )
        lbl_sp.pack(side="left", padx=(2, 4))

        # Category pill
        lbl_cat = ctk.CTkLabel(
            row_frame,
            text=category,
            font=get_font(size=10, weight="bold"),
            text_color="#ffffff",
            fg_color=cat_color,
            corner_radius=4,
            padx=7,
            pady=2,
        )
        lbl_cat.pack(side="left", padx=4)

        # App Name
        lbl_app = ctk.CTkLabel(
            row_frame,
            text=app,
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_primary"],
            width=120,
            anchor="w",
        )
        lbl_app.pack(side="left", padx=6)

        # Window Title
        display_title = title if len(title) <= 55 else f"{title[:52]}..."
        lbl_title = ctk.CTkLabel(
            row_frame,
            text=display_title,
            font=get_font(size=11),
            text_color=THEME["text_secondary"],
            anchor="w",
        )
        lbl_title.pack(side="left", fill="x", expand=True, padx=4)

        self._hide_empty_state()
        self._feed_rows.append(row_frame)
        # Cap feed rows in memory to prevent unbounded DOM growth
        if len(self._feed_rows) > 100:
            oldest = self._feed_rows.pop(0)
            oldest.destroy()

    def _show_empty_state(self) -> None:
        """Display the empty state placeholder if no rows exist."""
        if not self._feed_rows:
            self.empty_state_frame.pack(fill="both", expand=True, pady=20)

    def _hide_empty_state(self) -> None:
        """Hide the empty state placeholder once records exist."""
        try:
            self.empty_state_frame.pack_forget()
        except Exception:
            pass

    def _clear_feed(self) -> None:
        """Clear all visual feed rows."""
        for row in self._feed_rows:
            row.destroy()
        self._feed_rows.clear()
        self._show_empty_state()

    def _load_persisted_history(self) -> None:
        """Load recent activities from SQLite on launch so history is never reset."""
        if not self.db:
            self._show_empty_state()
            return
        try:
            activities = self.db.get_activities(limit=15)
            if not activities:
                self._show_empty_state()
                return

            self._hide_empty_state()
            for act in activities:
                try:
                    dt = datetime.datetime.fromisoformat(act.get("timestamp", ""))
                    time_str = dt.strftime("%H:%M:%S")
                except Exception:
                    time_str = str(act.get("timestamp", ""))[-8:]
                app = act.get("app_name", "Unknown")
                cat = act.get("category", "Work / Coding")
                title = act.get("window_title", "")
                is_idle = bool(act.get("is_idle", 0))
                cat_color = CATEGORY_CONFIG.get(cat, {}).get("color", "#64748b")
                sphere = ActivityCorrelator.classify_sphere(app, title, cat)
                self._add_feed_row(time_str, app, cat, title, cat_color, is_idle, sphere=sphere)

            if activities:
                last = activities[0]
                self.lbl_app_name.configure(text=last.get("app_name", "None"))
                self.lbl_window_title.configure(text=last.get("window_title", "Waiting for activity..."))
                last_cat = last.get("category", "Work / Coding")
                cat_color = CATEGORY_CONFIG.get(last_cat, {}).get("color", "#64748b")
                self.category_badge.configure(text=last_cat, fg_color=cat_color)
                
                # Update sphere badge
                last_sphere = ActivityCorrelator.classify_sphere(last.get("app_name", ""), last.get("window_title", ""), last_cat)
                sphere_meta = {
                    ActivityCorrelator.SPHERE_WORK: ("💼 Core Work", "#2563eb"),
                    ActivityCorrelator.SPHERE_RESEARCH: ("🔬 Research / Learning", "#0284c7"),
                    ActivityCorrelator.SPHERE_COMMUNICATION: ("💬 Team Sync", "#7c3aed"),
                    ActivityCorrelator.SPHERE_ACOUSTIC_RECHARGE: ("🎧 Flow Shield", "#10b981"),
                    ActivityCorrelator.SPHERE_LEISURE: ("☕ Leisure / Break", "#f59e0b"),
                    ActivityCorrelator.SPHERE_SYSTEM: ("⚙️ System", "#64748b"),
                }
                sp_text, sp_color = sphere_meta.get(last_sphere, ("💼 Core Work", "#2563eb"))
                self.sphere_badge.configure(text=sp_text, fg_color=sp_color)

                # Initialize live multitasking & work ratio
                try:
                    corr = ActivityCorrelator.correlate_recent_intervals(activities)
                    st = corr.get("multitasking_state", "🎯 Monotasking Deep Flow")
                    score = corr.get("dexterity_score", 95.0)
                    w_pct = corr.get("work_pct", 95.0)
                    self.lbl_multitask_badge.configure(text=f"{st} ({score}% Dexterity)")
                    self.lbl_allocation_ratio.configure(text=f"• Work Allocation: {w_pct}% clean flow")
                except Exception:
                    pass

                # Update deliverable button on initial load
                self._update_deliverable_card(last.get("app_name", ""), last.get("window_title", ""))
        except Exception as e:
            pass
