"""
Settings & AI Configuration View for ProductivityCheck.

This view provides controls for:
1. Dedicated Light Design System status and theme specs.
2. Activity tracking automation (auto-start on launch).
3. Local Ollama AI agent diagnostics, model selection, and model puller.
4. Custom categorization rules (mapping applications/window titles to specific categories).
5. Privacy exclusion safeguards.
"""

import threading
import subprocess
import tkinter.messagebox as messagebox
import customtkinter as ctk

from core.database import DatabaseManager
from core.ai_agent import OllamaAgent
from core.autostart import is_autostart_enabled, enable_autostart, disable_autostart
from config import THEME, CATEGORY_CONFIG, DEFAULT_PRIVACY_EXCLUSIONS, get_font, FOCUS_DOMAINS


class SettingsView(ctk.CTkFrame):
    """View managing visual theme, activity automation, local intelligence, and classification rules."""

    def __init__(
        self,
        master,
        db_manager: DatabaseManager,
        ai_agent: OllamaAgent,
        on_rules_changed=None,
        **kwargs,
    ):
        """
        Initialize the Settings View.

        Args:
            master: Parent container.
            db_manager: Database manager.
            ai_agent: Ollama AI agent.
            on_rules_changed: Callback invoked when categorization rules are added/deleted.
        """
        super().__init__(master, fg_color="transparent", **kwargs)

        self.db = db_manager
        self.ai = ai_agent
        self.on_rules_changed = on_rules_changed

        self._build_ui()
        self.check_ai_status()
        self._load_custom_rules()

    def _build_ui(self) -> None:
        """Construct the visual hierarchy."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(20, 10))

        header_left = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_left.pack(side="left", fill="both", expand=True)

        title_label = ctk.CTkLabel(
            header_left,
            text="Minion Workshop & Preferences",
            font=get_font(size=24, weight="bold"),
            text_color=THEME["yellow_title"],
        )
        title_label.pack(anchor="w")

        sub_label = ctk.CTkLabel(
            header_left,
            text="Bello! Customize your visual system, activity tracking, local intelligence, and work rules",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
        )
        sub_label.pack(anchor="w", pady=(2, 0))

        btn_wizard = ctk.CTkButton(
            header_frame,
            text="✨ Run Setup Wizard",
            font=get_font(size=12, weight="bold"),
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            corner_radius=8,
            height=36,
            command=self._handle_reopen_wizard,
        )
        btn_wizard.pack(side="right", padx=(10, 0))

        # Main Scrollable Container
        self.scroll_content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_content.pack(fill="both", expand=True, padx=25, pady=(5, 20))

        # SECTION 1: Studio Theme & Appearance (100% Light Mode Design System)
        theme_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        theme_card.pack(fill="x", pady=(0, 15))

        theme_inner = ctk.CTkFrame(theme_card, fg_color="transparent")
        theme_inner.pack(fill="x", padx=20, pady=18)

        lbl_theme_title = ctk.CTkLabel(
            theme_inner,
            text="🎨 Studio Theme & Design System",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_theme_title.pack(anchor="w", pady=(0, 4))

        lbl_theme_sub = ctk.CTkLabel(
            theme_inner,
            text="Minion runs on a dedicated high-contrast light design system with Work Sans typography and zero dark mode artifacts.",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
        )
        lbl_theme_sub.pack(anchor="w", pady=(0, 12))

        ctrl_theme = ctk.CTkFrame(theme_inner, fg_color=THEME["card_inner"], corner_radius=8, border_width=1, border_color=THEME["border"])
        ctrl_theme.pack(fill="x")

        ctrl_inner = ctk.CTkFrame(ctrl_theme, fg_color="transparent")
        ctrl_inner.pack(fill="x", padx=16, pady=12)

        lbl_active_theme = ctk.CTkLabel(
            ctrl_inner,
            text="☀️ Pure Light Studio • Banana Yellow & Denim Blue • High-Contrast WCAG AAA",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_active_theme.pack(side="left")

        badge_wcag = ctk.CTkLabel(
            ctrl_inner,
            text="WCAG AAA",
            font=get_font(size=10, weight="bold"),
            text_color=THEME["badge_success_text"],
            fg_color=THEME["badge_success_bg"],
            corner_radius=4,
            padx=8,
            pady=2,
        )
        badge_wcag.pack(side="right")

        # SECTION 2: General & Live Tracking Automation
        auto_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        auto_card.pack(fill="x", pady=(0, 15))

        auto_inner = ctk.CTkFrame(auto_card, fg_color="transparent")
        auto_inner.pack(fill="x", padx=20, pady=18)

        lbl_auto_title = ctk.CTkLabel(
            auto_inner,
            text="⚡ Activity Tracking Automation",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_auto_title.pack(anchor="w", pady=(0, 4))

        lbl_auto_sub = ctk.CTkLabel(
            auto_inner,
            text="Configure how Minion initiates screen activity tracking upon launch.",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
        )
        lbl_auto_sub.pack(anchor="w", pady=(0, 12))

        # Switch 1: Auto-Start Tracking
        current_auto_start = self.db.get_setting("auto_start_tracking", default="true").lower() == "true"
        self.switch_auto_start = ctk.CTkSwitch(
            auto_inner,
            text="Automatically resume live tracking on launch",
            font=get_font(size=13, weight="bold"),
            text_color=THEME["text_primary"],
            progress_color=THEME["denim_blue"],
            button_color=THEME["yellow"],
            button_hover_color=THEME["yellow_hover"],
            command=self._on_toggle_auto_start,
        )
        if current_auto_start:
            self.switch_auto_start.select()
        else:
            self.switch_auto_start.deselect()
        self.switch_auto_start.pack(anchor="w", pady=(2, 2))

        lbl_switch_hint = ctk.CTkLabel(
            auto_inner,
            text="When enabled, Minion on Duty immediately captures work activities when active.",
            font=get_font(size=12),
            text_color=THEME["text_muted"],
        )
        lbl_switch_hint.pack(anchor="w", pady=(0, 10))

        # Switch 2: Windows Boot Autostart
        current_autostart = is_autostart_enabled()
        self.switch_autostart_boot = ctk.CTkSwitch(
            auto_inner,
            text="Start Minion AI on Windows Boot (Silent Ambient Intelligence)",
            font=get_font(size=13, weight="bold"),
            text_color=THEME["text_primary"],
            progress_color=THEME["denim_blue"],
            button_color=THEME["yellow"],
            button_hover_color=THEME["yellow_hover"],
            command=self._on_toggle_autostart_boot,
        )
        if current_autostart:
            self.switch_autostart_boot.select()
        else:
            self.switch_autostart_boot.deselect()
        self.switch_autostart_boot.pack(anchor="w", pady=(2, 2))

        lbl_boot_hint = ctk.CTkLabel(
            auto_inner,
            text="Runs Minion AI silently in the background tray on restart. Tracking only resumes if not paused.",
            font=get_font(size=12),
            text_color=THEME["text_muted"],
        )
        lbl_boot_hint.pack(anchor="w", pady=(0, 10))

        # Switch 3: Close to System Tray
        current_close_tray = self.db.get_setting("close_to_tray", default="true").lower() == "true"
        self.switch_close_tray = ctk.CTkSwitch(
            auto_inner,
            text="Minimize to System Tray on Close (Keep Background Intelligence Alive)",
            font=get_font(size=13, weight="bold"),
            text_color=THEME["text_primary"],
            progress_color=THEME["denim_blue"],
            button_color=THEME["yellow"],
            button_hover_color=THEME["yellow_hover"],
            command=self._on_toggle_close_to_tray,
        )
        if current_close_tray:
            self.switch_close_tray.select()
        else:
            self.switch_close_tray.deselect()
        self.switch_close_tray.pack(anchor="w", pady=(2, 2))

        lbl_tray_hint = ctk.CTkLabel(
            auto_inner,
            text="Clicking 'X' hides the window to the tray while monitor threads stay alive.",
            font=get_font(size=12),
            text_color=THEME["text_muted"],
        )
        lbl_tray_hint.pack(anchor="w")

        # SECTION 2.5: Multi-Disciplinary Work Profile & Focus Domain
        profile_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        profile_card.pack(fill="x", pady=(0, 15))

        profile_inner = ctk.CTkFrame(profile_card, fg_color="transparent")
        profile_inner.pack(fill="x", padx=20, pady=18)

        lbl_prof_title = ctk.CTkLabel(
            profile_inner,
            text="🎯 Focus Profile & Work Discipline",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_prof_title.pack(anchor="w", pady=(0, 4))

        lbl_prof_sub = ctk.CTkLabel(
            profile_inner,
            text="Minion adapts focus styles, cognitive archetypes, workspaces, and deliverables to your profession.",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
        )
        lbl_prof_sub.pack(anchor="w", pady=(0, 12))

        prof_row = ctk.CTkFrame(profile_inner, fg_color="transparent")
        prof_row.pack(fill="x")

        domain_display_list = [f"{d['icon']}  {d['title']}" for d in FOCUS_DOMAINS.values()]
        active_domain = self.db.get_setting("user_focus_domain", "")
        if not active_domain:
            active_domain = self.db.get_user_profile().get("focus_domain", "general")
        active_info = FOCUS_DOMAINS.get(active_domain, FOCUS_DOMAINS["general"])

        self.combo_settings_domain = ctk.CTkComboBox(
            prof_row,
            values=domain_display_list,
            command=self._on_settings_domain_selected,
            height=36,
            corner_radius=8,
            border_width=1,
            border_color=THEME["input_border"],
            fg_color=THEME["card_inner"],
            button_color=THEME["card_bg"],
            button_hover_color=THEME["border"],
            dropdown_fg_color=THEME["card_bg"],
            dropdown_hover_color=THEME["yellow_tint"],
            dropdown_text_color=THEME["text_primary"],
            text_color=THEME["text_primary"],
            font=get_font(size=12, weight="bold"),
            width=320,
        )
        self.combo_settings_domain.set(f"{active_info['icon']}  {active_info['title']}")
        self.combo_settings_domain.pack(side="left", padx=(0, 14))

        self.lbl_domain_desc = ctk.CTkLabel(
            prof_row,
            text=active_info["tagline"],
            font=get_font(size=12),
            text_color=THEME["text_muted"],
            anchor="w",
            wraplength=400,
            justify="left",
        )
        self.lbl_domain_desc.pack(side="left", fill="x", expand=True)

        # SECTION 3: Local Ollama AI Agent Status, Auto-Start & Model Management
        ai_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        ai_card.pack(fill="x", pady=(0, 15))

        ai_inner = ctk.CTkFrame(ai_card, fg_color="transparent")
        ai_inner.pack(fill="x", padx=20, pady=18)

        # Header Row
        ai_header = ctk.CTkFrame(ai_inner, fg_color="transparent")
        ai_header.pack(fill="x", pady=(0, 4))

        lbl_ai_title = ctk.CTkLabel(
            ai_header,
            text="🧠 Minion Brain Engine (Local Intelligence)",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_ai_title.pack(side="left")

        self.ai_badge = ctk.CTkLabel(
            ai_header,
            text="Checking...",
            font=get_font(size=11, weight="bold"),
            text_color=THEME["text_secondary"],
            fg_color=THEME["card_inner"],
            corner_radius=6,
            padx=10,
            pady=3,
        )
        self.ai_badge.pack(side="right")

        self.lbl_ai_desc = ctk.CTkLabel(
            ai_inner,
            text="Sovereign, on-device intelligence powered by Ollama. Activity classification, sprint analysis, and standup generation run 100% locally on your workstation.",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
            anchor="w",
            wraplength=760,
            justify="left",
        )
        self.lbl_ai_desc.pack(fill="x", pady=(0, 14))

        # 1-Click Quick Setup Hero Banner
        self.frame_quick_setup = ctk.CTkFrame(
            ai_inner,
            fg_color=THEME["yellow_tint"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["yellow_border"],
        )
        self.frame_quick_setup.pack(fill="x", pady=(0, 14))

        setup_inner = ctk.CTkFrame(self.frame_quick_setup, fg_color="transparent")
        setup_inner.pack(fill="x", padx=16, pady=12)

        setup_top = ctk.CTkFrame(setup_inner, fg_color="transparent")
        setup_top.pack(fill="x")

        lbl_setup_icon = ctk.CTkLabel(
            setup_top,
            text="⚡",
            font=get_font(size=18, weight="bold"),
            text_color=THEME["yellow_title"],
        )
        lbl_setup_icon.pack(side="left", padx=(0, 8))

        setup_text_col = ctk.CTkFrame(setup_top, fg_color="transparent")
        setup_text_col.pack(side="left", fill="x", expand=True)

        lbl_setup_heading = ctk.CTkLabel(
            setup_text_col,
            text="1-Click AI Setup: Install, Start & Configure Brain",
            font=get_font(size=13, weight="bold"),
            text_color=THEME["yellow_text"],
            anchor="w",
        )
        lbl_setup_heading.pack(anchor="w")

        self.lbl_setup_sub = ctk.CTkLabel(
            setup_text_col,
            text="Verifies Ollama installation (v0.3.0+), launches background service, and downloads Llama 3.2 (3B) with one click.",
            font=get_font(size=11),
            text_color=THEME["yellow_text"],
            anchor="w",
        )
        self.lbl_setup_sub.pack(anchor="w")

        self.btn_one_click = ctk.CTkButton(
            setup_top,
            text="🚀 Quick Setup",
            command=self._run_one_click_setup,
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            font=get_font(size=12, weight="bold"),
            height=34,
            width=135,
            corner_radius=6,
            cursor="hand2",
        )
        self.btn_one_click.pack(side="right")

        # Live Progress container for Setup / Pull
        self.progress_container = ctk.CTkFrame(setup_inner, fg_color="transparent")
        self.setup_progress_bar = ctk.CTkProgressBar(
            self.progress_container,
            height=8,
            corner_radius=4,
            progress_color=THEME["denim_blue"],
            fg_color="#e2e8f0",
        )
        self.setup_progress_bar.set(0.0)
        self.lbl_setup_progress = ctk.CTkLabel(
            self.progress_container,
            text="",
            font=get_font(size=11, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )

        # Service Diagnostics & Controls Tile
        diag_tile = ctk.CTkFrame(
            ai_inner,
            fg_color=THEME["card_inner"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border"],
        )
        diag_tile.pack(fill="x", pady=(0, 14))

        diag_inner = ctk.CTkFrame(diag_tile, fg_color="transparent")
        diag_inner.pack(fill="x", padx=16, pady=12)

        # Left: Chips for Host, Version, Models
        chips_frame = ctk.CTkFrame(diag_inner, fg_color="transparent")
        chips_frame.pack(side="left", fill="x", expand=True)

        self.lbl_stat_daemon = ctk.CTkLabel(
            chips_frame,
            text="Daemon: localhost:11434",
            font=get_font(size=12),
            text_color=THEME["text_secondary"],
        )
        self.lbl_stat_daemon.pack(side="left", padx=(0, 16))

        self.lbl_stat_ver = ctk.CTkLabel(
            chips_frame,
            text="Engine: Checking...",
            font=get_font(size=12),
            text_color=THEME["text_secondary"],
        )
        self.lbl_stat_ver.pack(side="left", padx=(0, 16))

        self.lbl_stat_models = ctk.CTkLabel(
            chips_frame,
            text="Models: 0 Installed",
            font=get_font(size=12),
            text_color=THEME["text_secondary"],
        )
        self.lbl_stat_models.pack(side="left")

        # Right: Action Buttons
        self.diag_actions = ctk.CTkFrame(diag_inner, fg_color="transparent")
        self.diag_actions.pack(side="right")

        self.btn_start_service = ctk.CTkButton(
            self.diag_actions,
            text="▶ Start Ollama",
            command=self._start_service_click,
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            height=30,
            font=get_font(size=11, weight="bold"),
            corner_radius=6,
            cursor="hand2",
        )

        self.btn_check_ai = ctk.CTkButton(
            self.diag_actions,
            text="⟳ Test Ping",
            command=self.check_ai_status,
            fg_color=THEME["card_bg"],
            hover_color=THEME["card_hover"],
            text_color=THEME["text_primary"],
            border_width=1,
            border_color=THEME["border"],
            height=30,
            font=get_font(size=11, weight="bold"),
            corner_radius=6,
            cursor="hand2",
        )
        self.btn_check_ai.pack(side="right")

        # Auto-start switch
        auto_ollama_enabled = self.db.get_setting("auto_start_ollama", default="true").lower() == "true"
        self.switch_auto_ollama = ctk.CTkSwitch(
            ai_inner,
            text="Automatically start Ollama background service when Minion launches",
            command=self._on_toggle_auto_ollama,
            font=get_font(size=12),
            text_color=THEME["text_primary"],
            progress_color=THEME["denim_blue"],
            button_color=THEME["card_bg"],
            button_hover_color=THEME["card_hover"],
            fg_color=THEME["border"],
        )
        if auto_ollama_enabled:
            self.switch_auto_ollama.select()
        else:
            self.switch_auto_ollama.deselect()
        self.switch_auto_ollama.pack(anchor="w", pady=(0, 14))

        # Active Model Selection Row
        model_row = ctk.CTkFrame(ai_inner, fg_color="transparent")
        model_row.pack(fill="x", pady=(0, 14))

        lbl_active_model = ctk.CTkLabel(
            model_row,
            text="Active Model:",
            font=get_font(size=13, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_active_model.pack(side="left", padx=(0, 10))

        self.combo_models = ctk.CTkComboBox(
            model_row,
            values=["None Available"],
            command=self._on_model_selected,
            width=260,
            height=34,
            corner_radius=6,
            border_width=1,
            border_color=THEME["input_border"],
            fg_color=THEME["card_bg"],
            button_color=THEME["card_inner"],
            button_hover_color=THEME["border"],
            dropdown_fg_color=THEME["card_bg"],
            dropdown_hover_color=THEME["yellow_tint"],
            dropdown_text_color=THEME["text_primary"],
            text_color=THEME["text_primary"],
            font=get_font(size=12),
        )
        self.combo_models.pack(side="left", padx=(0, 12))

        self.lbl_model_hint = ctk.CTkLabel(
            model_row,
            text="Active model powers semantic classification, sprints, and standups.",
            font=get_font(size=11),
            text_color=THEME["text_secondary"],
        )
        self.lbl_model_hint.pack(side="left")

        # Curated Model Quick-Picks Card
        curated_frame = ctk.CTkFrame(
            ai_inner,
            fg_color=THEME["card_inner"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border"],
        )
        curated_frame.pack(fill="x", pady=(0, 12))

        curated_inner = ctk.CTkFrame(curated_frame, fg_color="transparent")
        curated_inner.pack(fill="x", padx=14, pady=12)

        lbl_curated_title = ctk.CTkLabel(
            curated_inner,
            text="Recommended Local Brain Models",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_curated_title.pack(anchor="w", pady=(0, 8))

        # 3 Quick-Pick Model Cards Container
        self.cards_row = ctk.CTkFrame(curated_inner, fg_color="transparent")
        self.cards_row.pack(fill="x")
        self.cards_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="model_col")

        # Custom Model Pull Bar
        custom_bar = ctk.CTkFrame(ai_inner, fg_color="transparent")
        custom_bar.pack(fill="x", pady=(2, 0))

        lbl_custom = ctk.CTkLabel(
            custom_bar,
            text="Download Custom Model:",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_secondary"],
        )
        lbl_custom.pack(side="left", padx=(0, 10))

        self.entry_pull_model = ctk.CTkEntry(
            custom_bar,
            placeholder_text="e.g. mistral:7b, phi3:mini, deepseek-r1:1.5b",
            placeholder_text_color=THEME["text_muted"],
            height=32,
            width=280,
            corner_radius=6,
            border_width=1,
            border_color=THEME["input_border"],
            fg_color=THEME["card_bg"],
            text_color=THEME["text_primary"],
            font=get_font(size=12),
        )
        self.entry_pull_model.pack(side="left", padx=(0, 10))

        self.btn_pull = ctk.CTkButton(
            custom_bar,
            text="📥 Download",
            command=self._pull_custom_model_click,
            fg_color=THEME["denim_blue"],
            hover_color=THEME["denim_hover"],
            text_color="#ffffff",
            height=32,
            width=110,
            corner_radius=6,
            font=get_font(size=12, weight="bold"),
            cursor="hand2",
        )
        self.btn_pull.pack(side="left")

        # SECTION 4: Custom Categorization Rules Manager
        rules_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        rules_card.pack(fill="x", pady=(0, 15))

        rules_inner = ctk.CTkFrame(rules_card, fg_color="transparent")
        rules_inner.pack(fill="x", padx=20, pady=18)

        lbl_rules_title = ctk.CTkLabel(
            rules_inner,
            text="🏷️ Custom Work & Task Categorization",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_rules_title.pack(anchor="w", pady=(0, 4))

        lbl_rules_sub = ctk.CTkLabel(
            rules_inner,
            text="Create custom classification rules that take precedence over default heuristics",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
        )
        lbl_rules_sub.pack(anchor="w", pady=(0, 12))

        # Add Rule Form
        form_frame = ctk.CTkFrame(rules_inner, fg_color=THEME["card_inner"], corner_radius=8, border_width=1, border_color=THEME["border"])
        form_frame.pack(fill="x", pady=(0, 15))

        form_inner = ctk.CTkFrame(form_frame, fg_color="transparent")
        form_inner.pack(fill="x", padx=15, pady=12)

        # Type Combo
        self.combo_rule_type = ctk.CTkComboBox(
            form_inner,
            values=["App Executable", "Window Title"],
            width=140,
            height=34,
            corner_radius=6,
            border_width=1,
            border_color=THEME["input_border"],
            fg_color=THEME["card_bg"],
            button_color=THEME["card_inner"],
            button_hover_color=THEME["border"],
            dropdown_fg_color=THEME["card_bg"],
            dropdown_hover_color=THEME["yellow_tint"],
            dropdown_text_color=THEME["text_primary"],
            text_color=THEME["text_primary"],
            font=get_font(size=12),
        )
        self.combo_rule_type.set("App Executable")
        self.combo_rule_type.pack(side="left", padx=(0, 8))

        # Pattern Entry
        self.entry_rule_pattern = ctk.CTkEntry(
            form_inner,
            placeholder_text="Keyword (e.g. myapp.exe or Internal Dashboard)",
            placeholder_text_color=THEME["text_muted"],
            width=240,
            height=34,
            corner_radius=6,
            border_width=1,
            border_color=THEME["input_border"],
            fg_color=THEME["card_bg"],
            text_color=THEME["text_primary"],
            font=get_font(size=12),
        )
        self.entry_rule_pattern.pack(side="left", padx=(0, 8), fill="x", expand=True)

        # Category Combo
        cat_choices = [c for c in CATEGORY_CONFIG.keys() if c != "Idle / Away"]
        self.combo_rule_cat = ctk.CTkComboBox(
            form_inner,
            values=cat_choices,
            width=170,
            height=34,
            corner_radius=6,
            border_width=1,
            border_color=THEME["input_border"],
            fg_color=THEME["card_bg"],
            button_color=THEME["card_inner"],
            button_hover_color=THEME["border"],
            dropdown_fg_color=THEME["card_bg"],
            dropdown_hover_color=THEME["yellow_tint"],
            dropdown_text_color=THEME["text_primary"],
            text_color=THEME["text_primary"],
            font=get_font(size=12),
        )
        self.combo_rule_cat.set("Work / Coding")
        self.combo_rule_cat.pack(side="left", padx=(0, 10))

        # Add Button
        btn_add_rule = ctk.CTkButton(
            form_inner,
            text="+ Add Rule",
            command=self._add_rule,
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            width=100,
            height=34,
            corner_radius=6,
            font=get_font(size=12, weight="bold"),
            cursor="hand2",
        )
        btn_add_rule.pack(side="right")

        # Existing Rules List
        lbl_list = ctk.CTkLabel(
            rules_inner,
            text="Active Custom Rules:",
            font=get_font(size=13, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_list.pack(anchor="w", pady=(0, 6))

        self.rules_list_frame = ctk.CTkFrame(rules_inner, fg_color="transparent")
        self.rules_list_frame.pack(fill="x")

        # SECTION 5: Privacy & Security Protections
        priv_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        priv_card.pack(fill="x", pady=(0, 15))

        priv_inner = ctk.CTkFrame(priv_card, fg_color="transparent")
        priv_inner.pack(fill="x", padx=20, pady=18)

        lbl_priv_title = ctk.CTkLabel(
            priv_inner,
            text="🔒 Privacy Safeguards & Secret Masking",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_priv_title.pack(anchor="w", pady=(0, 4))

        lbl_priv_sub = ctk.CTkLabel(
            priv_inner,
            text=(
                "Activities matching these sensitive keywords are automatically masked as "
                "[Private / Confidential Activity] before being saved to the local database:"
            ),
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
            wraplength=700,
            justify="left",
        )
        lbl_priv_sub.pack(anchor="w", pady=(0, 10))

        # Exclusion pills
        pills_frame = ctk.CTkFrame(priv_inner, fg_color="transparent")
        pills_frame.pack(fill="x")

        for exc in DEFAULT_PRIVACY_EXCLUSIONS:
            pill = ctk.CTkLabel(
                pills_frame,
                text=f"🔒 {exc}",
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_primary"],
                fg_color=THEME["card_inner"],
                corner_radius=4,
                padx=8,
                pady=4,
            )
            pill.pack(side="left", padx=4, pady=4)

    def _on_toggle_auto_start(self) -> None:
        """Persist auto-start setting when user flips the switch."""
        is_enabled = bool(self.switch_auto_start.get())
        self.db.set_setting("auto_start_tracking", "true" if is_enabled else "false")
        self.db.set_setting("tracking_enabled", "true" if is_enabled else "false")

    def _on_toggle_autostart_boot(self) -> None:
        """Toggle Windows startup registry entry."""
        is_enabled = bool(self.switch_autostart_boot.get())
        if is_enabled:
            enable_autostart(minimized=True)
        else:
            disable_autostart()

    def _on_toggle_close_to_tray(self) -> None:
        """Persist close-to-tray preference."""
        is_enabled = bool(self.switch_close_tray.get())
        self.db.set_setting("close_to_tray", "true" if is_enabled else "false")

    def _on_settings_domain_selected(self, choice: str) -> None:
        """Handle domain change from Settings view."""
        domain_key = "general"
        for k, d in FOCUS_DOMAINS.items():
            if choice.startswith(d["icon"]) or d["title"] in choice:
                domain_key = k
                break
        self.db.set_setting("user_focus_domain", domain_key)
        profile = self.db.get_user_profile()
        profile["focus_domain"] = domain_key
        self.db.save_user_profile(profile)

        d_info = FOCUS_DOMAINS.get(domain_key, FOCUS_DOMAINS["general"])
        if hasattr(self, "lbl_domain_desc"):
            self.lbl_domain_desc.configure(text=d_info["tagline"])

    def _on_toggle_auto_ollama(self) -> None:
        """Persist auto-start Ollama setting when user flips switch."""
        is_enabled = bool(self.switch_auto_ollama.get())
        self.db.set_setting("auto_start_ollama", "true" if is_enabled else "false")

    def _start_service_click(self) -> None:
        """Manually trigger background start of Ollama service."""
        self.btn_start_service.configure(text="⏳ Starting...", state="disabled")

        def _run():
            self.ai.start_service(timeout=8.0)
            self.after(0, self.check_ai_status)

        threading.Thread(target=_run, daemon=True).start()

    def _run_one_click_setup(self) -> None:
        """Execute end-to-end 1-click Ollama verification, service startup, and model pull."""
        self.btn_one_click.configure(state="disabled", text="⏳ Working...")
        self.progress_container.pack(fill="x", pady=(8, 0))
        self.setup_progress_bar.pack(fill="x", pady=(0, 4))
        self.lbl_setup_progress.pack(anchor="w")
        self.setup_progress_bar.set(0.05)
        self.lbl_setup_progress.configure(text="Initializing Minion Brain Setup...")

        def _progress(msg: str, pct: float):
            self.after(0, lambda: self._update_setup_progress(msg, pct))

        def _do_setup():
            ok, msg = self.ai.one_click_setup(target_model="llama3.2:3b", progress_callback=_progress)
            self.after(0, lambda: self._on_setup_completed(ok, msg))

        threading.Thread(target=_do_setup, daemon=True).start()

    def _update_setup_progress(self, msg: str, pct: float) -> None:
        """Update live progress bar and label."""
        self.setup_progress_bar.set(pct)
        self.lbl_setup_progress.configure(text=msg)

    def _on_setup_completed(self, success: bool, message: str) -> None:
        """Handle 1-click setup completion."""
        self.btn_one_click.configure(state="normal", text="🚀 Quick Setup")
        self.check_ai_status()
        if success:
            messagebox.showinfo("Brain Setup Complete", "Minion Brain Engine is ready to go!\n\n" + message)
        else:
            messagebox.showwarning("Setup Warning", message)

    def _handle_reopen_wizard(self) -> None:
        """Open the onboarding wizard modal on demand."""
        root = self.winfo_toplevel()
        if hasattr(root, "open_onboarding_wizard"):
            root.open_onboarding_wizard()

    def check_ai_status(self) -> None:
        """Query Ollama connection diagnostics and refresh UI state."""
        diag = self.ai.get_detailed_status()
        status_code = diag.get("status_code", "OFFLINE")
        models = diag.get("models", [])
        version_str = diag.get("version") or "unknown"
        msg = diag.get("message", "")
        latency = diag.get("latency_ms")

        if hasattr(self, "lbl_ai_desc"):
            self.lbl_ai_desc.configure(text=msg)
        self.lbl_stat_ver.configure(text=f"Engine: v{version_str}")
        self.lbl_stat_models.configure(text=f"Models: {len(models)} Installed")

        if diag.get("running"):
            lat_str = f" • {latency}ms" if latency is not None else ""
            self.lbl_stat_daemon.configure(text=f"Daemon: Online{lat_str}", text_color=THEME["badge_success_text"])
            self.btn_start_service.pack_forget()
        else:
            self.lbl_stat_daemon.configure(text="Daemon: Offline", text_color=THEME["badge_danger_text"])
            self.btn_start_service.pack(side="left", padx=(0, 8))

        # Status Badge styling
        if status_code == "READY":
            self.ai_badge.configure(
                text=f"● CONNECTED • v{version_str}",
                text_color=THEME["badge_success_text"],
                fg_color=THEME["badge_success_bg"],
            )
            self.lbl_setup_sub.configure(text=f"Brain is fully configured with {self.ai.model}! Click to re-verify anytime.")
        elif status_code == "NEED_MODEL":
            self.ai_badge.configure(
                text="▲ MODEL REQUIRED",
                text_color=THEME["badge_warning_text"],
                fg_color=THEME["badge_warning_bg"],
            )
            self.lbl_setup_sub.configure(text="Ollama is running. Click Quick Setup to download recommended Llama 3.2 (3B).")
        elif status_code == "NOT_RUNNING":
            self.ai_badge.configure(
                text="○ SERVICE STOPPED",
                text_color=THEME["badge_warning_text"],
                fg_color=THEME["badge_warning_bg"],
            )
            self.lbl_setup_sub.configure(text="Ollama is installed. Click Quick Setup to launch service and verify model.")
        elif status_code == "UPDATE_NEEDED":
            self.ai_badge.configure(
                text=f"▲ UPDATE RECOMMENDED (v{version_str})",
                text_color=THEME["badge_warning_text"],
                fg_color=THEME["badge_warning_bg"],
            )
            self.lbl_setup_sub.configure(text="Click Quick Setup to upgrade Ollama to latest version.")
        else:  # NOT_INSTALLED
            self.ai_badge.configure(
                text="✕ NOT INSTALLED",
                text_color=THEME["badge_danger_text"],
                fg_color=THEME["badge_danger_bg"],
            )
            self.lbl_setup_sub.configure(text="Ollama not detected. Click Quick Setup to install automatically.")

        # Update Models Dropdown
        if models:
            self.combo_models.configure(values=models)
            if self.ai.model in models:
                self.combo_models.set(self.ai.model)
            else:
                self.combo_models.set(models[0])
                self.ai.model = models[0]
        else:
            self.combo_models.configure(values=["No models found"])
            self.combo_models.set("No models found")

        # Render Curated Model Quick-Pick Cards
        self._render_curated_cards(models)

    def _render_curated_cards(self, installed_models: list) -> None:
        """Render 3 clean curated model tiles with 1-click download/use actions."""
        for child in self.cards_row.winfo_children():
            child.destroy()

        curated = [
            ("llama3.2:3b", "Llama 3.2 (3B)", "Recommended • 2.0GB", "Best balance of reasoning & low RAM"),
            ("llama3.2:1b", "Llama 3.2 (1B)", "Ultra Fast • 1.3GB", "Instant speed on battery / low-spec PCs"),
            ("qwen2.5:3b", "Qwen 2.5 (3B)", "Coding Focus • 1.9GB", "Superb precision for code & analysis"),
        ]

        installed_bases = [m.split(":")[0] for m in installed_models] + installed_models

        for idx, (tag, title, badge, desc) in enumerate(curated):
            card = ctk.CTkFrame(
                self.cards_row,
                fg_color=THEME["card_bg"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            card.grid(row=0, column=idx, padx=4, pady=2, sticky="nsew")

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=12, pady=10)

            top_row = ctk.CTkFrame(inner, fg_color="transparent")
            top_row.pack(fill="x", pady=(0, 2))

            lbl_title = ctk.CTkLabel(
                top_row,
                text=title,
                font=get_font(size=12, weight="bold"),
                text_color=THEME["text_primary"],
            )
            lbl_title.pack(side="left")

            lbl_badge = ctk.CTkLabel(
                inner,
                text=badge,
                font=get_font(size=10, weight="bold"),
                text_color=THEME["denim_blue"],
            )
            lbl_badge.pack(anchor="w", pady=(0, 2))

            lbl_desc = ctk.CTkLabel(
                inner,
                text=desc,
                font=get_font(size=10),
                text_color=THEME["text_secondary"],
                wraplength=180,
                justify="left",
            )
            lbl_desc.pack(anchor="w", pady=(0, 8))

            is_installed = tag in installed_models or tag.split(":")[0] in installed_bases
            is_active = self.ai.model == tag or (self.ai.model.split(":")[0] == tag.split(":")[0] and is_installed)

            if is_active:
                btn_action = ctk.CTkButton(
                    inner,
                    text="✓ Active Model",
                    state="disabled",
                    fg_color=THEME["badge_success_bg"],
                    text_color=THEME["badge_success_text"],
                    height=26,
                    font=get_font(size=11, weight="bold"),
                    corner_radius=5,
                )
            elif is_installed:
                btn_action = ctk.CTkButton(
                    inner,
                    text="Select Model",
                    command=lambda t=tag: self._select_curated_model(t),
                    fg_color=THEME["card_inner"],
                    hover_color=THEME["card_hover"],
                    text_color=THEME["text_primary"],
                    border_width=1,
                    border_color=THEME["border"],
                    height=26,
                    font=get_font(size=11, weight="bold"),
                    corner_radius=5,
                    cursor="hand2",
                )
            else:
                btn_action = ctk.CTkButton(
                    inner,
                    text="📥 Download",
                    command=lambda t=tag: self._pull_model_stream(t),
                    fg_color=THEME["denim_blue"],
                    hover_color=THEME["denim_hover"],
                    text_color="#ffffff",
                    height=26,
                    font=get_font(size=11, weight="bold"),
                    corner_radius=5,
                    cursor="hand2",
                )
            btn_action.pack(fill="x")

    def _select_curated_model(self, tag: str) -> None:
        """Select an already installed model as active."""
        self.ai.model = tag
        self.check_ai_status()

    def _pull_custom_model_click(self) -> None:
        """Handle custom model input download button click."""
        name = self.entry_pull_model.get().strip()
        if not name:
            return
        self._pull_model_stream(name)

    def _pull_model_stream(self, model_name: str) -> None:
        """Stream pull a model with real-time UI percentage feedback."""
        self.progress_container.pack(fill="x", pady=(8, 0))
        self.setup_progress_bar.pack(fill="x", pady=(0, 4))
        self.lbl_setup_progress.pack(anchor="w")
        self.setup_progress_bar.set(0.02)
        self.lbl_setup_progress.configure(text=f"Connecting to pull {model_name}...")
        self.btn_pull.configure(state="disabled", text="Pulling...")

        def _progress(msg: str, pct: float):
            self.after(0, lambda: self._update_setup_progress(msg, pct))

        def _do_pull():
            ok, msg = self.ai.pull_model_stream(model_name, progress_callback=_progress)
            self.after(0, lambda: self._on_pull_complete(model_name, ok, msg))

        threading.Thread(target=_do_pull, daemon=True).start()

    def _on_pull_complete(self, model_name: str, success: bool, msg: str = "") -> None:
        """Callback when pull completes."""
        self.btn_pull.configure(state="normal", text="📥 Download")
        self.check_ai_status()
        if success:
            self.ai.model = model_name
            self.check_ai_status()
            messagebox.showinfo("Model Ready", f"Successfully pulled and activated {model_name}!")
        else:
            messagebox.showwarning("Download Incomplete", f"Could not pull {model_name}:\n{msg}")

    def _on_model_selected(self, choice: str) -> None:
        """Handle model dropdown change."""
        if choice and choice not in ("None Available", "No models found", "Ollama Offline"):
            self.ai.model = choice
            self.check_ai_status()

    def _add_rule(self) -> None:
        """Add new custom rule to DB."""
        ptype_raw = self.combo_rule_type.get()
        ptype = "app" if "App" in ptype_raw else "title"
        pattern = self.entry_rule_pattern.get().strip()
        category = self.combo_rule_cat.get()

        if not pattern:
            return

        self.db.add_custom_rule(ptype, pattern, category)
        self.entry_rule_pattern.delete(0, "end")
        self._load_custom_rules()

        if self.on_rules_changed:
            self.on_rules_changed()

    def _delete_rule(self, rule_id: int) -> None:
        """Delete custom rule."""
        self.db.delete_custom_rule(rule_id)
        self._load_custom_rules()
        if self.on_rules_changed:
            self.on_rules_changed()

    def _load_custom_rules(self) -> None:
        """Render active custom rules list."""
        for child in self.rules_list_frame.winfo_children():
            child.destroy()

        rules = self.db.get_custom_rules()
        if not rules:
            lbl_none = ctk.CTkLabel(
                self.rules_list_frame,
                text="No custom rules defined yet. Add one above to customize categorization.",
                font=get_font(size=12),
                text_color=THEME["text_secondary"],
            )
            lbl_none.pack(pady=10)
            return

        for r in rules:
            row = ctk.CTkFrame(self.rules_list_frame, fg_color=THEME["card_inner"], corner_radius=6, height=38, border_width=1, border_color=THEME["border"])
            row.pack(fill="x", pady=3)

            type_badge = ctk.CTkLabel(
                row,
                text=r["pattern_type"].upper(),
                font=get_font(size=10, weight="bold"),
                text_color=THEME["denim_blue"],
                width=50,
            )
            type_badge.pack(side="left", padx=(10, 4))

            pattern_lbl = ctk.CTkLabel(
                row,
                text=f'"{r["pattern"]}"',
                font=get_font(size=12, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            pattern_lbl.pack(side="left", padx=8, fill="x", expand=True)

            cat_pill = ctk.CTkLabel(
                row,
                text=r["category"],
                font=get_font(size=10, weight="bold"),
                text_color="#ffffff",
                fg_color=CATEGORY_CONFIG.get(r["category"], {}).get("color", "#475569"),
                corner_radius=4,
                padx=8,
                pady=2,
            )
            cat_pill.pack(side="left", padx=10)

            btn_del = ctk.CTkButton(
                row,
                text="✕ Delete",
                command=lambda rid=r["id"]: self._delete_rule(rid),
                fg_color=THEME["card_bg"],
                hover_color="#fef2f2",
                text_color="#dc2626",
                border_width=1,
                border_color=THEME["border"],
                height=26,
                width=75,
                font=get_font(size=10, weight="bold"),
                corner_radius=4,
                cursor="hand2",
            )
            btn_del.pack(side="right", padx=(4, 10))
