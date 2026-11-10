"""
First-Run Setup & Onboarding Wizard for Minion AI.

This module provides a delightful, multi-step interactive onboarding experience
displayed when the application runs for the first time (or when re-invoked
from Preferences).

Features:
- Step 1: User Identity & Focus Domain Selection
- Step 2: Focus Sprint Pace & Productivity Goals
- Step 3: Local AI & Ollama Diagnostics (100% offline intelligence setup)
- Step 4: Summary & Launch
- 100% Light Mode Design System adhering to Work Sans typography and pure light surfaces.
"""

import logging
import threading
import customtkinter as ctk

from config import THEME, FOCUS_DOMAINS, ICON_ICO_PATH, ICON_PNG_PATH, get_font
from core.database import DatabaseManager
from core.ai_agent import OllamaAgent

logger = logging.getLogger(__name__)


class OnboardingWizard(ctk.CTkToplevel):
    """Multi-step modal dialog guiding new users through Minion's personalized setup."""

    def __init__(
        self,
        parent,
        db_manager: DatabaseManager,
        ai_agent: OllamaAgent,
        on_complete_callback=None,
    ):
        super().__init__(parent)

        self.db = db_manager
        self.ai = ai_agent
        self.on_complete_callback = on_complete_callback

        # Window Configuration
        self.title("Minion Setup — Personalize Your Focus Companion")
        self.geometry("780x640")
        self.minsize(700, 580)
        self.resizable(False, False)

        # Force Light Mode
        self.configure(fg_color=THEME.get("bg", "#f8fafc"))

        # Try setting window icon
        if ICON_ICO_PATH.exists():
            try:
                self.iconbitmap(str(ICON_ICO_PATH))
            except Exception:
                pass

        # Modal ergonomics
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_close_wizard)
        self.grab_set()

        # Wizard State
        self.current_step = 1
        self.total_steps = 4

        # User form selections
        self.selected_domain = "general"
        self.selected_sprint_minutes = 45

        # Initialize UI Components
        self._build_shell()
        self._show_step(1)

        # Center on parent window
        self.after(50, self._center_on_parent)

    def _center_on_parent(self) -> None:
        """Center the modal relative to the parent window."""
        try:
            self.update_idletasks()
            pw = self.master.winfo_width()
            ph = self.master.winfo_height()
            px = self.master.winfo_rootx()
            py = self.master.winfo_rooty()

            w = self.winfo_width()
            h = self.winfo_height()

            x = max(10, px + (pw - w) // 2)
            y = max(10, py + (ph - h) // 2)
            self.geometry(f"+{x}+{y}")
        except Exception as e:
            logger.debug("Could not center onboarding window: %s", e)

    def _build_shell(self) -> None:
        """Create outer wizard chrome: progress tracker header, dynamic body, and footer controls."""
        # Top Header Bar
        self.header_frame = ctk.CTkFrame(self, fg_color=THEME["surface"], corner_radius=0, height=85)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        top_inner = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        top_inner.pack(fill="both", expand=True, padx=28, pady=12)

        # Mascot + Title
        title_box = ctk.CTkFrame(top_inner, fg_color="transparent")
        title_box.pack(side="left")

        lbl_logo = ctk.CTkLabel(
            title_box,
            text="🍌 Minion AI",
            font=get_font("title", 18, "bold"),
            text_color=THEME["text_primary"],
        )
        lbl_logo.pack(anchor="w")

        self.lbl_subtitle = ctk.CTkLabel(
            title_box,
            text="Quick Setup & Personalization",
            font=get_font("small", 12),
            text_color=THEME["text_muted"],
        )
        self.lbl_subtitle.pack(anchor="w")

        # Step Progress Pills on Right
        self.steps_indicator_frame = ctk.CTkFrame(top_inner, fg_color="transparent")
        self.steps_indicator_frame.pack(side="right", pady=8)

        self.step_pills = []
        for i in range(1, self.total_steps + 1):
            pill = ctk.CTkLabel(
                self.steps_indicator_frame,
                text=f"  {i}  ",
                font=get_font("body", 11, "bold"),
                fg_color=THEME["yellow"] if i == 1 else THEME["surface_subtle"],
                text_color=THEME["yellow_text"] if i == 1 else THEME["text_muted"],
                corner_radius=12,
                height=24,
            )
            pill.pack(side="left", padx=4)
            self.step_pills.append(pill)

        # Divider
        div = ctk.CTkFrame(self, height=1, fg_color=THEME["border"], corner_radius=0)
        div.pack(fill="x")

        # Bottom Navigation Footer
        self.footer_frame = ctk.CTkFrame(self, fg_color=THEME["surface"], corner_radius=0, height=65)
        self.footer_frame.pack(fill="x", side="bottom")
        self.footer_frame.pack_propagate(False)

        # Footer divider
        fdiv = ctk.CTkFrame(self, height=1, fg_color=THEME["border"], corner_radius=0)
        fdiv.pack(fill="x", side="bottom")

        footer_inner = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        footer_inner.pack(fill="both", expand=True, padx=28, pady=12)

        self.btn_back = ctk.CTkButton(
            footer_inner,
            text="← Back",
            font=get_font("body", 13, "bold"),
            fg_color=THEME["surface_subtle"],
            hover_color=THEME["surface_hover"],
            text_color=THEME["text_secondary"],
            border_width=1,
            border_color=THEME["border"],
            corner_radius=8,
            width=100,
            height=38,
            command=self._on_back_clicked,
        )
        self.btn_back.pack(side="left")

        self.btn_next = ctk.CTkButton(
            footer_inner,
            text="Continue →",
            font=get_font("body", 13, "bold"),
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            corner_radius=8,
            width=140,
            height=38,
            command=self._on_next_clicked,
        )
        self.btn_next.pack(side="right")

        # Central Dynamic Body Container
        self.body_container = ctk.CTkFrame(self, fg_color="transparent")
        self.body_container.pack(fill="both", expand=True, padx=28, pady=20)

    def _update_indicators(self, step: int) -> None:
        """Update the visual state of step pills."""
        for i, pill in enumerate(self.step_pills, start=1):
            if i == step:
                pill.configure(
                    fg_color=THEME["yellow"],
                    text_color=THEME["yellow_text"],
                )
            elif i < step:
                pill.configure(
                    fg_color=THEME["accent_green"],
                    text_color="#ffffff",
                    text=f" ✓ ",
                )
            else:
                pill.configure(
                    fg_color=THEME["surface_subtle"],
                    text_color=THEME["text_muted"],
                    text=f"  {i}  ",
                )

    def _clear_body(self) -> None:
        """Remove existing step content from the body container."""
        for widget in self.body_container.winfo_children():
            widget.destroy()

    def _show_step(self, step: int) -> None:
        """Render the specific step layout."""
        self.current_step = step
        self._update_indicators(step)
        self._clear_body()

        # Navigation buttons update
        if step == 1:
            self.btn_back.pack_forget()
        else:
            self.btn_back.pack(side="left")

        if step == self.total_steps:
            self.btn_next.configure(
                text="🍌 Launch Minion AI",
                fg_color=THEME["yellow"],
                hover_color=THEME["yellow_hover"],
                text_color=THEME["yellow_text"],
                width=180,
            )
        else:
            self.btn_next.configure(
                text="Continue →",
                fg_color=THEME["yellow"],
                hover_color=THEME["yellow_hover"],
                text_color=THEME["yellow_text"],
                width=140,
            )

        if step == 1:
            self._render_step_1_identity()
        elif step == 2:
            self._render_step_2_habits()
        elif step == 3:
            self._render_step_3_ai()
        elif step == 4:
            self._render_step_4_launch()

    # =========================================================================
    # STEP 1: IDENTITY & FOCUS DOMAIN
    # =========================================================================
    def _render_step_1_identity(self) -> None:
        """Render Step 1: User name, role, and domain."""
        self.lbl_subtitle.configure(text="Step 1 of 4: Welcome & Identity")

        card = ctk.CTkFrame(
            self.body_container,
            fg_color=THEME["surface"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        card.pack(fill="both", expand=True, padx=10, pady=5)

        inner = ctk.CTkScrollableFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=20)

        # Greeting banner
        lbl_welcome = ctk.CTkLabel(
            inner,
            text="Bello! Let's get Minion ready for you.",
            font=get_font("header", 20, "bold"),
            text_color=THEME["text_primary"],
        )
        lbl_welcome.pack(anchor="w", pady=(0, 4))

        lbl_desc = ctk.CTkLabel(
            inner,
            text="Minion protects your attention, tracks work sessions, and gives you intelligent focus feedback.",
            font=get_font("body", 13),
            text_color=THEME["text_secondary"],
        )
        lbl_desc.pack(anchor="w", pady=(0, 20))

        # Full Name Field
        lbl_name = ctk.CTkLabel(
            inner,
            text="What should Minion call you?",
            font=get_font("bold", 13, "bold"),
            text_color=THEME["text_primary"],
        )
        lbl_name.pack(anchor="w", pady=(0, 4))

        # Prepopulate with current profile name if available
        profile = self.db.get_user_profile()
        saved_name = profile.get("full_name") or ""

        self.entry_name = ctk.CTkEntry(
            inner,
            font=get_font("body", 13),
            placeholder_text="e.g. Alex, Jordan, Sarah...",
            fg_color=THEME["surface_subtle"],
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            height=40,
            corner_radius=8,
        )
        self.entry_name.pack(fill="x", pady=(0, 16))
        if saved_name:
            self.entry_name.insert(0, saved_name)

        # Primary Role / Craft
        lbl_role = ctk.CTkLabel(
            inner,
            text="Your Role or Main Title",
            font=get_font("bold", 13, "bold"),
            text_color=THEME["text_primary"],
        )
        lbl_role.pack(anchor="w", pady=(0, 4))

        saved_role = profile.get("profession_role") or ""
        self.entry_role = ctk.CTkEntry(
            inner,
            font=get_font("body", 13),
            placeholder_text="e.g. Full-Stack Developer, Product Designer, Founder, Writer...",
            fg_color=THEME["surface_subtle"],
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            height=40,
            corner_radius=8,
        )
        self.entry_role.pack(fill="x", pady=(0, 16))
        if saved_role:
            self.entry_role.insert(0, saved_role)

        # Focus Domain Selector
        lbl_domain = ctk.CTkLabel(
            inner,
            text="Select Your Primary Work Domain",
            font=get_font("bold", 13, "bold"),
            text_color=THEME["text_primary"],
        )
        lbl_domain.pack(anchor="w", pady=(0, 4))

        lbl_domain_sub = ctk.CTkLabel(
            inner,
            text="Minion customizes its productivity scoring and vocabulary for your craft.",
            font=get_font("small", 12),
            text_color=THEME["text_muted"],
        )
        lbl_domain_sub.pack(anchor="w", pady=(0, 8))

        saved_domain = self.db.get_setting("user_focus_domain", default="general")
        self.selected_domain = saved_domain

        # Domain radio cards
        self.domain_var = ctk.StringVar(value=saved_domain)

        domain_grid = ctk.CTkFrame(inner, fg_color="transparent")
        domain_grid.pack(fill="x", pady=(0, 10))
        domain_grid.grid_columnconfigure((0, 1), weight=1)

        for idx, (k, d) in enumerate(FOCUS_DOMAINS.items()):
            row = idx // 2
            col = idx % 2

            domain_card = ctk.CTkFrame(
                domain_grid,
                fg_color=THEME["surface_subtle"],
                border_width=1,
                border_color=THEME["border"],
                corner_radius=8,
            )
            domain_card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            rb = ctk.CTkRadioButton(
                domain_card,
                text=f"{d['icon']}  {d['title']}",
                value=k,
                variable=self.domain_var,
                font=get_font("body", 12, "bold"),
                text_color=THEME["text_primary"],
                fg_color=THEME["yellow"],
                border_color=THEME["border"],
                hover_color=THEME["yellow_hover"],
            )
            rb.pack(anchor="w", padx=12, pady=10)

    # =========================================================================
    # STEP 2: FOCUS PACE & SPRINT GOALS
    # =========================================================================
    def _render_step_2_habits(self) -> None:
        """Render Step 2: Work rhythm, focus sprint duration, and goals."""
        self.lbl_subtitle.configure(text="Step 2 of 4: Focus Pace & Goals")

        card = ctk.CTkFrame(
            self.body_container,
            fg_color=THEME["surface"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        card.pack(fill="both", expand=True, padx=10, pady=5)

        inner = ctk.CTkScrollableFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=20)

        lbl_title = ctk.CTkLabel(
            inner,
            text="How do you prefer to run your focus sessions?",
            font=get_font("header", 18, "bold"),
            text_color=THEME["text_primary"],
        )
        lbl_title.pack(anchor="w", pady=(0, 4))

        lbl_desc = ctk.CTkLabel(
            inner,
            text="Pick a work rhythm that matches your energy curve.",
            font=get_font("body", 13),
            text_color=THEME["text_secondary"],
        )
        lbl_desc.pack(anchor="w", pady=(0, 16))

        # Sprint duration presets
        saved_sprint = int(self.db.get_setting("sprint_duration_minutes", default="45"))
        self.sprint_var = ctk.IntVar(value=saved_sprint)

        presets = [
            (25, "⚡ 25 min Pomodoro", "Classic short agile sprints with rapid recovery."),
            (45, "🎯 45 min Deep Dive", "Recommended for engineering, analysis & deep work."),
            (60, "🌊 60 min Flow State", "Uninterrupted immersion for long-form complex tasks."),
        ]

        for minutes, label, sub in presets:
            pframe = ctk.CTkFrame(
                inner,
                fg_color=THEME["surface_subtle"],
                border_width=1,
                border_color=THEME["border"],
                corner_radius=8,
            )
            pframe.pack(fill="x", pady=4)

            rb = ctk.CTkRadioButton(
                pframe,
                text=label,
                value=minutes,
                variable=self.sprint_var,
                font=get_font("body", 13, "bold"),
                text_color=THEME["text_primary"],
                fg_color=THEME["yellow"],
                border_color=THEME["border"],
                hover_color=THEME["yellow_hover"],
            )
            rb.pack(anchor="w", padx=14, pady=(10, 2))

            sub_lbl = ctk.CTkLabel(
                pframe,
                text=sub,
                font=get_font("small", 11),
                text_color=THEME["text_muted"],
            )
            sub_lbl.pack(anchor="w", padx=38, pady=(0, 10))

        # Focus Purpose / Goal
        profile = self.db.get_user_profile()
        lbl_goal = ctk.CTkLabel(
            inner,
            text="Current Big Mission / Main Goal",
            font=get_font("bold", 13, "bold"),
            text_color=THEME["text_primary"],
        )
        lbl_goal.pack(anchor="w", pady=(16, 4))

        self.entry_goal = ctk.CTkEntry(
            inner,
            font=get_font("body", 13),
            placeholder_text="e.g. Launch the new billing platform, finish master thesis...",
            fg_color=THEME["surface_subtle"],
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            height=38,
            corner_radius=8,
        )
        self.entry_goal.pack(fill="x", pady=(0, 12))
        if profile.get("short_term_goals"):
            self.entry_goal.insert(0, profile.get("short_term_goals"))

        # Distraction Triggers
        lbl_avoid = ctk.CTkLabel(
            inner,
            text="Habits or Distractions to Guard Against",
            font=get_font("bold", 13, "bold"),
            text_color=THEME["text_primary"],
        )
        lbl_avoid.pack(anchor="w", pady=(4, 4))

        self.entry_avoid = ctk.CTkEntry(
            inner,
            font=get_font("body", 13),
            placeholder_text="e.g. YouTube shorts, social feeds, checking stock tickers during work...",
            fg_color=THEME["surface_subtle"],
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            height=38,
            corner_radius=8,
        )
        self.entry_avoid.pack(fill="x", pady=(0, 10))
        if profile.get("things_to_avoid"):
            self.entry_avoid.insert(0, profile.get("things_to_avoid"))

    # =========================================================================
    # STEP 3: OLLAMA & LOCAL AI ENGINE
    # =========================================================================
    def _render_step_3_ai(self) -> None:
        """Render Step 3: Ollama local intelligence diagnostics and auto-start."""
        self.lbl_subtitle.configure(text="Step 3 of 4: Intelligence Engine")

        card = ctk.CTkFrame(
            self.body_container,
            fg_color=THEME["surface"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        card.pack(fill="both", expand=True, padx=10, pady=5)

        inner = ctk.CTkScrollableFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=20)

        lbl_title = ctk.CTkLabel(
            inner,
            text="Private Local AI Engine (Ollama)",
            font=get_font("header", 18, "bold"),
            text_color=THEME["text_primary"],
        )
        lbl_title.pack(anchor="w", pady=(0, 4))

        lbl_desc = ctk.CTkLabel(
            inner,
            text="Minion connects with local LLMs (like Llama 3.2 or Mistral) for 100% offline context synthesis and chat.",
            font=get_font("body", 13),
            text_color=THEME["text_secondary"],
        )
        lbl_desc.pack(anchor="w", pady=(0, 16))

        # Status Card
        self.ai_status_card = ctk.CTkFrame(
            inner,
            fg_color=THEME["surface_subtle"],
            border_width=1,
            border_color=THEME["border"],
            corner_radius=8,
        )
        self.ai_status_card.pack(fill="x", pady=(0, 16))

        sc_inner = ctk.CTkFrame(self.ai_status_card, fg_color="transparent")
        sc_inner.pack(fill="x", padx=16, pady=14)

        self.lbl_ai_indicator = ctk.CTkLabel(
            sc_inner,
            text="Checking Ollama Service...",
            font=get_font("body", 13, "bold"),
            text_color=THEME["text_secondary"],
        )
        self.lbl_ai_indicator.pack(side="left")

        self.btn_check_ai = ctk.CTkButton(
            sc_inner,
            text="Check / Start Ollama",
            font=get_font("small", 12, "bold"),
            fg_color=THEME["blue"],
            hover_color=THEME["blue_hover"],
            text_color="#ffffff",
            corner_radius=6,
            height=32,
            command=self._handle_check_or_start_ai,
        )
        self.btn_check_ai.pack(side="right")

        # Fallback explanation
        note_frame = ctk.CTkFrame(
            inner,
            fg_color="#f0fdf4",
            border_width=1,
            border_color="#bbf7d0",
            corner_radius=8,
        )
        note_frame.pack(fill="x", pady=(0, 16))

        note_inner = ctk.CTkFrame(note_frame, fg_color="transparent")
        note_inner.pack(fill="x", padx=16, pady=12)

        lbl_shield = ctk.CTkLabel(
            note_inner,
            text="💡 Minion Works Without Ollama Too!",
            font=get_font("bold", 12, "bold"),
            text_color="#166534",
        )
        lbl_shield.pack(anchor="w", pady=(0, 2))

        lbl_shield_sub = ctk.CTkLabel(
            note_inner,
            text="If Ollama is not installed on this PC, Minion's built-in heuristic engine automatically scores activity, creates work segments, and tracks your focus with zero setup.",
            font=get_font("small", 11),
            text_color="#15803d",
            wraplength=640,
            justify="left",
        )
        lbl_shield_sub.pack(anchor="w")

        # Auto-start Ollama checkbox
        auto_start = self.db.get_setting("auto_start_ollama", default="true").lower() == "true"
        self.var_auto_ollama = ctk.BooleanVar(value=auto_start)

        cb = ctk.CTkCheckBox(
            inner,
            text="Automatically start Ollama background service when Minion launches",
            variable=self.var_auto_ollama,
            font=get_font("body", 12),
            text_color=THEME["text_primary"],
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            checkmark_color=THEME["yellow_text"],
        )
        cb.pack(anchor="w", pady=(0, 10))

        # Start background check
        threading.Thread(target=self._check_ai_status_bg, daemon=True).start()

    def _check_ai_status_bg(self) -> None:
        """Query Ollama status in background thread."""
        is_running = self.ai.is_service_running()
        model_name = self.db.get_setting("ollama_model", default="llama3.2")

        def _update():
            if not self.winfo_exists():
                return
            if is_running:
                self.lbl_ai_indicator.configure(
                    text=f"● Ollama Active ({model_name})",
                    text_color="#059669",
                )
                self.btn_check_ai.configure(text="Connected ✓", state="disabled")
            else:
                self.lbl_ai_indicator.configure(
                    text="○ Ollama Offline / Not Detected",
                    text_color="#d97706",
                )
                self.btn_check_ai.configure(text="Start Service", state="normal")

        self.after(0, _update)

    def _handle_check_or_start_ai(self) -> None:
        """Start or verify Ollama on demand."""
        self.lbl_ai_indicator.configure(text="Connecting to Ollama...", text_color=THEME["text_secondary"])
        self.btn_check_ai.configure(state="disabled")

        def _worker():
            started = self.ai.start_service(timeout=6.0)
            is_active = self.ai.is_service_running()
            model_name = self.db.get_setting("ollama_model", default="llama3.2")

            def _done():
                if not self.winfo_exists():
                    return
                if is_active:
                    self.lbl_ai_indicator.configure(text=f"● Ollama Active ({model_name})", text_color="#059669")
                    self.btn_check_ai.configure(text="Connected ✓", state="disabled")
                else:
                    self.lbl_ai_indicator.configure(text="○ Ollama Not Running (Heuristic Mode Active)", text_color=THEME["text_muted"])
                    self.btn_check_ai.configure(text="Retry Start", state="normal")

            self.after(0, _done)

        threading.Thread(target=worker, daemon=True) if (worker := _worker) else None

    # =========================================================================
    # STEP 4: LAUNCH SUMMARY
    # =========================================================================
    def _render_step_4_launch(self) -> None:
        """Render final step summary before entering the main app."""
        self.lbl_subtitle.configure(text="Step 4 of 4: All Set!")

        card = ctk.CTkFrame(
            self.body_container,
            fg_color=THEME["surface"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        card.pack(fill="both", expand=True, padx=10, pady=5)

        inner = ctk.CTkScrollableFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=20)

        # Mascot celebration
        lbl_party = ctk.CTkLabel(
            inner,
            text="🍌 Minion is Ready to Roll!",
            font=get_font("header", 22, "bold"),
            text_color=THEME["text_primary"],
        )
        lbl_party.pack(anchor="w", pady=(0, 6))

        # Name readout
        name = getattr(self, "_cached_name", "Friend") or "Friend"
        lbl_sub = ctk.CTkLabel(
            inner,
            text=f"Welcome aboard, {name}! Minion will quietly monitor active windows, detect flow states, and guard your deep work.",
            font=get_font("body", 13),
            text_color=THEME["text_secondary"],
            wraplength=640,
            justify="left",
        )
        lbl_sub.pack(anchor="w", pady=(0, 20))

        # Summary Checklist
        summary_box = ctk.CTkFrame(
            inner,
            fg_color=THEME["surface_subtle"],
            border_width=1,
            border_color=THEME["border"],
            corner_radius=8,
        )
        summary_box.pack(fill="x", pady=(0, 16))

        s_inner = ctk.CTkFrame(summary_box, fg_color="transparent")
        s_inner.pack(fill="x", padx=18, pady=16)

        domain_key = getattr(self, "selected_domain", "general")
        domain_info = FOCUS_DOMAINS.get(domain_key, FOCUS_DOMAINS["general"])
        sprint_mins = getattr(self, "selected_sprint_minutes", 45)

        domain_desc = domain_info.get("tagline") or domain_info.get("description") or domain_info.get("work_label") or "Productivity"
        items = [
            (f"{domain_info.get('icon', '💼')} Focus Archetype", f"{domain_info.get('title', 'General')} ({domain_desc})"),
            ("⏱️ Sprint Cadence", f"{sprint_mins} Minutes per Focus Sprint"),
            ("🛡️ Privacy Protection", "100% Local data storage, zero cloud telemetry"),
            ("🧠 Intelligence Tier", "Embedded Python runtime + Local Ollama / Smart Heuristics"),
        ]

        for title, val in items:
            row_frame = ctk.CTkFrame(s_inner, fg_color="transparent")
            row_frame.pack(fill="x", pady=4)

            lbl_t = ctk.CTkLabel(
                row_frame,
                text=title,
                font=get_font("bold", 12, "bold"),
                text_color=THEME["text_primary"],
                width=160,
                anchor="w",
            )
            lbl_t.pack(side="left")

            lbl_v = ctk.CTkLabel(
                row_frame,
                text=val,
                font=get_font("body", 12),
                text_color=THEME["text_secondary"],
                anchor="w",
            )
            lbl_v.pack(side="left", fill="x", expand=True)

        # Quick tip
        tip_frame = ctk.CTkFrame(
            inner,
            fg_color="#fffbeb",
            border_width=1,
            border_color="#fef3c7",
            corner_radius=8,
        )
        tip_frame.pack(fill="x", pady=(4, 10))

        lbl_tip = ctk.CTkLabel(
            tip_frame,
            text="✨ Tip: You can adjust these settings anytime in the 'Preferences & Lab' tab.",
            font=get_font("small", 12),
            text_color="#92400e",
            padx=14,
            pady=10,
        )
        lbl_tip.pack(anchor="w")

    # =========================================================================
    # NAVIGATION HANDLERS & SAVE
    # =========================================================================
    def _save_current_step_inputs(self) -> None:
        """Capture inputs from the current step into memory / database."""
        if self.current_step == 1:
            if hasattr(self, "entry_name"):
                self._cached_name = self.entry_name.get().strip()
            if hasattr(self, "entry_role"):
                self._cached_role = self.entry_role.get().strip()
            if hasattr(self, "domain_var"):
                self.selected_domain = self.domain_var.get()
                self.db.set_setting("user_focus_domain", self.selected_domain)

        elif self.current_step == 2:
            if hasattr(self, "sprint_var"):
                self.selected_sprint_minutes = self.sprint_var.get()
                self.db.set_setting("sprint_duration_minutes", str(self.selected_sprint_minutes))
            if hasattr(self, "entry_goal"):
                self._cached_goal = self.entry_goal.get().strip()
            if hasattr(self, "entry_avoid"):
                self._cached_avoid = self.entry_avoid.get().strip()

        elif self.current_step == 3:
            if hasattr(self, "var_auto_ollama"):
                val = "true" if self.var_auto_ollama.get() else "false"
                self.db.set_setting("auto_start_ollama", val)

    def _on_back_clicked(self) -> None:
        """Go back one step."""
        self._save_current_step_inputs()
        if self.current_step > 1:
            self._show_step(self.current_step - 1)

    def _on_next_clicked(self) -> None:
        """Proceed to next step or complete onboarding."""
        self._save_current_step_inputs()
        if self.current_step < self.total_steps:
            self._show_step(self.current_step + 1)
        else:
            self._finalize_onboarding()

    def _finalize_onboarding(self) -> None:
        """Save all collected information to SQLite and close wizard."""
        try:
            profile = self.db.get_user_profile()
            if hasattr(self, "_cached_name") and self._cached_name:
                profile["full_name"] = self._cached_name
            if hasattr(self, "_cached_role") and self._cached_role:
                profile["profession_role"] = self._cached_role
            if hasattr(self, "selected_domain"):
                profile["focus_domain"] = self.selected_domain
            if hasattr(self, "_cached_goal") and self._cached_goal:
                profile["short_term_goals"] = self._cached_goal
            if hasattr(self, "_cached_avoid") and self._cached_avoid:
                profile["things_to_avoid"] = self._cached_avoid

            self.db.save_user_profile(profile)

            # Mark onboarding as completed
            self.db.set_setting("onboarding_completed", "true")

            logger.info("🍌 Minion onboarding wizard successfully completed!")
        except Exception as e:
            logger.error("Error saving onboarding profile: %s", e)

        # Notify callback
        if callable(self.on_complete_callback):
            try:
                self.on_complete_callback()
            except Exception as e:
                logger.debug("Error in onboarding completion callback: %s", e)

        self.grab_release()
        self.destroy()

    def _on_close_wizard(self) -> None:
        """Handle user closing the wizard via window [X] button."""
        try:
            self.db.set_setting("onboarding_completed", "true")
        except Exception:
            pass
        self.grab_release()
        self.destroy()
