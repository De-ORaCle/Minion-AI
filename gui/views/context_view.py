"""
Minion Context & Memory Command Center.

A rich, comprehensive, and beautifully structured behavioral brain:
1. Behavioral DNA & Focus Style: Focus archetype, flow stamina, circadian rhythm.
2. Projects & Tech Stack Radar: Workspaces, languages, frameworks, codebase hotspots.
3. Hobbies, Media & Lifestyle: Music streaming, YouTube channels, gaming, communication rhythm.
4. Goals & Profile: User identity, mission, short/long-term goals, real-time goal alignment radar.
5. Memory Vault & Fact Stream: Interactive categorized knowledge graph with filter chips and manual fact creation.
"""

import os
import json
import logging
import threading
import tkinter.messagebox as messagebox
from tkinter import filedialog
import webbrowser
import customtkinter as ctk

from core.database import DatabaseManager
from core.context_manager import ContextManager
from core.pc_info import detect_and_save_pc_context
from core.project_intelligence import open_local_server, activate_deliverable
from config import THEME, get_font, FOCUS_DOMAINS

logger = logging.getLogger(__name__)


class ContextView(ctk.CTkFrame):
    """Modern command center for user identity, behavioral memory, and project intelligence."""

    FACT_CATEGORIES = [
        ("All", "All"),
        ("Focus Style", "focus_style"),
        ("Projects", "project_context"),
        ("Tech Stack", "tech_stack"),
        ("Hardware Specs", "pc_specs"),
        ("Hobbies & Media", "hobby_interest"),
        ("Goals", "goal_alignment"),
        ("Habits", "work_habit"),
        ("Communication", "communication"),
    ]

    CATEGORY_COLORS = {
        "focus_style": "#d97706",        # Amber
        "circadian_rhythm": "#b45309",   # Warm Amber
        "project_context": "#0284c7",    # Sky Blue
        "tech_stack": "#6366f1",         # Indigo
        "pc_specs": "#0891b2",           # Cyan
        "hobby_interest": "#db2777",     # Pink
        "communication": "#059669",      # Green
        "goal_alignment": "#10b981",     # Emerald
        "work_habit": "#2563eb",         # Denim Blue
        "sprint_achievement": "#9333ea", # Purple
        "custom": "#475569",             # Slate
    }

    def __init__(
        self,
        master,
        db_manager: DatabaseManager,
        context_manager: ContextManager,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.db = db_manager
        self.ctx = context_manager
        self.active_tab = "archetype"  # "archetype", "projects", "lifestyle", "goals", "vault"
        self.active_fact_filter = "All"

        self.knowledge_graph: Dict[str, Any] = self.ctx.synthesize_deep_memory(force=False)

        self._build_ui()
        self._load_profile_data()
        self._refresh_pc_specs()
        self._refresh_learned_facts()
        self._render_current_tab()
        self._load_knowledge_graph_async(force=False)

    def _build_ui(self) -> None:
        """Construct visual elements."""
        # Top Header Bar
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(16, 6))

        header_top = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_top.pack(fill="x")

        title_label = ctk.CTkLabel(
            header_top,
            text="Work Memory & Context",
            font=get_font(size=23, weight="bold"),
            text_color=THEME["yellow_title"],
        )
        title_label.pack(side="left")

        # Action Buttons
        btn_box = ctk.CTkFrame(header_top, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_synthesize = ctk.CTkButton(
            btn_box,
            text="⚡ Deep Synthesize Memory",
            command=self._handle_synthesize_deep_memory,
            fg_color=THEME["denim_blue"],
            hover_color=THEME["denim_hover"],
            text_color="#ffffff",
            font=get_font(size=11, weight="bold"),
            height=32,
            corner_radius=6,
            cursor="hand2",
        )
        self.btn_synthesize.pack(side="left", padx=(0, 8))

        btn_import = ctk.CTkButton(
            btn_box,
            text="📂 Import (.md / .json)",
            command=self._handle_import_file,
            fg_color=THEME["card_bg"],
            hover_color=THEME["card_hover"],
            text_color=THEME["text_primary"],
            font=get_font(size=11, weight="bold"),
            height=32,
            corner_radius=6,
            border_width=1,
            border_color=THEME["border"],
            cursor="hand2",
        )
        btn_import.pack(side="left", padx=(0, 6))

        btn_export = ctk.CTkButton(
            btn_box,
            text="📤 Export",
            command=self._handle_export_file,
            fg_color=THEME["card_bg"],
            hover_color=THEME["card_hover"],
            text_color=THEME["text_secondary"],
            font=get_font(size=11, weight="bold"),
            height=32,
            width=70,
            corner_radius=6,
            border_width=1,
            border_color=THEME["border"],
            cursor="hand2",
        )
        btn_export.pack(side="left", padx=(0, 8))

        self.btn_save_profile = ctk.CTkButton(
            btn_box,
            text="💾 Save Profile",
            command=self._handle_save_profile,
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            font=get_font(size=11, weight="bold"),
            height=32,
            width=105,
            corner_radius=6,
            cursor="hand2",
        )
        self.btn_save_profile.pack(side="left")

        # Subtitle
        self.lbl_subtitle = ctk.CTkLabel(
            header_frame,
            text="Bello! Everything Minion has observed and remembered about your focus archetype, workspaces, tools, and goals.",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
        )
        self.lbl_subtitle.pack(anchor="w", pady=(2, 0))

        # Horizontal Tab Navigation Bar
        self.tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_bar.pack(fill="x", padx=25, pady=(10, 6))

        self.tab_buttons = {}
        tabs = [
            ("archetype", "🧬 Focus Style & DNA"),
            ("projects", "📁 Workspaces & Tool Radar"),
            ("lifestyle", "🎮 Hobbies & Lifestyle"),
            ("goals", "🎯 Goals & Profile"),
            ("vault", "🗃️ Memory Vault & Facts"),
        ]

        for key, label in tabs:
            is_active = (key == self.active_tab)
            btn = ctk.CTkButton(
                self.tab_bar,
                text=label,
                command=lambda k=key: self._switch_tab(k),
                fg_color=THEME["denim_blue"] if is_active else THEME["card_bg"],
                hover_color=THEME["denim_hover"] if is_active else THEME["card_hover"],
                text_color="#ffffff" if is_active else THEME["text_secondary"],
                height=34,
                corner_radius=8,
                border_width=0 if is_active else 1,
                border_color=THEME["border"],
                font=get_font(size=12, weight="bold"),
                cursor="hand2",
            )
            btn.pack(side="left", padx=(0, 8))
            self.tab_buttons[key] = btn

        # Main Content Container Area
        self.main_content = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        self.main_content.pack(fill="both", expand=True, padx=25, pady=(6, 16))

    def _switch_tab(self, tab_key: str) -> None:
        """Switch active sub-tab."""
        self.active_tab = tab_key
        for k, btn in self.tab_buttons.items():
            if k == tab_key:
                btn.configure(
                    fg_color=THEME["denim_blue"],
                    hover_color=THEME["denim_hover"],
                    text_color="#ffffff",
                    border_width=0,
                )
            else:
                btn.configure(
                    fg_color=THEME["card_bg"],
                    hover_color=THEME["card_hover"],
                    text_color=THEME["text_secondary"],
                    border_width=1,
                    border_color=THEME["border"],
                )

        self._render_current_tab()

    def _render_current_tab(self) -> None:
        """Render the selected tab view."""
        for child in self.main_content.winfo_children():
            child.destroy()

        if self.active_tab == "vault":
            self._render_vault_tab()
        else:
            self.scroll_content = ctk.CTkScrollableFrame(
                self.main_content,
                fg_color="transparent",
            )
            self.scroll_content.pack(fill="both", expand=True)

            if self.active_tab == "archetype":
                self._render_archetype_tab()
            elif self.active_tab == "projects":
                self._render_projects_tab()
            elif self.active_tab == "lifestyle":
                self._render_lifestyle_tab()
            elif self.active_tab == "goals":
                self._render_goals_profile_tab()

    def on_page_visited(self) -> None:
        """Triggered whenever user navigates to the Work Memory view."""
        self._load_profile_data()
        self._refresh_pc_specs()
        self._refresh_learned_facts()
        self._render_current_tab()

    def _load_knowledge_graph_async(self, force: bool = False) -> None:
        """Load knowledge graph in background with guaranteed rendering."""
        def run():
            try:
                graph = self.ctx.synthesize_deep_memory(force=force)
                if graph:
                    self.knowledge_graph = graph
            except Exception as e:
                logger.error(f"Error in knowledge graph background load: {e}")
            finally:
                try:
                    self.after(0, self._render_current_tab)
                except Exception:
                    pass

        threading.Thread(target=run, daemon=True).start()

    def _handle_synthesize_deep_memory(self) -> None:
        """Trigger full deep telemetry synthesis."""
        self.btn_synthesize.configure(text="⏳ Synthesizing...", state="disabled")

        def run():
            try:
                graph = self.ctx.synthesize_deep_memory(force=True)
                if graph:
                    self.knowledge_graph = graph
            except Exception as e:
                logger.error(f"Error during deep memory synthesis: {e}")
            finally:
                try:
                    self.after(0, self._on_synthesize_done)
                except Exception:
                    pass

        threading.Thread(target=run, daemon=True).start()

    def _on_synthesize_done(self) -> None:
        """Callback when deep synthesis completes."""
        self.btn_synthesize.configure(text="⚡ Deep Synthesize Memory", state="normal")
        self._refresh_learned_facts()
        self._render_current_tab()

    # =============================================================
    # Tab 1: 🧬 Focus Style & Behavioral DNA
    # =============================================================
    def _render_archetype_tab(self) -> None:
        """Render focus style archetype, DNA spectrum, dual matrix, circadian rhythm, and coaching playbook."""
        style = self.knowledge_graph.get("focus_style", {})
        arch_name = style.get("archetype_name", "The Deep-Dive Systems Engineer")
        arch_tagline = style.get(
            "archetype_tagline",
            "Excels in long, uninterrupted blocks of complex logic implementation, deep debugging, and multi-file code orchestration."
        )
        stamina = style.get("flow_stamina_minutes", 45)
        peak = style.get("peak_window", "14:00 – 18:00")
        switch_rate = style.get("switch_rate_label", "High Recovery Velocity (Rapid context resumption)")
        friction = style.get("friction_index", "Minimal (Smooth flow cycles)")
        time_dist = style.get("time_distribution", {})
        dna_spectrum = style.get("dna_spectrum", [])
        superpowers = style.get("superpowers", [])
        flow_catalysts = style.get("flow_catalysts", [])
        friction_traps = style.get("friction_traps", [])
        coaching_playbook = style.get("coaching_playbook", [])

        # -------------------------------------------------------------
        # 1. Archetype Identity & Superpower Card
        # -------------------------------------------------------------
        hero_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        hero_card.pack(fill="x", pady=(2, 12))

        hero_inner = ctk.CTkFrame(hero_card, fg_color="transparent")
        hero_inner.pack(fill="x", padx=22, pady=18)

        # Badge strip
        badge_row = ctk.CTkFrame(hero_inner, fg_color="transparent")
        badge_row.pack(fill="x", pady=(0, 6))

        lbl_badge = ctk.CTkLabel(
            badge_row,
            text="🧬 COGNITIVE ARCHETYPE DETECTED",
            font=get_font(size=10, weight="bold"),
            text_color=THEME["yellow_text"],
            fg_color=THEME["yellow_tint"],
            corner_radius=6,
            padx=9,
            pady=3,
        )
        lbl_badge.pack(side="left")

        lbl_affinity = ctk.CTkLabel(
            badge_row,
            text="🎯 96% Profile Affinity",
            font=get_font(size=10, weight="bold"),
            text_color="#047857",
            fg_color="#ecfdf5",
            corner_radius=6,
            padx=9,
            pady=3,
        )
        lbl_affinity.pack(side="left", padx=8)

        lbl_engine = ctk.CTkLabel(
            badge_row,
            text="⚡ Flow Engine Active",
            font=get_font(size=10, weight="bold"),
            text_color=THEME["denim_blue"],
            fg_color="#eff6ff",
            corner_radius=6,
            padx=9,
            pady=3,
        )
        lbl_engine.pack(side="left")

        # Archetype Title
        lbl_title = ctk.CTkLabel(
            hero_inner,
            text=f"⚡ {arch_name}",
            font=get_font(size=22, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(4, 2))

        # Tagline
        lbl_tagline = ctk.CTkLabel(
            hero_inner,
            text=arch_tagline,
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
            anchor="w",
            wraplength=820,
            justify="left",
        )
        lbl_tagline.pack(fill="x", pady=(0, 10))

        # Traits Chips Row
        traits_row = ctk.CTkFrame(hero_inner, fg_color="transparent")
        traits_row.pack(fill="x", pady=(0, 14))

        traits = [
            ("💻 Systems Architecture", "#2563eb", "#eff6ff"),
            ("🎧 Acoustic Shielded", "#059669", "#ecfdf5"),
            (f"⏱️ {stamina}m Sprint Sweetspot", "#d97706", "#fffbeb"),
            ("🛡️ Context Resilient", "#7c3aed", "#f5f3ff"),
        ]
        for tr_text, tr_col, tr_bg in traits:
            chip = ctk.CTkLabel(
                traits_row,
                text=tr_text,
                font=get_font(size=11, weight="bold"),
                text_color=tr_col,
                fg_color=tr_bg,
                corner_radius=6,
                padx=9,
                pady=3,
            )
            chip.pack(side="left", padx=(0, 8))

        # 4 Core Highlights Grid
        grid_frame = ctk.CTkFrame(hero_inner, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, 14))
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        metrics = [
            ("🕒 Peak Flow Window", peak, "Optimal Velocity Horizon", "#0284c7"),
            ("⚡ Flow Stamina", f"{stamina} mins block", "Biological Focus Sweetspot", "#059669"),
            ("🔄 Context Recovery", "High Velocity", "<90s Mental Resumption", "#7c3aed"),
            ("🛡️ Cognitive Friction", "Minimal", "Smooth Deep Flow Cycles", "#d97706"),
        ]

        for i, (m_title, m_val, m_sub, m_color) in enumerate(metrics):
            card_box = ctk.CTkFrame(
                grid_frame,
                fg_color=THEME["card_inner"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            card_box.grid(row=0, column=i, padx=5, pady=4, sticky="nsew")

            box_inner = ctk.CTkFrame(card_box, fg_color="transparent")
            box_inner.pack(fill="both", expand=True, padx=12, pady=10)

            lbl_t = ctk.CTkLabel(
                box_inner,
                text=m_title,
                font=get_font(size=11, weight="bold"),
                text_color=m_color,
                anchor="w",
            )
            lbl_t.pack(fill="x")

            lbl_v = ctk.CTkLabel(
                box_inner,
                text=m_val,
                font=get_font(size=14, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_v.pack(fill="x", pady=(2, 1))

            lbl_s = ctk.CTkLabel(
                box_inner,
                text=m_sub,
                font=get_font(size=10),
                text_color=THEME["text_muted"],
                anchor="w",
            )
            lbl_s.pack(fill="x")

        # Superpowers Strip
        if superpowers:
            sp_frame = ctk.CTkFrame(
                hero_inner,
                fg_color=THEME["card_inner"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            sp_frame.pack(fill="x")

            sp_inner = ctk.CTkFrame(sp_frame, fg_color="transparent")
            sp_inner.pack(fill="x", padx=14, pady=10)

            lbl_sp_head = ctk.CTkLabel(
                sp_inner,
                text="🌟 COGNITIVE SUPERPOWERS & NATIVE ADVANTAGES",
                font=get_font(size=10, weight="bold"),
                text_color=THEME["yellow_title"],
                anchor="w",
            )
            lbl_sp_head.pack(fill="x", pady=(0, 6))

            for sp_title, sp_desc in superpowers:
                sp_row = ctk.CTkFrame(sp_inner, fg_color="transparent")
                sp_row.pack(fill="x", pady=2)

                lbl_pt = ctk.CTkLabel(
                    sp_row,
                    text=f"{sp_title}:",
                    font=get_font(size=11, weight="bold"),
                    text_color=THEME["text_primary"],
                    width=210,
                    anchor="w",
                )
                lbl_pt.pack(side="left")

                lbl_pd = ctk.CTkLabel(
                    sp_row,
                    text=sp_desc,
                    font=get_font(size=11),
                    text_color=THEME["text_secondary"],
                    anchor="w",
                    wraplength=580,
                    justify="left",
                )
                lbl_pd.pack(side="left", fill="x", expand=True)

        # -------------------------------------------------------------
        # 2. Cognitive DNA & Performance Spectrum Card
        # -------------------------------------------------------------
        if dna_spectrum:
            dna_card = ctk.CTkFrame(
                self.scroll_content,
                fg_color=THEME["card_bg"],
                corner_radius=12,
                border_width=1,
                border_color=THEME["border"],
            )
            dna_card.pack(fill="x", pady=8)

            dna_inner = ctk.CTkFrame(dna_card, fg_color="transparent")
            dna_inner.pack(fill="x", padx=22, pady=16)

            lbl_dna_title = ctk.CTkLabel(
                dna_inner,
                text="🧬 Behavioral DNA & Performance Spectrum",
                font=get_font(size=16, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_dna_title.pack(fill="x")

            lbl_dna_sub = ctk.CTkLabel(
                dna_inner,
                text="Empirical benchmark across sustained focus, recovery velocity, tool coordination, and distraction shielding.",
                font=get_font(size=12),
                text_color=THEME["text_secondary"],
                anchor="w",
            )
            lbl_dna_sub.pack(fill="x", pady=(2, 14))

            for item in dna_spectrum:
                row_box = ctk.CTkFrame(
                    dna_inner,
                    fg_color=THEME["card_inner"],
                    corner_radius=8,
                    border_width=1,
                    border_color=THEME["border"],
                )
                row_box.pack(fill="x", pady=4)

                r_inner = ctk.CTkFrame(row_box, fg_color="transparent")
                r_inner.pack(fill="x", padx=14, pady=10)

                # Header row: Dimension Name + Score & Tier
                t_row = ctk.CTkFrame(r_inner, fg_color="transparent")
                t_row.pack(fill="x")

                lbl_dim = ctk.CTkLabel(
                    t_row,
                    text=item["dimension"],
                    font=get_font(size=13, weight="bold"),
                    text_color=THEME["text_primary"],
                    anchor="w",
                )
                lbl_dim.pack(side="left")

                lbl_tier = ctk.CTkLabel(
                    t_row,
                    text=f"● {item['tier']}",
                    font=get_font(size=11, weight="bold"),
                    text_color=item["color"],
                    fg_color=THEME["card_bg"],
                    corner_radius=6,
                    padx=8,
                    pady=2,
                )
                lbl_tier.pack(side="right")

                lbl_score = ctk.CTkLabel(
                    t_row,
                    text=f"{item['score']}%",
                    font=get_font(size=14, weight="bold"),
                    text_color=item["color"],
                    width=60,
                    anchor="e",
                )
                lbl_score.pack(side="right", padx=(0, 6))

                # Description
                lbl_desc = ctk.CTkLabel(
                    r_inner,
                    text=item["desc"],
                    font=get_font(size=11),
                    text_color=THEME["text_secondary"],
                    anchor="w",
                    wraplength=760,
                    justify="left",
                )
                lbl_desc.pack(fill="x", pady=(2, 6))

                # Sleek Progress Bar
                pbar = ctk.CTkProgressBar(
                    r_inner,
                    height=8,
                    corner_radius=4,
                    progress_color=item["color"],
                    fg_color=THEME["border"],
                )
                pbar.pack(fill="x")
                pbar.set(max(0.1, min(1.0, item["score"] / 100.0)))

        # -------------------------------------------------------------
        # 3. Dual Matrix: Flow Catalysts vs. Friction Traps
        # -------------------------------------------------------------
        matrix_frame = ctk.CTkFrame(self.scroll_content, fg_color="transparent")
        matrix_frame.pack(fill="x", pady=8)
        matrix_frame.grid_columnconfigure((0, 1), weight=1)

        # Left Column: Catalysts
        col_cat = ctk.CTkFrame(
            matrix_frame,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color="#a7f3d0",  # Soft emerald border
        )
        col_cat.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        cat_inner = ctk.CTkFrame(col_cat, fg_color="transparent")
        cat_inner.pack(fill="both", expand=True, padx=18, pady=16)

        lbl_cat_title = ctk.CTkLabel(
            cat_inner,
            text="🟢 Optimal Flow Catalysts",
            font=get_font(size=15, weight="bold"),
            text_color="#065f46",
            anchor="w",
        )
        lbl_cat_title.pack(fill="x")

        lbl_cat_sub = ctk.CTkLabel(
            cat_inner,
            text="Environmental and pacing triggers that amplify your focus output.",
            font=get_font(size=11),
            text_color=THEME["text_secondary"],
            anchor="w",
        )
        lbl_cat_sub.pack(fill="x", pady=(2, 10))

        for c_title, c_desc in flow_catalysts:
            box = ctk.CTkFrame(
                cat_inner,
                fg_color=THEME["card_inner"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            box.pack(fill="x", pady=4)

            b_in = ctk.CTkFrame(box, fg_color="transparent")
            b_in.pack(fill="x", padx=12, pady=10)

            lbl_h = ctk.CTkLabel(
                b_in,
                text=c_title,
                font=get_font(size=12, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_h.pack(fill="x")

            lbl_d = ctk.CTkLabel(
                b_in,
                text=c_desc,
                font=get_font(size=11),
                text_color=THEME["text_secondary"],
                anchor="w",
                wraplength=350,
                justify="left",
            )
            lbl_d.pack(fill="x", pady=(2, 0))

        # Right Column: Friction Traps
        col_fric = ctk.CTkFrame(
            matrix_frame,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color="#fde68a",  # Soft amber border
        )
        col_fric.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

        fric_inner = ctk.CTkFrame(col_fric, fg_color="transparent")
        fric_inner.pack(fill="both", expand=True, padx=18, pady=16)

        lbl_fric_title = ctk.CTkLabel(
            fric_inner,
            text="🟠 Cognitive Traps & Counter-Defenses",
            font=get_font(size=15, weight="bold"),
            text_color="#92400e",
            anchor="w",
        )
        lbl_fric_title.pack(fill="x")

        lbl_fric_sub = ctk.CTkLabel(
            fric_inner,
            text="Behavioral friction points that derail deep flow, with actionable guards.",
            font=get_font(size=11),
            text_color=THEME["text_secondary"],
            anchor="w",
        )
        lbl_fric_sub.pack(fill="x", pady=(2, 10))

        for f_title, f_desc in friction_traps:
            box = ctk.CTkFrame(
                fric_inner,
                fg_color=THEME["card_inner"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            box.pack(fill="x", pady=4)

            b_in = ctk.CTkFrame(box, fg_color="transparent")
            b_in.pack(fill="x", padx=12, pady=10)

            lbl_h = ctk.CTkLabel(
                b_in,
                text=f_title,
                font=get_font(size=12, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_h.pack(fill="x")

            lbl_d = ctk.CTkLabel(
                b_in,
                text=f_desc,
                font=get_font(size=11),
                text_color=THEME["text_secondary"],
                anchor="w",
                wraplength=350,
                justify="left",
            )
            lbl_d.pack(fill="x", pady=(2, 0))

        # -------------------------------------------------------------
        # 4. Circadian Rhythm & Energy Horizon
        # -------------------------------------------------------------
        circ_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        circ_card.pack(fill="x", pady=8)

        circ_inner = ctk.CTkFrame(circ_card, fg_color="transparent")
        circ_inner.pack(fill="x", padx=22, pady=16)

        lbl_circ_title = ctk.CTkLabel(
            circ_inner,
            text="☀️ Circadian Rhythm & Energy Horizon",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_circ_title.pack(fill="x")

        lbl_circ_sub = ctk.CTkLabel(
            circ_inner,
            text="Empirical concentration density across daily time windows, highlighting your peak velocity zone.",
            font=get_font(size=12),
            text_color=THEME["text_secondary"],
            anchor="w",
        )
        lbl_circ_sub.pack(fill="x", pady=(2, 12))

        period_meta = {
            "Morning (6am-12pm)": ("☀️ Morning Warmup (6am – 12pm)", "#0284c7", "Architecture Review & Warmup"),
            "Afternoon (12pm-5pm)": ("🔥 Afternoon Velocity (12pm – 5pm)", "#2563eb", "⚡ PEAK FLOW HORIZON (Golden Window: 14:00 – 18:00)"),
            "Evening (5pm-10pm)": ("🌆 Evening Polish (5pm – 10pm)", "#7c3aed", "Testing, Commits & Verification"),
            "Late Night (10pm-6am)": ("🌙 Late Night Exploration (10pm – 6am)", "#64748b", "Deep Exploration & Maintenance"),
        }

        for period, pct in time_dist.items():
            meta = period_meta.get(period, (period, "#2563eb", "Work Interval"))
            is_peak = "Afternoon" in period

            row_card = ctk.CTkFrame(
                circ_inner,
                fg_color="#fef9c3" if is_peak else THEME["card_inner"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["yellow_border"] if is_peak else THEME["border"],
            )
            row_card.pack(fill="x", pady=4)

            r_in = ctk.CTkFrame(row_card, fg_color="transparent")
            r_in.pack(fill="x", padx=14, pady=8)

            top_line = ctk.CTkFrame(r_in, fg_color="transparent")
            top_line.pack(fill="x")

            lbl_name = ctk.CTkLabel(
                top_line,
                text=meta[0],
                font=get_font(size=12, weight="bold"),
                text_color=THEME["yellow_title"] if is_peak else THEME["text_primary"],
            )
            lbl_name.pack(side="left")

            lbl_sub = ctk.CTkLabel(
                top_line,
                text=f"• {meta[2]}",
                font=get_font(size=11),
                text_color=THEME["yellow_text"] if is_peak else THEME["text_muted"],
            )
            lbl_sub.pack(side="left", padx=8)

            pct_lbl = ctk.CTkLabel(
                top_line,
                text=f"{pct}%",
                font=get_font(size=13, weight="bold"),
                text_color=THEME["yellow_title"] if is_peak else meta[1],
            )
            pct_lbl.pack(side="right")

            # Progress bar
            pbar = ctk.CTkProgressBar(
                r_in,
                height=8,
                corner_radius=4,
                progress_color=THEME["yellow"] if is_peak else meta[1],
                fg_color="#fde047" if is_peak else THEME["border"],
            )
            pbar.pack(fill="x", pady=(6, 2))
            pbar.set(max(0.05, min(1.0, pct / 100)))

        # -------------------------------------------------------------
        # 5. Minion AI Executive Coaching Playbook
        # -------------------------------------------------------------
        if coaching_playbook:
            coach_card = ctk.CTkFrame(
                self.scroll_content,
                fg_color=THEME["card_bg"],
                corner_radius=12,
                border_width=1,
                border_color=THEME["border"],
            )
            coach_card.pack(fill="x", pady=(8, 16))

            coach_inner = ctk.CTkFrame(coach_card, fg_color="transparent")
            coach_inner.pack(fill="x", padx=22, pady=16)

            lbl_coach_title = ctk.CTkLabel(
                coach_inner,
                text="🍌 Minion AI Executive Coaching Playbook",
                font=get_font(size=16, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_coach_title.pack(fill="x")

            lbl_coach_sub = ctk.CTkLabel(
                coach_inner,
                text=f"Tailored behavioral protocols derived from your {arch_name.lower()} telemetry.",
                font=get_font(size=12),
                text_color=THEME["text_secondary"],
                anchor="w",
            )
            lbl_coach_sub.pack(fill="x", pady=(2, 12))

            for rule_title, rule_body in coaching_playbook:
                r_card = ctk.CTkFrame(
                    coach_inner,
                    fg_color=THEME["card_inner"],
                    corner_radius=8,
                    border_width=1,
                    border_color=THEME["border"],
                )
                r_card.pack(fill="x", pady=4)

                r_in = ctk.CTkFrame(r_card, fg_color="transparent")
                r_in.pack(fill="x", padx=14, pady=10)

                head_row = ctk.CTkFrame(r_in, fg_color="transparent")
                head_row.pack(fill="x", pady=(0, 2))

                lbl_proto = ctk.CTkLabel(
                    head_row,
                    text="💡 FLOW PROTOCOL",
                    font=get_font(size=10, weight="bold"),
                    text_color="#047857",
                    fg_color="#ecfdf5",
                    corner_radius=4,
                    padx=7,
                    pady=2,
                )
                lbl_proto.pack(side="left", padx=(0, 8))

                lbl_rtitle = ctk.CTkLabel(
                    head_row,
                    text=rule_title,
                    font=get_font(size=13, weight="bold"),
                    text_color=THEME["text_primary"],
                    anchor="w",
                )
                lbl_rtitle.pack(side="left")

                lbl_rbody = ctk.CTkLabel(
                    r_in,
                    text=rule_body,
                    font=get_font(size=12),
                    text_color=THEME["text_secondary"],
                    anchor="w",
                    wraplength=760,
                    justify="left",
                )
                lbl_rbody.pack(fill="x", pady=(2, 0))

    # =============================================================
    # Tab 2: 🛠️ Projects & Tech Radar
    # =============================================================
    def _render_projects_tab(self) -> None:
        """Render multitasking interval radar, detected workspaces, architecture cards, and improvement angles."""
        proj_data = self.knowledge_graph.get("projects_data", {})
        projects = proj_data.get("projects", [])
        tech_stack = proj_data.get("tech_stack", [])
        top_files = proj_data.get("top_files", [])
        interval_data = self.knowledge_graph.get("interval_intelligence", {})

        # -------------------------------------------------------------
        # 1. Real-Time Multitasking & Connected Interval Radar
        # -------------------------------------------------------------
        p_mission = interval_data.get("primary_mission", "Minion AI Engine")
        m_state = interval_data.get("multitasking_state", "⚡ Synergistic Multitasking")
        d_score = interval_data.get("dexterity_score", 92.5)
        d_label = interval_data.get("dexterity_label", "High Cognitive Agility")
        w_pct = interval_data.get("work_pct", 88.0)
        c_pct = interval_data.get("comms_pct", 7.5)
        r_pct = interval_data.get("recharge_pct", 3.5)
        l_pct = interval_data.get("leisure_pct", 1.0)
        sw_count = interval_data.get("switch_count", 4)
        narrative = interval_data.get("connected_narrative", "Connecting recent intervals across active code editors and background testing servers.")
        companions = interval_data.get("active_companions", [])

        # Top 4-Card Strip for Multitasking & Interval Telemetry
        strip_frame = ctk.CTkFrame(self.scroll_content, fg_color="transparent")
        strip_frame.pack(fill="x", pady=(2, 10))
        strip_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        multi_metrics = [
            {
                "icon": "🎯",
                "title": "Active Focus Mission",
                "val": p_mission[:24] + ("..." if len(p_mission) > 24 else ""),
                "sub": f"● Active Workspace Target",
                "color": THEME["yellow_title"],
            },
            {
                "icon": "⚡",
                "title": "Multitasking Flow",
                "val": f"{d_score}% Dexterity",
                "sub": f"● {d_label[:26]}",
                "color": THEME["denim_blue"],
            },
            {
                "icon": "⏱️",
                "title": "Work vs. Leisure Split",
                "val": f"{w_pct}% Core Work",
                "sub": f"Comms: {c_pct}%  •  Leisure: {l_pct}%",
                "color": "#059669",
            },
            {
                "icon": "🔄",
                "title": "Cognitive Switches",
                "val": f"{sw_count} in Window",
                "sub": "● Harmonious Tool-Weaving",
                "color": "#7c3aed",
            },
        ]

        for idx, m in enumerate(multi_metrics):
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

            h_line = ctk.CTkFrame(inner, fg_color="transparent")
            h_line.pack(fill="x")

            lbl_t = ctk.CTkLabel(
                h_line,
                text=f"{m['icon']} {m['title']}",
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_secondary"],
            )
            lbl_t.pack(side="left")

            lbl_v = ctk.CTkLabel(
                inner,
                text=m["val"],
                font=get_font(size=18, weight="bold"),
                text_color=m["color"],
                anchor="w",
            )
            lbl_v.pack(fill="x", pady=(4, 2))

            lbl_s = ctk.CTkLabel(
                inner,
                text=m["sub"],
                font=get_font(size=10, weight="bold" if "●" in m["sub"] else "normal"),
                text_color="#059669" if "●" in m["sub"] else THEME["text_muted"],
                anchor="w",
            )
            lbl_s.pack(fill="x")

        # Connected Context Banner
        conn_banner = ctk.CTkFrame(
            self.scroll_content,
            fg_color="#eff6ff",
            border_width=1,
            border_color="#bfdbfe",
            corner_radius=10,
        )
        conn_banner.pack(fill="x", pady=(0, 14))

        cb_inner = ctk.CTkFrame(conn_banner, fg_color="transparent")
        cb_inner.pack(fill="x", padx=16, pady=12)

        cb_top = ctk.CTkFrame(cb_inner, fg_color="transparent")
        cb_top.pack(fill="x", pady=(0, 4))

        lbl_cb_title = ctk.CTkLabel(
            cb_top,
            text="💡 Live Interval Intelligence & Multi-App Correlation",
            font=get_font(size=13, weight="bold"),
            text_color="#1e40af",
            anchor="w",
        )
        lbl_cb_title.pack(side="left")

        # Companion pills
        comp_box = ctk.CTkFrame(cb_top, fg_color="transparent")
        comp_box.pack(side="right")
        for comp in companions:
            c_pill = ctk.CTkLabel(
                comp_box,
                text=f"● {comp}",
                font=get_font(size=10, weight="bold"),
                text_color="#1d4ed8",
                fg_color="#dbeafe",
                corner_radius=4,
                padx=6,
                pady=2,
            )
            c_pill.pack(side="left", padx=2)

        lbl_cb_desc = ctk.CTkLabel(
            cb_inner,
            text=narrative,
            font=get_font(size=11),
            text_color="#1e3a8a",
            anchor="w",
            justify="left",
            wraplength=840,
        )
        lbl_cb_desc.pack(fill="x", pady=(0, 6))

        # Visual Work vs Leisure Progress Distribution Bar
        bar_box = ctk.CTkFrame(cb_inner, fg_color="transparent")
        bar_box.pack(fill="x", pady=(4, 0))

        lbl_bar_legend = ctk.CTkLabel(
            bar_box,
            text=f"Allocation: 🟢 {w_pct}% Core Work  •  🔵 {c_pct}% Team Sync  •  🟣 {r_pct}% Acoustic Focus  •  🟠 {l_pct}% Leisure Diversion",
            font=get_font(size=10, weight="bold"),
            text_color="#3b82f6",
            anchor="w",
        )
        lbl_bar_legend.pack(fill="x")

        # -------------------------------------------------------------
        # 2. Discovered Active Workspaces & Deliverables Section
        # -------------------------------------------------------------
        lbl_section = ctk.CTkLabel(
            self.scroll_content,
            text="📁 Discovered Active Workspaces & Deliverables (Separated & Isolated)",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_section.pack(fill="x", pady=(4, 8))

        for p in projects:
            p_card = ctk.CTkFrame(
                self.scroll_content,
                fg_color=THEME["card_bg"],
                corner_radius=12,
                border_width=1,
                border_color=THEME["border"],
            )
            p_card.pack(fill="x", pady=8)

            p_inner = ctk.CTkFrame(p_card, fg_color="transparent")
            p_inner.pack(fill="x", padx=20, pady=16)

            # Top Header Row: Project Name + Status Badge & Category
            top_row = ctk.CTkFrame(p_inner, fg_color="transparent")
            top_row.pack(fill="x", pady=(0, 4))

            lbl_pname = ctk.CTkLabel(
                top_row,
                text=f"📂 {p.get('name')}",
                font=get_font(size=18, weight="bold"),
                text_color=THEME["text_primary"],
            )
            lbl_pname.pack(side="left")

            badge_box = ctk.CTkFrame(top_row, fg_color="transparent")
            badge_box.pack(side="right")

            # Status Badge (e.g. ⚡ Active Focus / 🟢 Live Web Review)
            badge_status = ctk.CTkLabel(
                badge_box,
                text=p.get("status_label", "⚡ Active Focus"),
                font=get_font(size=11, weight="bold"),
                text_color="#065f46",
                fg_color="#d1fae5",
                corner_radius=6,
                padx=10,
                pady=3,
            )
            badge_status.pack(side="left", padx=3)

            # Category Badge
            badge_cat = ctk.CTkLabel(
                badge_box,
                text=p.get("category", "Project"),
                font=get_font(size=11, weight="bold"),
                text_color=THEME["denim_blue"],
                fg_color=THEME["denim_tint"],
                corner_radius=6,
                padx=10,
                pady=3,
            )
            badge_cat.pack(side="left", padx=3)

            # Secondary Metadata Strip (Ensures Architecture & Hours have ample room and NEVER truncate!)
            meta_strip = ctk.CTkFrame(p_inner, fg_color="transparent")
            meta_strip.pack(fill="x", pady=(2, 6))

            # Architecture Badge Pill
            badge_arch = ctk.CTkLabel(
                meta_strip,
                text=f"🖥️ {p.get('architecture_type', 'Workspace')}",
                font=get_font(size=11, weight="bold"),
                text_color=THEME["yellow_title"],
                fg_color=THEME["yellow_tint"],
                corner_radius=6,
                padx=10,
                pady=3,
            )
            badge_arch.pack(side="left", padx=(0, 6))

            # Hours Invested Pill
            badge_hrs = ctk.CTkLabel(
                meta_strip,
                text=f"⏱️ {p.get('hours', 0)} hrs invested",
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_secondary"],
                fg_color=THEME["card_inner"],
                corner_radius=6,
                padx=10,
                pady=3,
            )
            badge_hrs.pack(side="left", padx=(0, 6))

            # Key Modules Count Pill
            key_modules_list = p.get("key_modules", [])
            if key_modules_list:
                badge_mods = ctk.CTkLabel(
                    meta_strip,
                    text=f"📦 {len(key_modules_list)} Hotspots Tracked",
                    font=get_font(size=11, weight="bold"),
                    text_color=THEME["text_secondary"],
                    fg_color=THEME["card_inner"],
                    corner_radius=6,
                    padx=10,
                    pady=3,
                )
                badge_mods.pack(side="left")

            # Executive Brief Subtitle
            lbl_brief = ctk.CTkLabel(
                p_inner,
                text=p.get("executive_brief", "Active deliverable workspace monitored by Minion AI."),
                font=get_font(size=12),
                text_color=THEME["text_secondary"],
                anchor="w",
            )
            lbl_brief.pack(fill="x", pady=(2, 10))

            # -------------------------------------------------------------
            # Project Deliverable Banner (Strictly Scoped & Isolated!)
            # -------------------------------------------------------------
            deliv = p.get("active_deliverable")
            if not deliv and p.get("local_url"):
                deliv = {
                    "title": f"Live Web App ({p.get('name')})",
                    "type": "Live Web Development Server",
                    "icon": "🌐",
                    "action_label": "🚀 Launch in Browser",
                    "action_type": "url",
                    "target": p.get("local_url"),
                    "status": p.get("local_url_status", "Online"),
                    "summary": "Active local web server ready for live testing and review.",
                }

            if deliv:
                d_type = str(deliv.get("type", "")).lower()
                act_type = deliv.get("action_type", "focus")

                # Tailor color theme by deliverable craft
                if "web" in d_type or act_type == "url":
                    b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#f0fdf4", "#86efac", "#166534", "#15803d", "#16a34a", "#15803d"
                elif "desktop" in d_type or "focus intelligence" in d_type:
                    b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#eff6ff", "#bfdbfe", "#1e40af", "#1d4ed8", "#2563eb", "#1d4ed8"
                elif "financial" in d_type or "spreadsheet" in d_type:
                    b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#eff6ff", "#bfdbfe", "#1e40af", "#1d4ed8", "#2563eb", "#1d4ed8"
                elif "manuscript" in d_type or "document" in d_type or "authoring" in d_type:
                    b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#fffbeb", "#fde68a", "#92400e", "#b45309", "#d97706", "#b45309"
                elif "design" in d_type or "canvas" in d_type or "artboard" in d_type:
                    b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#faf5ff", "#e9d5ff", "#6b21a8", "#7e22ce", "#9333ea", "#7e22ce"
                else:
                    b_bg, b_border, b_text, b_sub, btn_bg, btn_hover = "#f8fafc", "#cbd5e1", "#334155", "#475569", "#475569", "#334155"

                deliv_banner = ctk.CTkFrame(
                    p_inner,
                    fg_color=b_bg,
                    border_width=1,
                    border_color=b_border,
                    corner_radius=8,
                )
                deliv_banner.pack(fill="x", pady=(0, 10))

                db_inner = ctk.CTkFrame(deliv_banner, fg_color="transparent")
                db_inner.pack(fill="x", padx=14, pady=8)

                left_info = ctk.CTkFrame(db_inner, fg_color="transparent")
                left_info.pack(side="left", fill="x", expand=True)

                lbl_pulse = ctk.CTkLabel(
                    left_info,
                    text=f"{deliv.get('icon', '📁')} {deliv.get('title')}  •  {deliv.get('status', 'Active')}",
                    font=get_font(size=12, weight="bold"),
                    text_color=b_text,
                    anchor="w",
                )
                lbl_pulse.pack(anchor="w")

                lbl_hint = ctk.CTkLabel(
                    left_info,
                    text=deliv.get("summary", "Primary active deliverable for focused execution."),
                    font=get_font(size=11),
                    text_color=b_sub,
                    anchor="w",
                )
                lbl_hint.pack(anchor="w")

                btn_action = ctk.CTkButton(
                    db_inner,
                    text=deliv.get("action_label", "⚡ Focus Deliverable"),
                    font=get_font(size=12, weight="bold"),
                    fg_color=btn_bg,
                    hover_color=btn_hover,
                    text_color="#ffffff",
                    height=32,
                    corner_radius=6,
                    cursor="hand2",
                    command=lambda d=deliv: activate_deliverable(d),
                )
                btn_action.pack(side="right", padx=(8, 0))

            # -------------------------------------------------------------
            # Key Modules & Architecture Hotspots
            # -------------------------------------------------------------
            key_modules = p.get("key_modules", [])
            if key_modules:
                mod_box = ctk.CTkFrame(p_inner, fg_color=THEME["card_inner"], corner_radius=8, border_width=1, border_color=THEME["border"])
                mod_box.pack(fill="x", pady=(2, 8))

                mb_inner = ctk.CTkFrame(mod_box, fg_color="transparent")
                mb_inner.pack(fill="x", padx=14, pady=10)

                lbl_mod_title = ctk.CTkLabel(
                    mb_inner,
                    text="📄 Active Key Modules & Architecture Hotspots:",
                    font=get_font(size=12, weight="bold"),
                    text_color=THEME["text_primary"],
                    anchor="w",
                )
                lbl_mod_title.pack(fill="x", pady=(0, 6))

                # Grid of modules (2 columns)
                mod_grid = ctk.CTkFrame(mb_inner, fg_color="transparent")
                mod_grid.pack(fill="x")
                mod_grid.grid_columnconfigure((0, 1), weight=1)

                for idx, km in enumerate(key_modules[:6]):
                    r_idx = idx // 2
                    c_idx = idx % 2
                    m_card = ctk.CTkFrame(mod_grid, fg_color=THEME["card_bg"], corner_radius=6, border_width=1, border_color=THEME["border"])
                    m_card.grid(row=r_idx, column=c_idx, padx=4, pady=3, sticky="nsew")

                    mc_inner = ctk.CTkFrame(m_card, fg_color="transparent")
                    mc_inner.pack(fill="both", expand=True, padx=10, pady=6)

                    lbl_m_file = ctk.CTkLabel(
                        mc_inner,
                        text=f"{km.get('icon', '📄')} {km.get('file', '')}",
                        font=get_font(size=11, weight="bold"),
                        text_color=THEME["text_primary"],
                        anchor="w",
                    )
                    lbl_m_file.pack(fill="x")

                    lbl_m_role = ctk.CTkLabel(
                        mc_inner,
                        text=km.get("role", "Core Module"),
                        font=get_font(size=10),
                        text_color=THEME["text_secondary"],
                        anchor="w",
                    )
                    lbl_m_role.pack(fill="x")

            # Tools & Stack Badges
            tech_row = ctk.CTkFrame(p_inner, fg_color="transparent")
            tech_row.pack(fill="x", pady=(4, 6))

            lbl_stk = ctk.CTkLabel(
                tech_row,
                text="Tools & Stack:",
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_secondary"],
            )
            lbl_stk.pack(side="left", padx=(0, 6))

            for stk in p.get("stack", []):
                pill = ctk.CTkLabel(
                    tech_row,
                    text=stk,
                    font=get_font(size=11, weight="bold"),
                    text_color=THEME["text_primary"],
                    fg_color=THEME["card_inner"],
                    corner_radius=4,
                    padx=8,
                    pady=2,
                )
                pill.pack(side="left", padx=3)

            # -------------------------------------------------------------
            # STRATEGIC ANGLES & HOW TO IMPROVE THE PROJECT
            # -------------------------------------------------------------
            angles = p.get("strategic_angles", [])
            if angles:
                angles_box = ctk.CTkFrame(
                    p_inner,
                    fg_color=THEME["card_inner"],
                    border_width=1,
                    border_color=THEME["border"],
                    corner_radius=8,
                )
                angles_box.pack(fill="x", pady=(6, 6))

                ab_inner = ctk.CTkFrame(angles_box, fg_color="transparent")
                ab_inner.pack(fill="x", padx=14, pady=12)

                lbl_ang_title = ctk.CTkLabel(
                    ab_inner,
                    text="💡 Strategic Improvement Angles & Multi-Perspective Review",
                    font=get_font(size=13, weight="bold"),
                    text_color=THEME["yellow_title"],
                    anchor="w",
                )
                lbl_ang_title.pack(fill="x", pady=(0, 6))

                for ang in angles:
                    cardlet = ctk.CTkFrame(ab_inner, fg_color=THEME["card_bg"], corner_radius=6, border_width=1, border_color=THEME["border"])
                    cardlet.pack(fill="x", pady=4)

                    c_inner = ctk.CTkFrame(cardlet, fg_color="transparent")
                    c_inner.pack(fill="x", padx=12, pady=8)

                    lbl_header = ctk.CTkLabel(
                        c_inner,
                        text=f"{ang['angle']}  •  {ang['summary']}",
                        font=get_font(size=12, weight="bold"),
                        text_color=THEME["text_primary"],
                        anchor="w",
                    )
                    lbl_header.pack(fill="x", pady=(0, 2))

                    lbl_rec = ctk.CTkLabel(
                        c_inner,
                        text=ang["recommendation"],
                        font=get_font(size=11),
                        text_color=THEME["text_secondary"],
                        anchor="w",
                        justify="left",
                        wraplength=760,
                    )
                    lbl_rec.pack(fill="x")

            # -------------------------------------------------------------
            # TOOL MASTERY & VELOCITY ACCELERATORS (Modern Modular Cardlets)
            # -------------------------------------------------------------
            tool_tips = p.get("tool_improvements", [])
            if tool_tips:
                tool_box = ctk.CTkFrame(
                    p_inner,
                    fg_color=THEME["card_inner"],
                    border_width=1,
                    border_color=THEME["border"],
                    corner_radius=10,
                )
                tool_box.pack(fill="x", pady=(6, 6))

                tb_inner = ctk.CTkFrame(tool_box, fg_color="transparent")
                tb_inner.pack(fill="x", padx=16, pady=14)

                tb_head = ctk.CTkFrame(tb_inner, fg_color="transparent")
                tb_head.pack(fill="x", pady=(0, 8))

                lbl_tool_title = ctk.CTkLabel(
                    tb_head,
                    text="🛠️ Tool Mastery & Workflow Boosts",
                    font=get_font(size=14, weight="bold"),
                    text_color=THEME["denim_blue"],
                    anchor="w",
                )
                lbl_tool_title.pack(side="left")

                lbl_tool_sub = ctk.CTkLabel(
                    tb_head,
                    text="⚡ 10x Stack Velocity Accelerators",
                    font=get_font(size=10, weight="bold"),
                    text_color=THEME["denim_blue"],
                    fg_color=THEME["denim_tint"],
                    corner_radius=5,
                    padx=8,
                    pady=2,
                )
                lbl_tool_sub.pack(side="right")

                for tt in tool_tips:
                    # Individual polished micro-cardlet with elevation border
                    tip_card = ctk.CTkFrame(
                        tb_inner,
                        fg_color=THEME["card_bg"],
                        corner_radius=8,
                        border_width=1,
                        border_color=THEME["border"],
                    )
                    tip_card.pack(fill="x", pady=4)

                    tc_inner = ctk.CTkFrame(tip_card, fg_color="transparent")
                    tc_inner.pack(fill="x", padx=14, pady=10)

                    # Top header inside micro-card: Tool Name + Category Tag
                    tc_top = ctk.CTkFrame(tc_inner, fg_color="transparent")
                    tc_top.pack(fill="x", pady=(0, 4))

                    lbl_t_name = ctk.CTkLabel(
                        tc_top,
                        text=tt.get("tool", "Development Tool"),
                        font=get_font(size=12, weight="bold"),
                        text_color=THEME["text_primary"],
                        anchor="w",
                    )
                    lbl_t_name.pack(side="left")

                    lbl_tip_tag = ctk.CTkLabel(
                        tc_top,
                        text="💡 PRO-TIP",
                        font=get_font(size=10, weight="bold"),
                        text_color="#059669",
                        fg_color="#d1fae5",
                        corner_radius=4,
                        padx=6,
                        pady=1,
                    )
                    lbl_tip_tag.pack(side="right")

                    # Body: Clean, comfortably wrapped tip description
                    lbl_t_tip = ctk.CTkLabel(
                        tc_inner,
                        text=tt.get("tip", ""),
                        font=get_font(size=11),
                        text_color=THEME["text_secondary"],
                        anchor="w",
                        justify="left",
                        wraplength=820,
                    )
                    lbl_t_tip.pack(fill="x")

            # -------------------------------------------------------------
            # ACTIONABLE NEXT MILESTONES (Clean Checklist Cardlets)
            # -------------------------------------------------------------
            milestones = p.get("actionable_milestones", [])
            if milestones:
                m_box = ctk.CTkFrame(p_inner, fg_color="#fffbeb", border_width=1, border_color="#fde68a", corner_radius=10)
                m_box.pack(fill="x", pady=(6, 2))

                mb_inner = ctk.CTkFrame(m_box, fg_color="transparent")
                mb_inner.pack(fill="x", padx=16, pady=12)

                mb_head = ctk.CTkFrame(mb_inner, fg_color="transparent")
                mb_head.pack(fill="x", pady=(0, 6))

                lbl_m_title = ctk.CTkLabel(
                    mb_head,
                    text="🎯 Recommended Next Milestones to Achieve Project Goals",
                    font=get_font(size=13, weight="bold"),
                    text_color="#92400e",
                    anchor="w",
                )
                lbl_m_title.pack(side="left")

                for idx, m in enumerate(milestones):
                    ms_card = ctk.CTkFrame(
                        mb_inner,
                        fg_color=THEME["card_bg"],
                        corner_radius=6,
                        border_width=1,
                        border_color="#fde68a",
                    )
                    ms_card.pack(fill="x", pady=3)

                    mc_row = ctk.CTkFrame(ms_card, fg_color="transparent")
                    mc_row.pack(fill="x", padx=12, pady=7)

                    lbl_m_text = ctk.CTkLabel(
                        mc_row,
                        text=f"⚡ Stage {idx + 1}:  {m}",
                        font=get_font(size=11, weight="bold"),
                        text_color="#78350f",
                        anchor="w",
                    )
                    lbl_m_text.pack(side="left")

                    lbl_ms_tag = ctk.CTkLabel(
                        mc_row,
                        text="⏳ TARGET MILESTONE",
                        font=get_font(size=9, weight="bold"),
                        text_color="#92400e",
                        fg_color="#fef3c7",
                        corner_radius=4,
                        padx=6,
                        pady=1,
                    )
                    lbl_ms_tag.pack(side="right")

        # Tech Stack Badges Card
        tech_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["border"],
        )
        tech_card.pack(fill="x", pady=(12, 6))

        t_inner = ctk.CTkFrame(tech_card, fg_color="transparent")
        t_inner.pack(fill="x", padx=18, pady=14)

        lbl_t_title = ctk.CTkLabel(
            t_inner,
            text="🧰 Core Application & Tool Stack",
            font=get_font(size=15, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_t_title.pack(fill="x", pady=(0, 8))

        pills_box = ctk.CTkFrame(t_inner, fg_color="transparent")
        pills_box.pack(fill="x")

        for t in tech_stack:
            t_pill = ctk.CTkLabel(
                pills_box,
                text=f"  {t}  ",
                font=get_font(size=12, weight="bold"),
                text_color=THEME["denim_blue"],
                fg_color=THEME["denim_tint"],
                corner_radius=6,
                padx=8,
                pady=4,
            )
            t_pill.pack(side="left", padx=4, pady=4)

        # Codebase Hotspots
        if top_files:
            hot_card = ctk.CTkFrame(
                self.scroll_content,
                fg_color=THEME["card_bg"],
                corner_radius=10,
                border_width=1,
                border_color=THEME["border"],
            )
            hot_card.pack(fill="x", pady=8)

            hot_inner = ctk.CTkFrame(hot_card, fg_color="transparent")
            hot_inner.pack(fill="x", padx=18, pady=14)

            lbl_hot = ctk.CTkLabel(
                hot_inner,
                text="🔥 Most Active Deliverables & Documents",
                font=get_font(size=15, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_hot.pack(fill="x", pady=(0, 6))

            for item in top_files:
                row = ctk.CTkFrame(hot_inner, fg_color="transparent")
                row.pack(fill="x", pady=3)

                lbl_fn = ctk.CTkLabel(
                    row,
                    text=f"• {item['file']}",
                    font=get_font(size=12, weight="bold"),
                    text_color=THEME["text_primary"],
                    anchor="w",
                )
                lbl_fn.pack(side="left")

                lbl_cnt = ctk.CTkLabel(
                    row,
                    text=f"{item['count']} focus observations",
                    font=get_font(size=11),
                    text_color=THEME["text_muted"],
                )
                lbl_cnt.pack(side="right")

    # =============================================================
    # Tab 3: 🎮 Hobbies, Media & Lifestyle
    # =============================================================
    def _render_lifestyle_tab(self) -> None:
        """Render rich AI behavioral insights for music, YouTube, research, and communication habits."""
        life = self.knowledge_graph.get("lifestyle_data", {})
        music = life.get("music_tracks", [])
        structured_tracks = life.get("structured_tracks", [])
        yt = life.get("youtube_topics", [])
        academics = life.get("academic_topics", [])
        comms = life.get("comm_channels", [])

        # ---------------------------------------------------------
        # Card 1: 🎵 Music, Audio & Flow Soundtracks
        # ---------------------------------------------------------
        m_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        m_card.pack(fill="x", pady=8)

        m_inner = ctk.CTkFrame(m_card, fg_color="transparent")
        m_inner.pack(fill="x", padx=20, pady=16)

        m_head = ctk.CTkFrame(m_inner, fg_color="transparent")
        m_head.pack(fill="x", pady=(0, 8))

        lbl_m = ctk.CTkLabel(
            m_head,
            text="🎵 Music, Audio & Flow Soundtracks",
            font=get_font(size=16, weight="bold"),
            text_color="#059669",
            anchor="w",
        )
        lbl_m.pack(side="left")

        m_sessions = life.get("music_sessions", 0)
        top_genre = life.get("top_genre", "")
        genre_dist = life.get("genre_distribution", [])

        badge_text = f"🎧 {top_genre} • {m_sessions} Sessions" if top_genre else f"⚡ Audio Flow • {m_sessions} Sessions Tracked"
        lbl_m_badge = ctk.CTkLabel(
            m_head,
            text=badge_text,
            font=get_font(size=11, weight="bold"),
            text_color="#065f46",
            fg_color="#d1fae5",
            corner_radius=6,
            padx=8,
            pady=2,
        )
        lbl_m_badge.pack(side="right")

        # Synthesized AI Behavioral Insight Box
        m_insight_text = life.get("music_insight") or (
            "No audio playback detected during focus blocks yet. "
            "Stream music during your work sessions to see your actual flow correlation and stamina metrics."
        )
        m_callout = ctk.CTkFrame(
            m_inner,
            fg_color="#f0fdf4",
            border_width=1,
            border_color="#86efac",
            corner_radius=8,
        )
        m_callout.pack(fill="x", pady=(0, 10))

        m_callout_inner = ctk.CTkFrame(m_callout, fg_color="transparent")
        m_callout_inner.pack(fill="x", padx=14, pady=10)

        lbl_ci_title = ctk.CTkLabel(
            m_callout_inner,
            text="💡 AI Flow Correlation Insight",
            font=get_font(size=11, weight="bold"),
            text_color="#166534",
            anchor="w",
        )
        lbl_ci_title.pack(fill="x")

        lbl_ci_desc = ctk.CTkLabel(
            m_callout_inner,
            text=m_insight_text,
            font=get_font(size=11),
            text_color="#15803d",
            anchor="w",
            wraplength=830,
            justify="left",
        )
        lbl_ci_desc.pack(fill="x", pady=(2, 0))

        # Multi-Genre Cognitive Distribution Strip
        if genre_dist:
            g_strip = ctk.CTkFrame(m_inner, fg_color="transparent")
            g_strip.pack(fill="x", pady=(0, 12))

            lbl_g_title = ctk.CTkLabel(
                g_strip,
                text="📊 Studied Genre Distribution & Flow Impact:",
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_secondary"],
                anchor="w",
            )
            lbl_g_title.pack(anchor="w", pady=(0, 4))

            pills_row = ctk.CTkFrame(g_strip, fg_color="transparent")
            pills_row.pack(fill="x")

            for g in genre_dist[:4]:
                g_pill = ctk.CTkFrame(
                    pills_row,
                    fg_color=THEME["card_inner"],
                    border_width=1,
                    border_color=THEME["border"],
                    corner_radius=6,
                )
                g_pill.pack(side="left", padx=(0, 8), pady=2)

                g_text = f"{g.get('icon', '🎵')} {g.get('name', 'Genre')} • {g.get('pct', 0)}%"
                lbl_gp = ctk.CTkLabel(
                    g_pill,
                    text=g_text,
                    font=get_font(size=11, weight="bold"),
                    text_color=THEME["text_primary"],
                    padx=8,
                    pady=3,
                )
                lbl_gp.pack(side="left")

                if g.get("impact"):
                    lbl_g_imp = ctk.CTkLabel(
                        g_pill,
                        text=g["impact"],
                        font=get_font(size=10),
                        text_color="#059669",
                        fg_color="#d1fae5",
                        corner_radius=4,
                        padx=6,
                        pady=1,
                    )
                    lbl_g_imp.pack(side="left", padx=(0, 6), pady=3)

        # Real Deduplicated Music Tracks Grid
        raw_tracks = structured_tracks if structured_tracks else [
            {"title": tr, "artist": tr.split(" - ")[0] if " - " in tr else "Audio Artist", "song": tr.split(" - ")[1] if " - " in tr else tr, "plays": 1, "tag": "Flow Anchor"}
            for tr in music
        ]

        seen_songs = set()
        tracks_to_show = []
        for t in raw_tracks:
            clean_name = (t.get("title") or t.get("song") or "").strip()
            lower_name = clean_name.lower()
            if any(lower_name == g for g in ["spotify", "spotify premium", "spotify free", "advertisement", "spotify audio", "spotify streaming (background audio)"]):
                continue
            if lower_name and lower_name not in seen_songs:
                seen_songs.add(lower_name)
                tracks_to_show.append(t)

        if not tracks_to_show:
            empty_m = ctk.CTkFrame(m_inner, fg_color=THEME["card_inner"], corner_radius=8, border_width=1, border_color=THEME["border"])
            empty_m.pack(fill="x", pady=4)
            lbl_no_m = ctk.CTkLabel(
                empty_m,
                text="🎵 No audio playback captured yet. Play Spotify, Apple Music, or your audio player during focus sessions to discover your flow soundtrack.",
                font=get_font(size=12),
                text_color=THEME["text_muted"],
                padx=16,
                pady=14,
            )
            lbl_no_m.pack(anchor="w")
        else:
            tracks_grid = ctk.CTkFrame(m_inner, fg_color="transparent")
            tracks_grid.pack(fill="x")
            tracks_grid.grid_columnconfigure((0, 1), weight=1)

            for idx, t in enumerate(tracks_to_show[:6]):
                r = idx // 2
                c = idx % 2
                t_row = ctk.CTkFrame(
                    tracks_grid,
                    fg_color=THEME["card_inner"],
                    corner_radius=8,
                    border_width=1,
                    border_color=THEME["border"],
                )
                t_row.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")

                tr_box = ctk.CTkFrame(t_row, fg_color="transparent")
                tr_box.pack(fill="x", padx=12, pady=8)

                g_icon = t.get("genre_icon") or "🎧"
                lbl_song = ctk.CTkLabel(
                    tr_box,
                    text=f"{g_icon} {t.get('song') or t.get('title')}",
                    font=get_font(size=12, weight="bold"),
                    text_color=THEME["text_primary"],
                    anchor="w",
                )
                lbl_song.pack(fill="x")

                sub_line = ctk.CTkFrame(tr_box, fg_color="transparent")
                sub_line.pack(fill="x", pady=(2, 0))

                lbl_artist = ctk.CTkLabel(
                    sub_line,
                    text=t.get("artist", "Audio Artist"),
                    font=get_font(size=11),
                    text_color=THEME["text_secondary"],
                    anchor="w",
                )
                lbl_artist.pack(side="left")

                tag_text = t.get("genre") or t.get("tag") or "Flow Anchor"
                lbl_tag = ctk.CTkLabel(
                    sub_line,
                    text=tag_text,
                    font=get_font(size=10, weight="bold"),
                    text_color="#059669",
                    fg_color="#d1fae5",
                    corner_radius=4,
                    padx=6,
                    pady=1,
                )
                lbl_tag.pack(side="right")

        # ---------------------------------------------------------
        # Card 2: 📺 Off-Duty Media, Gaming & Entertainment
        # ---------------------------------------------------------
        yt_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        yt_card.pack(fill="x", pady=8)

        yt_inner = ctk.CTkFrame(yt_card, fg_color="transparent")
        yt_inner.pack(fill="x", padx=20, pady=16)

        yt_head = ctk.CTkFrame(yt_inner, fg_color="transparent")
        yt_head.pack(fill="x", pady=(0, 8))

        lbl_yt = ctk.CTkLabel(
            yt_head,
            text="📺 Off-Duty Media, Gaming & Entertainment",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["yellow_title"],
            anchor="w",
        )
        lbl_yt.pack(side="left")

        lbl_yt_badge = ctk.CTkLabel(
            yt_head,
            text="🕒 Afternoon Transition Window",
            font=get_font(size=11, weight="bold"),
            text_color=THEME["yellow_text"],
            fg_color=THEME["yellow_tint"],
            corner_radius=6,
            padx=8,
            pady=2,
        )
        lbl_yt_badge.pack(side="right")

        # Synthesized AI Media Recharge Insight
        yt_insight_text = life.get("media_insight") or (
            "No off-duty media or entertainment streaming tracked yet. "
            "Off-duty recharge patterns will be analyzed here once leisure activities are observed."
        )
        yt_callout = ctk.CTkFrame(
            yt_inner,
            fg_color="#fffbeb",
            border_width=1,
            border_color="#fde68a",
            corner_radius=8,
        )
        yt_callout.pack(fill="x", pady=(0, 12))

        yt_callout_inner = ctk.CTkFrame(yt_callout, fg_color="transparent")
        yt_callout_inner.pack(fill="x", padx=14, pady=10)

        lbl_yci_title = ctk.CTkLabel(
            yt_callout_inner,
            text="💡 AI Cognitive Recharge Insight",
            font=get_font(size=11, weight="bold"),
            text_color="#92400e",
            anchor="w",
        )
        lbl_yci_title.pack(fill="x")

        lbl_yci_desc = ctk.CTkLabel(
            yt_callout_inner,
            text=yt_insight_text,
            font=get_font(size=11),
            text_color="#b45309",
            anchor="w",
            wraplength=830,
            justify="left",
        )
        lbl_yci_desc.pack(fill="x", pady=(2, 0))

        # Deduplicated Media List
        for y in yt[:5]:
            y_row = ctk.CTkFrame(
                yt_inner,
                fg_color=THEME["card_inner"],
                corner_radius=6,
                border_width=1,
                border_color=THEME["border"],
            )
            y_row.pack(fill="x", pady=3)

            y_inner = ctk.CTkFrame(y_row, fg_color="transparent")
            y_inner.pack(fill="x", padx=12, pady=7)

            lbl_y_title = ctk.CTkLabel(
                y_inner,
                text=f"🎬 {y}",
                font=get_font(size=12, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_y_title.pack(side="left", fill="x", expand=True)

            lbl_y_tag = ctk.CTkLabel(
                y_inner,
                text="Recharge Stream",
                font=get_font(size=10, weight="bold"),
                text_color=THEME["yellow_title"],
                fg_color=THEME["yellow_tint"],
                corner_radius=4,
                padx=6,
                pady=1,
            )
            lbl_y_tag.pack(side="right")

        # ---------------------------------------------------------
        # Card 3: 📚 Academic Systems & Teaching Notes
        # ---------------------------------------------------------
        if academics:
            ac_card = ctk.CTkFrame(
                self.scroll_content,
                fg_color=THEME["card_bg"],
                corner_radius=12,
                border_width=1,
                border_color=THEME["border"],
            )
            ac_card.pack(fill="x", pady=8)

            ac_inner = ctk.CTkFrame(ac_card, fg_color="transparent")
            ac_inner.pack(fill="x", padx=20, pady=16)

            ac_head = ctk.CTkFrame(ac_inner, fg_color="transparent")
            ac_head.pack(fill="x", pady=(0, 8))

            lbl_ac = ctk.CTkLabel(
                ac_head,
                text="📚 Academic Systems, Curriculum & Deep Research",
                font=get_font(size=16, weight="bold"),
                text_color="#0284c7",
                anchor="w",
            )
            lbl_ac.pack(side="left")

            lbl_ac_badge = ctk.CTkLabel(
                ac_head,
                text="🔬 High Leverage Mastery",
                font=get_font(size=11, weight="bold"),
                text_color="#0369a1",
                fg_color="#e0f2fe",
                corner_radius=6,
                padx=8,
                pady=2,
            )
            lbl_ac_badge.pack(side="right")

            # Synthesized AI Academic Insight
            ac_insight_text = life.get("academic_insight") or (
                "No technical documentation or research sessions tracked yet. "
                "Deep research topics will appear here as you read articles, technical docs, and papers."
            )
            ac_callout = ctk.CTkFrame(
                ac_inner,
                fg_color="#f0f9ff",
                border_width=1,
                border_color="#bae6fd",
                corner_radius=8,
            )
            ac_callout.pack(fill="x", pady=(0, 12))

            ac_callout_inner = ctk.CTkFrame(ac_callout, fg_color="transparent")
            ac_callout_inner.pack(fill="x", padx=14, pady=10)

            lbl_aci_title = ctk.CTkLabel(
                ac_callout_inner,
                text="💡 Continuous Skill Mastery Insight",
                font=get_font(size=11, weight="bold"),
                text_color="#075985",
                anchor="w",
            )
            lbl_aci_title.pack(fill="x")

            lbl_aci_desc = ctk.CTkLabel(
                ac_callout_inner,
                text=ac_insight_text,
                font=get_font(size=11),
                text_color="#0284c7",
                anchor="w",
                wraplength=830,
                justify="left",
            )
            lbl_aci_desc.pack(fill="x", pady=(2, 0))

            for a in academics[:5]:
                a_row = ctk.CTkFrame(
                    ac_inner,
                    fg_color=THEME["card_inner"],
                    corner_radius=6,
                    border_width=1,
                    border_color=THEME["border"],
                )
                a_row.pack(fill="x", pady=3)

                a_box = ctk.CTkFrame(a_row, fg_color="transparent")
                a_box.pack(fill="x", padx=12, pady=7)

                lbl_a = ctk.CTkLabel(
                    a_box,
                    text=f"📑 {a}",
                    font=get_font(size=12, weight="bold"),
                    text_color=THEME["text_primary"],
                    anchor="w",
                )
                lbl_a.pack(side="left", fill="x", expand=True)

                lbl_a_tag = ctk.CTkLabel(
                    a_box,
                    text="Active Synthesis",
                    font=get_font(size=10, weight="bold"),
                    text_color="#0284c7",
                    fg_color="#e0f2fe",
                    corner_radius=4,
                    padx=6,
                    pady=1,
                )
                lbl_a_tag.pack(side="right")

        # ---------------------------------------------------------
        # Card 4: 💬 Communication & Collaboration Rhythm
        # ---------------------------------------------------------
        comm_card = ctk.CTkFrame(
            self.scroll_content,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        comm_card.pack(fill="x", pady=8)

        c_inner = ctk.CTkFrame(comm_card, fg_color="transparent")
        c_inner.pack(fill="x", padx=20, pady=16)

        c_head = ctk.CTkFrame(c_inner, fg_color="transparent")
        c_head.pack(fill="x", pady=(0, 8))

        lbl_c = ctk.CTkLabel(
            c_head,
            text="💬 Collaboration & Messaging Rhythm",
            font=get_font(size=16, weight="bold"),
            text_color="#7c3aed",
            anchor="w",
        )
        lbl_c.pack(side="left")

        lbl_c_badge = ctk.CTkLabel(
            c_head,
            text="🛡️ Focus Shielded",
            font=get_font(size=11, weight="bold"),
            text_color="#5b21b6",
            fg_color="#ede9fe",
            corner_radius=6,
            padx=8,
            pady=2,
        )
        lbl_c_badge.pack(side="right")

        # Synthesized AI Communication Insight
        comm_insight_text = life.get("comm_insight") or (
            "No team collaboration channels (Slack, Teams, Discord, WhatsApp) observed yet. "
            "Messaging rhythm and context-shielding metrics will appear here once communication tools are active."
        )
        c_callout = ctk.CTkFrame(
            c_inner,
            fg_color="#faf5ff",
            border_width=1,
            border_color="#ddd6fe",
            corner_radius=8,
        )
        c_callout.pack(fill="x", pady=(0, 12))

        c_callout_inner = ctk.CTkFrame(c_callout, fg_color="transparent")
        c_callout_inner.pack(fill="x", padx=14, pady=10)

        lbl_cci_title = ctk.CTkLabel(
            c_callout_inner,
            text="💡 Collaboration Velocity Insight",
            font=get_font(size=11, weight="bold"),
            text_color="#6b21a8",
            anchor="w",
        )
        lbl_cci_title.pack(fill="x")

        lbl_cci_desc = ctk.CTkLabel(
            c_callout_inner,
            text=comm_insight_text,
            font=get_font(size=11),
            text_color="#7c3aed",
            anchor="w",
            wraplength=830,
            justify="left",
        )
        lbl_cci_desc.pack(fill="x", pady=(2, 0))

        for c in comms:
            c_row = ctk.CTkFrame(
                c_inner,
                fg_color=THEME["card_inner"],
                corner_radius=6,
                border_width=1,
                border_color=THEME["border"],
            )
            c_row.pack(fill="x", pady=3)

            cb = ctk.CTkFrame(c_row, fg_color="transparent")
            cb.pack(fill="x", padx=12, pady=7)

            lbl_cm = ctk.CTkLabel(
                cb,
                text=f"💬 {c}",
                font=get_font(size=12, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_cm.pack(side="left", fill="x", expand=True)

            lbl_cm_tag = ctk.CTkLabel(
                cb,
                text="Batched Comms",
                font=get_font(size=10, weight="bold"),
                text_color="#7c3aed",
                fg_color="#ede9fe",
                corner_radius=4,
                padx=6,
                pady=1,
            )
            lbl_cm_tag.pack(side="right")

    # =============================================================
    # Tab 4: 🎯 Goals & Profile (User Input & Alignment Radar)
    # =============================================================
    def _render_goals_profile_tab(self) -> None:
        """Render studio-grade user profile, goal alignment radar, time allocation breakdown, and milestone roadmap."""
        alignment = self.knowledge_graph.get("goal_alignment", {})
        align_pct = alignment.get("alignment_percentage", 0.0)
        momentum = alignment.get("momentum_label", "Baseline Focus Tracking")
        focused_hrs = alignment.get("total_focused_hours", 0.0)
        shield_eff = alignment.get("shield_efficacy", 100.0)
        time_breakdown = alignment.get("time_breakdown", [])
        milestones = alignment.get("milestone_roadmap", [])
        coaching_tactics = alignment.get("coaching_tactics", [])
        target_goal = alignment.get("target_goal_display", "Declare your goals in Profile to track trajectory")

        # Dynamic Project Subtitle
        projs = self.knowledge_graph.get("projects_data", {}).get("projects", [])
        proj_sub = ", ".join(p["name"] for p in projs[:2]) if projs else "Active Workspaces"

        # Dynamic Milestone Velocity
        total_m = len(milestones)
        completed_m = sum(1 for m in milestones if m.get("status") == "completed")
        m_val = f"Stage {completed_m} of {total_m}" if total_m > 0 else "Sprint Ready"
        m_sub = f"{round((completed_m / total_m) * 100)}% Completed" if total_m > 0 else "Milestones initializing"

        # -------------------------------------------------------------
        # 1. Top Quick Trajectory Metric Strip
        # -------------------------------------------------------------
        strip_frame = ctk.CTkFrame(self.scroll_content, fg_color="transparent")
        strip_frame.pack(fill="x", pady=(2, 12))
        strip_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        metric_cards = [
            {
                "icon": "🎯",
                "title": "Goal Alignment",
                "val": f"{align_pct}%",
                "sub": f"● {momentum}",
                "color": THEME["yellow_title"],
            },
            {
                "icon": "⏱️",
                "title": "Direct Goal Work",
                "val": f"{focused_hrs} hrs",
                "sub": proj_sub,
                "color": THEME["denim_blue"],
            },
            {
                "icon": "🗺️",
                "title": "Milestone Velocity",
                "val": m_val,
                "sub": m_sub,
                "color": "#059669",
            },
            {
                "icon": "🛡️",
                "title": "Boundary Shield",
                "val": f"{shield_eff}%",
                "sub": "Clean Flow Protected",
                "color": "#7c3aed",
            },
        ]

        for idx, m in enumerate(metric_cards):
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

            h_line = ctk.CTkFrame(inner, fg_color="transparent")
            h_line.pack(fill="x")

            lbl_t = ctk.CTkLabel(
                h_line,
                text=f"{m['icon']} {m['title']}",
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_secondary"],
            )
            lbl_t.pack(side="left")

            lbl_v = ctk.CTkLabel(
                inner,
                text=m["val"],
                font=get_font(size=20, weight="bold"),
                text_color=m["color"],
                anchor="w",
            )
            lbl_v.pack(fill="x", pady=(4, 2))

            lbl_s = ctk.CTkLabel(
                inner,
                text=m["sub"],
                font=get_font(size=10, weight="bold" if "●" in m["sub"] else "normal"),
                text_color="#059669" if "●" in m["sub"] else THEME["text_muted"],
                anchor="w",
            )
            lbl_s.pack(fill="x")

        # -------------------------------------------------------------
        # 2. Main 2-Column Split Container
        # -------------------------------------------------------------
        container = ctk.CTkFrame(self.scroll_content, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure((0, 1), weight=1)

        # =============================================================
        # Left Column: User Identity & Profile Form Card
        # =============================================================
        left_card = ctk.CTkFrame(
            container,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        left_card.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        l_inner = ctk.CTkFrame(left_card, fg_color="transparent")
        l_inner.pack(fill="both", expand=True, padx=20, pady=18)

        # Header with user avatar and domain tag
        l_head = ctk.CTkFrame(l_inner, fg_color="transparent")
        l_head.pack(fill="x", pady=(0, 12))

        lbl_p_title = ctk.CTkLabel(
            l_head,
            text="👤 User Identity & Core Objectives",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_p_title.pack(side="left")

        lbl_profile_tag = ctk.CTkLabel(
            l_head,
            text="👨‍💻 Engineering Core",
            font=get_font(size=10, weight="bold"),
            text_color=THEME["yellow_title"],
            fg_color=THEME["yellow_tint"],
            corner_radius=5,
            padx=8,
            pady=2,
        )
        lbl_profile_tag.pack(side="right")

        entry_kwargs = {
            "height": 36,
            "corner_radius": 6,
            "border_width": 1,
            "border_color": THEME["input_border"],
            "fg_color": THEME["card_inner"],
            "text_color": THEME["text_primary"],
            "font": get_font(size=13),
        }

        txt_kwargs = {
            "corner_radius": 6,
            "border_width": 1,
            "border_color": THEME["input_border"],
            "fg_color": THEME["card_inner"],
            "text_color": THEME["text_primary"],
            "font": get_font(size=13),
        }

        # 0. Focus Profile & Discipline
        lbl_domain = ctk.CTkLabel(
            l_inner,
            text="🎯 Focus Profile & Discipline:",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_secondary"],
            anchor="w",
        )
        lbl_domain.pack(fill="x", pady=(4, 2))

        domain_display_list = [f"{d['icon']}  {d['title']}" for d in FOCUS_DOMAINS.values()]
        self.combo_domain = ctk.CTkComboBox(
            l_inner,
            values=domain_display_list,
            command=self._on_domain_selected,
            height=36,
            corner_radius=6,
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
        )
        self.combo_domain.pack(fill="x", pady=(0, 8))

        # 1. Name
        lbl_name = ctk.CTkLabel(l_inner, text="Your Name / Nickname:", font=get_font(size=12, weight="bold"), text_color=THEME["text_secondary"], anchor="w")
        lbl_name.pack(fill="x", pady=(4, 2))
        self.entry_name = ctk.CTkEntry(l_inner, **entry_kwargs)
        self.entry_name.pack(fill="x", pady=(0, 8))

        # 2. Role
        lbl_role = ctk.CTkLabel(l_inner, text="What You Do (Profession & Role):", font=get_font(size=12, weight="bold"), text_color=THEME["text_secondary"], anchor="w")
        lbl_role.pack(fill="x", pady=(4, 2))
        self.entry_role = ctk.CTkEntry(l_inner, **entry_kwargs)
        self.entry_role.pack(fill="x", pady=(0, 8))

        # 3. Why
        lbl_why = ctk.CTkLabel(l_inner, text="Why You Do What You Do (Motivation & North Star):", font=get_font(size=12, weight="bold"), text_color=THEME["text_secondary"], anchor="w")
        lbl_why.pack(fill="x", pady=(4, 2))
        self.txt_why = ctk.CTkTextbox(l_inner, height=58, **txt_kwargs)
        self.txt_why.pack(fill="x", pady=(0, 8))

        # 4. Short-Term Goals
        lbl_short = ctk.CTkLabel(l_inner, text="Short-Term Goals (Current Focus & Weekly Milestones):", font=get_font(size=12, weight="bold"), text_color=THEME["text_secondary"], anchor="w")
        lbl_short.pack(fill="x", pady=(4, 2))
        self.txt_short_goals = ctk.CTkTextbox(l_inner, height=58, **txt_kwargs)
        self.txt_short_goals.pack(fill="x", pady=(0, 8))

        # 5. Long-Term Goals
        lbl_long = ctk.CTkLabel(l_inner, text="Long-Term Goals (12-Month Architectural Vision):", font=get_font(size=12, weight="bold"), text_color=THEME["text_secondary"], anchor="w")
        lbl_long.pack(fill="x", pady=(4, 2))
        self.txt_long_goals = ctk.CTkTextbox(l_inner, height=58, **txt_kwargs)
        self.txt_long_goals.pack(fill="x", pady=(0, 8))

        # 6. Things to Avoid
        lbl_avoid = ctk.CTkLabel(l_inner, text="Things to Avoid (Distractions & Anti-Goals):", font=get_font(size=12, weight="bold"), text_color=THEME["text_secondary"], anchor="w")
        lbl_avoid.pack(fill="x", pady=(4, 2))
        self.txt_avoid = ctk.CTkTextbox(l_inner, height=58, **txt_kwargs)
        self.txt_avoid.pack(fill="x", pady=(0, 12))

        # Bottom Action: Direct Save Button
        self.btn_save_inner = ctk.CTkButton(
            l_inner,
            text="💾 Save Profile & Synchronize Intelligence",
            command=self._handle_save_profile,
            fg_color=THEME["denim_blue"],
            hover_color=THEME["denim_hover"],
            text_color="#ffffff",
            font=get_font(size=12, weight="bold"),
            height=36,
            corner_radius=6,
            cursor="hand2",
        )
        self.btn_save_inner.pack(fill="x", pady=(4, 0))

        # =============================================================
        # Right Column: Deep Strategic Radar & Learning Cards
        # =============================================================
        right_card = ctk.CTkFrame(
            container,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        right_card.grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        r_inner = ctk.CTkFrame(right_card, fg_color="transparent")
        r_inner.pack(fill="both", expand=True, padx=20, pady=18)

        # Header
        r_head = ctk.CTkFrame(r_inner, fg_color="transparent")
        r_head.pack(fill="x", pady=(0, 10))

        lbl_r_title = ctk.CTkLabel(
            r_head,
            text="🎯 Goal Alignment & Trajectory Radar",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_r_title.pack(side="left")

        lbl_r_badge = ctk.CTkLabel(
            r_head,
            text=f"● {momentum}",
            font=get_font(size=11, weight="bold"),
            text_color="#065f46",
            fg_color="#d1fae5",
            corner_radius=6,
            padx=8,
            pady=2,
        )
        lbl_r_badge.pack(side="right")

        # -------------------------------------------------------------
        # Section A: Time Allocation & Objective Breakdown
        # -------------------------------------------------------------
        alloc_box = ctk.CTkFrame(
            r_inner,
            fg_color=THEME["card_inner"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["border"],
        )
        alloc_box.pack(fill="x", pady=(0, 12))

        ab_inner = ctk.CTkFrame(alloc_box, fg_color="transparent")
        ab_inner.pack(fill="x", padx=16, pady=14)

        score_row = ctk.CTkFrame(ab_inner, fg_color="transparent")
        score_row.pack(fill="x")

        lbl_pct = ctk.CTkLabel(
            score_row,
            text=f"{align_pct}%",
            font=get_font(size=32, weight="bold"),
            text_color=THEME["yellow_title"],
        )
        lbl_pct.pack(side="left")

        score_info = ctk.CTkFrame(score_row, fg_color="transparent")
        score_info.pack(side="left", fill="x", expand=True, padx=12)

        lbl_sc_title = ctk.CTkLabel(
            score_info,
            text="Objective Momentum",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_sc_title.pack(fill="x")

        lbl_sc_desc = ctk.CTkLabel(
            score_info,
            text=f"{focused_hrs} hrs invested directly into target deliverables",
            font=get_font(size=11),
            text_color=THEME["text_secondary"],
            anchor="w",
        )
        lbl_sc_desc.pack(fill="x")

        # Category Time Allocation Rows
        alloc_rows = ctk.CTkFrame(ab_inner, fg_color="transparent")
        alloc_rows.pack(fill="x", pady=(10, 0))

        for tb in time_breakdown[:4]:
            tb_row = ctk.CTkFrame(alloc_rows, fg_color="transparent")
            tb_row.pack(fill="x", pady=2)

            lbl_tb_label = ctk.CTkLabel(
                tb_row,
                text=tb["label"],
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_tb_label.pack(side="left")

            lbl_tb_val = ctk.CTkLabel(
                tb_row,
                text=f"{tb['hours']}h ({tb['pct']}%)",
                font=get_font(size=11, weight="bold"),
                text_color=tb.get("color", THEME["denim_blue"]),
            )
            lbl_tb_val.pack(side="right")

            lbl_tb_detail = ctk.CTkLabel(
                alloc_rows,
                text=tb["detail"],
                font=get_font(size=10),
                text_color=THEME["text_muted"],
                anchor="w",
            )
            lbl_tb_detail.pack(fill="x", pady=(0, 4))

        # -------------------------------------------------------------
        # Section B: Milestone Execution Roadmap
        # -------------------------------------------------------------
        ms_card = ctk.CTkFrame(
            r_inner,
            fg_color=THEME["card_inner"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["border"],
        )
        ms_card.pack(fill="x", pady=(0, 12))

        ms_inner = ctk.CTkFrame(ms_card, fg_color="transparent")
        ms_inner.pack(fill="x", padx=16, pady=12)

        ms_head = ctk.CTkFrame(ms_inner, fg_color="transparent")
        ms_head.pack(fill="x", pady=(0, 6))

        lbl_ms_title = ctk.CTkLabel(
            ms_head,
            text="🗺️ Milestone Execution Roadmap",
            font=get_font(size=13, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        lbl_ms_title.pack(side="left")

        lbl_ms_goal = ctk.CTkLabel(
            ms_head,
            text=f"Target: {target_goal[:28]}...",
            font=get_font(size=10, weight="bold"),
            text_color=THEME["denim_blue"],
        )
        lbl_ms_goal.pack(side="right")

        for m_item in milestones:
            st = m_item.get("status", "planned")
            st_color = "#166534" if st == "completed" else ("#b45309" if st == "in_progress" else THEME["text_muted"])
            st_bg = "#dcfce7" if st == "completed" else ("#fef3c7" if st == "in_progress" else THEME["card_bg"])

            m_row = ctk.CTkFrame(ms_inner, fg_color="transparent")
            m_row.pack(fill="x", pady=3)

            lbl_m_name = ctk.CTkLabel(
                m_row,
                text=m_item.get("stage", ""),
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
            )
            lbl_m_name.pack(side="left", fill="x", expand=True)

            lbl_m_badge = ctk.CTkLabel(
                m_row,
                text=m_item.get("status_label", ""),
                font=get_font(size=10, weight="bold"),
                text_color=st_color,
                fg_color=st_bg,
                corner_radius=4,
                padx=6,
                pady=1,
            )
            lbl_m_badge.pack(side="right")

            lbl_m_desc = ctk.CTkLabel(
                ms_inner,
                text=m_item.get("detail", ""),
                font=get_font(size=10),
                text_color=THEME["text_secondary"],
                anchor="w",
                wraplength=380,
                justify="left",
            )
            lbl_m_desc.pack(fill="x", pady=(0, 4))

        # -------------------------------------------------------------
        # Section C: Minion AI Strategic Coaching Levers
        # -------------------------------------------------------------
        coach_card = ctk.CTkFrame(
            r_inner,
            fg_color="#fefce8",
            border_width=1,
            border_color="#fde047",
            corner_radius=10,
        )
        coach_card.pack(fill="x")

        c_box = ctk.CTkFrame(coach_card, fg_color="transparent")
        c_box.pack(fill="x", padx=16, pady=12)

        lbl_c_head = ctk.CTkLabel(
            c_box,
            text="💡 Minion Strategic Trajectory Coaching",
            font=get_font(size=12, weight="bold"),
            text_color="#854d0e",
            anchor="w",
        )
        lbl_c_head.pack(fill="x", pady=(0, 4))

        for ct in coaching_tactics[:2]:
            t_row = ctk.CTkFrame(c_box, fg_color="transparent")
            t_row.pack(fill="x", pady=2)

            lbl_t_name = ctk.CTkLabel(
                t_row,
                text=ct.get("title", ""),
                font=get_font(size=11, weight="bold"),
                text_color="#713f12",
                anchor="w",
            )
            lbl_t_name.pack(fill="x")

            lbl_t_desc = ctk.CTkLabel(
                t_row,
                text=ct.get("desc", ""),
                font=get_font(size=10),
                text_color="#92400e",
                anchor="w",
                wraplength=380,
                justify="left",
            )
            lbl_t_desc.pack(fill="x")

        # Load existing profile values into inputs
        self._load_profile_data()

    # =============================================================
    # Tab 5: 🗃️ Memory Vault & Facts Stream
    # =============================================================
    def _render_vault_tab(self) -> None:
        """Render filterable memory facts stream, PC specs card, and manual fact adder."""
        # Top: Category Filter Chips
        chips_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        chips_frame.pack(fill="x", pady=(2, 6))

        lbl_filter = ctk.CTkLabel(
            chips_frame,
            text="Filter Memory:",
            font=get_font(size=11, weight="bold"),
            text_color=THEME["text_secondary"],
        )
        lbl_filter.pack(side="left", padx=(0, 8))

        for display_name, cat_val in self.FACT_CATEGORIES:
            is_active = (cat_val == self.active_fact_filter)
            btn = ctk.CTkButton(
                chips_frame,
                text=display_name,
                command=lambda cv=cat_val: self._on_fact_filter_changed(cv),
                fg_color=THEME["denim_blue"] if is_active else THEME["card_bg"],
                hover_color=THEME["denim_hover"] if is_active else THEME["card_hover"],
                text_color="#ffffff" if is_active else THEME["text_secondary"],
                font=get_font(size=11, weight="bold" if is_active else "normal"),
                height=28,
                corner_radius=14,
                border_width=0 if is_active else 1,
                border_color=THEME["border"],
                cursor="hand2",
            )
            btn.pack(side="left", padx=3)

        # Add Custom Memory Fact Row
        add_box = ctk.CTkFrame(
            self.main_content,
            fg_color=THEME["card_bg"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border"],
        )
        add_box.pack(fill="x", pady=(0, 8))

        add_inner = ctk.CTkFrame(add_box, fg_color="transparent")
        add_inner.pack(fill="x", padx=14, pady=8)

        lbl_teach = ctk.CTkLabel(
            add_inner,
            text="➕ Teach Minion a New Fact:",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_teach.pack(side="left", padx=(0, 10))

        self.entry_new_fact = ctk.CTkEntry(
            add_inner,
            placeholder_text="e.g. Focuses best in 45-minute sprint intervals...",
            placeholder_text_color=THEME["text_muted"],
            font=get_font(size=12),
            height=32,
            border_width=1,
            border_color=THEME["input_border"],
            fg_color=THEME["card_inner"],
            text_color=THEME["text_primary"],
        )
        self.entry_new_fact.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_new_fact.bind("<Return>", lambda e: self._handle_add_custom_fact())

        btn_add = ctk.CTkButton(
            add_inner,
            text="Teach Minion",
            command=self._handle_add_custom_fact,
            fg_color=THEME["denim_blue"],
            hover_color=THEME["denim_hover"],
            height=32,
            width=110,
            font=get_font(size=11, weight="bold"),
            cursor="hand2",
        )
        btn_add.pack(side="right")

        # Two columns: Facts Stream (left, scrollable) + PC Hardware Specs (right, permanently pinned!)
        vault_grid = ctk.CTkFrame(self.main_content, fg_color="transparent")
        vault_grid.pack(fill="both", expand=True, pady=0)
        vault_grid.grid_columnconfigure(0, weight=3)
        vault_grid.grid_columnconfigure(1, weight=2)
        vault_grid.grid_rowconfigure(0, weight=1)

        # Facts Stream Container (Scrollable independently so specs stay pinned on screen!)
        self.facts_container = ctk.CTkScrollableFrame(vault_grid, fg_color="transparent")
        self.facts_container.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        # PC Hardware Specs Card (Stays firmly pinned in the right column!)
        pc_card = ctk.CTkFrame(
            vault_grid,
            fg_color=THEME["card_bg"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["border"],
        )
        pc_card.grid(row=0, column=1, sticky="nsew")

        pc_inner = ctk.CTkFrame(pc_card, fg_color="transparent")
        pc_inner.pack(fill="both", expand=True, padx=12, pady=(10, 8))

        pc_top = ctk.CTkFrame(pc_inner, fg_color="transparent")
        pc_top.pack(fill="x", pady=(0, 6))

        lbl_pc_title = ctk.CTkLabel(
            pc_top,
            text="💻 PC & Environment Specs",
            font=get_font(size=14, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_pc_title.pack(side="left")

        btn_box = ctk.CTkFrame(pc_top, fg_color="transparent")
        btn_box.pack(side="right")

        badge_pinned = ctk.CTkLabel(
            btn_box,
            text="📌 PINNED",
            font=get_font(size=10, weight="bold"),
            text_color=THEME["denim_blue"],
            fg_color=THEME["denim_tint"],
            corner_radius=4,
            padx=6,
            pady=2,
        )
        badge_pinned.pack(side="left", padx=(0, 6))

        btn_refresh_pc = ctk.CTkButton(
            btn_box,
            text="🔄 Refresh",
            command=lambda: self._refresh_pc_specs(force=True),
            width=70,
            height=26,
            fg_color=THEME["card_inner"],
            hover_color=THEME["card_hover"],
            text_color=THEME["text_secondary"],
            border_width=1,
            border_color=THEME["border"],
            font=get_font(size=10, weight="bold"),
            corner_radius=4,
            cursor="hand2",
        )
        btn_refresh_pc.pack(side="left")

        # Scrollable container for rich specs cards so nothing is ever clipped
        self.pc_specs_container = ctk.CTkScrollableFrame(pc_inner, fg_color="transparent")
        self.pc_specs_container.pack(fill="both", expand=True)

        self._refresh_pc_specs(force=False)
        self._refresh_learned_facts()

    def _on_fact_filter_changed(self, category_val: str) -> None:
        """Filter memory facts stream."""
        self.active_fact_filter = category_val
        self._render_current_tab()

    def _handle_add_custom_fact(self) -> None:
        """Add a custom user-taught memory fact."""
        text = self.entry_new_fact.get().strip() if hasattr(self, "entry_new_fact") else ""
        if not text:
            return

        self.db.add_learned_fact("custom", text, confidence=1.0)
        if hasattr(self, "entry_new_fact"):
            self.entry_new_fact.delete(0, "end")
        self._refresh_learned_facts()

    def _handle_delete_fact(self, fact_id: int) -> None:
        """Remove a memory fact."""
        self.db.delete_learned_fact(fact_id)
        self._refresh_learned_facts()

    def _refresh_learned_facts(self) -> None:
        """Fetch and populate facts stream in the vault tab."""
        if not hasattr(self, "facts_container") or not self.facts_container.winfo_exists():
            return

        for child in self.facts_container.winfo_children():
            child.destroy()

        cat = None if self.active_fact_filter == "All" else self.active_fact_filter
        facts = self.db.get_learned_facts(limit=40, category=cat)

        if not facts:
            lbl_empty = ctk.CTkLabel(
                self.facts_container,
                text="No memory facts found in this category.\nClick '⚡ Deep Synthesize Memory' to infer habits from screen snapshots.",
                font=get_font(size=13),
                text_color=THEME["text_muted"],
                justify="center",
            )
            lbl_empty.pack(pady=30)
            return

        for f in facts:
            f_card = ctk.CTkFrame(
                self.facts_container,
                fg_color=THEME["card_bg"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            f_card.pack(fill="x", pady=4)

            inner = ctk.CTkFrame(f_card, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=10)

            top = ctk.CTkFrame(inner, fg_color="transparent")
            top.pack(fill="x")

            cat_name = f.get("category", "memory")
            color = self.CATEGORY_COLORS.get(cat_name, "#475569")

            badge = ctk.CTkLabel(
                top,
                text=cat_name.replace("_", " ").title(),
                font=get_font(size=10, weight="bold"),
                text_color="#ffffff",
                fg_color=color,
                corner_radius=4,
                padx=6,
                pady=1,
            )
            badge.pack(side="left")

            conf = int(f.get("confidence", 1.0) * 100)
            lbl_conf = ctk.CTkLabel(
                top,
                text=f"{conf}% confidence",
                font=get_font(size=10),
                text_color=THEME["text_muted"],
            )
            lbl_conf.pack(side="left", padx=8)

            btn_del = ctk.CTkButton(
                top,
                text="✕",
                command=lambda fid=f["id"]: self._handle_delete_fact(fid),
                width=20,
                height=20,
                fg_color="transparent",
                hover_color="#fef2f2",
                text_color="#ef4444",
                font=get_font(size=10, weight="bold"),
                corner_radius=10,
                cursor="hand2",
            )
            btn_del.pack(side="right")

            lbl_txt = ctk.CTkLabel(
                inner,
                text=f.get("fact_text", ""),
                font=get_font(size=12),
                text_color=THEME["text_primary"],
                anchor="w",
                justify="left",
                wraplength=420,
            )
            lbl_txt.pack(fill="x", pady=(4, 0))

    def _refresh_pc_specs(self, force: bool = False) -> None:
        """Query detected PC specs and render in the UI with rich, modern cardlets."""
        if not hasattr(self, "pc_specs_container") or not self.pc_specs_container.winfo_exists():
            return

        pc = self.db.get_pc_context()
        if force or not pc or not pc.get("hostname") or not pc.get("cpu_info"):
            try:
                detect_and_save_pc_context(self.db)
                pc = self.db.get_pc_context()
            except Exception as e:
                logger.warning(f"Failed to detect PC specs: {e}")

        for child in self.pc_specs_container.winfo_children():
            child.destroy()

        if not pc or not pc.get("hostname"):
            lbl_fallback = ctk.CTkLabel(
                self.pc_specs_container,
                text="Detecting workstation specs...\nClick '🔄 Refresh' to probe hardware.",
                font=get_font(size=12),
                text_color=THEME["text_muted"],
            )
            lbl_fallback.pack(pady=20)
            return

        specs_items = [
            ("💻", "Machine & Node", pc.get("hostname", "Unknown Host")),
            ("🪟", "Operating System", pc.get("os_info", "Windows")),
            ("⚡", "Processor / CPU", pc.get("cpu_info", "Multi-Core CPU")),
            ("💾", "RAM Memory", pc.get("ram_info", "RAM Info Unavailable")),
            ("📺", "Display Resolution", pc.get("display_info", "Primary Display")),
            ("🐍", "Local Runtime", pc.get("python_env", "Python 3")),
        ]

        for icon, title, val in specs_items:
            row_card = ctk.CTkFrame(
                self.pc_specs_container,
                fg_color=THEME["card_inner"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            row_card.pack(fill="x", pady=2)

            r_box = ctk.CTkFrame(row_card, fg_color="transparent")
            r_box.pack(fill="x", padx=10, pady=5)

            # Fixed-width container to guarantee 100% consistent horizontal alignment across all rows
            ic_box = ctk.CTkFrame(r_box, width=24, height=24, fg_color="transparent")
            ic_box.pack(side="left", padx=(0, 8))
            ic_box.pack_propagate(False)

            lbl_ic = ctk.CTkLabel(ic_box, text=icon, font=get_font(size=13))
            lbl_ic.place(relx=0.5, rely=0.5, anchor="center")

            info_col = ctk.CTkFrame(r_box, fg_color="transparent")
            info_col.pack(side="left", fill="x", expand=True)

            lbl_t = ctk.CTkLabel(
                info_col,
                text=title,
                font=get_font(size=10, weight="bold"),
                text_color=THEME["text_muted"],
                anchor="w",
                height=13,
            )
            lbl_t.pack(fill="x")

            lbl_v = ctk.CTkLabel(
                info_col,
                text=val,
                font=get_font(size=11, weight="bold"),
                text_color=THEME["text_primary"],
                anchor="w",
                wraplength=250,
                justify="left",
                height=16,
            )
            lbl_v.pack(fill="x")

        # Pinned Footprint & Telemetry Anchors Card
        footprint_box = ctk.CTkFrame(
            self.pc_specs_container,
            fg_color=THEME["yellow_tint"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["yellow_border"],
        )
        footprint_box.pack(fill="x", pady=(6, 0))

        fp_inner = ctk.CTkFrame(footprint_box, fg_color="transparent")
        fp_inner.pack(fill="x", padx=10, pady=7)

        lbl_fp_title = ctk.CTkLabel(
            fp_inner,
            text="📌 Pinned Workstation Context",
            font=get_font(size=11, weight="bold"),
            text_color=THEME["yellow_title"],
            anchor="w",
        )
        lbl_fp_title.pack(fill="x", pady=(0, 2))

        lbl_fp_desc = ctk.CTkLabel(
            fp_inner,
            text=(
                "• Pinned into Minion's behavioral knowledge graph\n"
                "• Injected into local Ollama prompt grounding\n"
                "• 100% private, sovereign on-device telemetry"
            ),
            font=get_font(size=10),
            text_color=THEME["text_secondary"],
            anchor="w",
            justify="left",
        )
        lbl_fp_desc.pack(fill="x")

    def _on_domain_selected(self, choice: str) -> None:
        """Handle focus profile / domain change."""
        domain_key = "general"
        for k, d in FOCUS_DOMAINS.items():
            if choice.startswith(d["icon"]) or d["title"] in choice:
                domain_key = k
                break
        self.db.set_setting("user_focus_domain", domain_key)
        profile = self.db.get_user_profile()
        profile["focus_domain"] = domain_key
        self.db.save_user_profile(profile)
        # Background re-synthesize so the archetype and metrics reflect the new domain
        self._load_knowledge_graph_async(force=True)

    def _load_profile_data(self) -> None:
        """Populate form inputs from SQLite database."""
        if not hasattr(self, "entry_name"):
            return

        profile = self.db.get_user_profile()

        if hasattr(self, "combo_domain"):
            domain_key = self.db.get_setting("user_focus_domain", "")
            role = profile.get("profession_role", "").lower()
            if not domain_key or domain_key == "general":
                if any(w in role for w in ["software", "engineer", "dev", "code", "tech"]):
                    domain_key = "software"
                elif any(w in role for w in ["write", "author", "editor", "journalis"]):
                    domain_key = "writing"
                elif any(w in role for w in ["design", "ui", "ux", "artist"]):
                    domain_key = "design"
                elif any(w in role for w in ["finance", "business", "analyst", "bank"]):
                    domain_key = "business"
                elif any(w in role for w in ["research", "academic", "scholar"]):
                    domain_key = "research"
                else:
                    domain_key = "general"
                self.db.set_setting("user_focus_domain", domain_key)

            domain_info = FOCUS_DOMAINS.get(domain_key, FOCUS_DOMAINS["general"])
            self.combo_domain.set(f"{domain_info['icon']}  {domain_info['title']}")

        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, profile.get("full_name", ""))

        self.entry_role.delete(0, "end")
        self.entry_role.insert(0, profile.get("profession_role", ""))

        self.txt_why.delete("1.0", "end")
        self.txt_why.insert("1.0", profile.get("purpose_why", ""))

        self.txt_short_goals.delete("1.0", "end")
        self.txt_short_goals.insert("1.0", profile.get("short_term_goals", ""))

        self.txt_long_goals.delete("1.0", "end")
        self.txt_long_goals.insert("1.0", profile.get("long_term_goals", ""))

        self.txt_avoid.delete("1.0", "end")
        self.txt_avoid.insert("1.0", profile.get("things_to_avoid", ""))

    def _handle_save_profile(self) -> None:
        """Save form input values to the database."""
        profile = self.db.get_user_profile()

        if hasattr(self, "combo_domain"):
            choice = self.combo_domain.get()
            domain_key = "general"
            for k, d in FOCUS_DOMAINS.items():
                if choice.startswith(d["icon"]) or d["title"] in choice:
                    domain_key = k
                    break
            profile["focus_domain"] = domain_key
            self.db.set_setting("user_focus_domain", domain_key)

        if hasattr(self, "entry_name"):
            profile["full_name"] = self.entry_name.get().strip()
            profile["profession_role"] = self.entry_role.get().strip()
            profile["purpose_why"] = self.txt_why.get("1.0", "end-1c").strip()
            profile["short_term_goals"] = self.txt_short_goals.get("1.0", "end-1c").strip()
            profile["long_term_goals"] = self.txt_long_goals.get("1.0", "end-1c").strip()
            profile["things_to_avoid"] = self.txt_avoid.get("1.0", "end-1c").strip()

        self.db.save_user_profile(profile)

        # Visual feedback toast on header button
        orig_text = self.btn_save_profile.cget("text")
        self.btn_save_profile.configure(text="✓ Saved!", fg_color="#059669", text_color="#ffffff")
        self.after(2000, lambda: self.btn_save_profile.configure(text=orig_text, fg_color=THEME["yellow"], text_color=THEME["yellow_text"]))

        # Visual feedback toast on in-form button if present
        if hasattr(self, "btn_save_inner") and self.btn_save_inner.winfo_exists():
            inner_orig = self.btn_save_inner.cget("text")
            self.btn_save_inner.configure(text="✓ Profile Saved & Synchronized!", fg_color="#059669")
            self.after(2000, lambda: self.btn_save_inner.configure(text=inner_orig, fg_color=THEME["denim_blue"]))

        # Invalidate cached knowledge graph and refresh so radar reflects any new goals
        self._load_knowledge_graph_async(force=True)

    def _handle_import_file(self) -> None:
        """Import user profile from JSON or Markdown."""
        fpath = filedialog.askopenfilename(
            title="Import Minion Context Profile",
            filetypes=[("Context Files (*.md, *.json)", "*.md;*.json"), ("Markdown Files", "*.md"), ("JSON Files", "*.json")],
        )
        if not fpath:
            return

        try:
            self.ctx.import_from_file(fpath)
            self._load_profile_data()
            self._load_knowledge_graph_async()
            messagebox.showinfo("Import Successful", f"Bello! Successfully imported context profile from:\n{os.path.basename(fpath)}")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import file:\n{str(e)}")

    def _handle_export_file(self) -> None:
        """Export current profile to JSON or Markdown."""
        fpath = filedialog.asksaveasfilename(
            title="Export Minion Context Profile",
            defaultextension=".json",
            filetypes=[("JSON File", "*.json"), ("Markdown File", "*.md")],
            initialfile="minion_user_context.json",
        )
        if not fpath:
            return

        try:
            self.ctx.export_to_file(fpath)
            messagebox.showinfo("Export Successful", f"Bello! Successfully exported context profile to:\n{os.path.basename(fpath)}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export profile:\n{str(e)}")
