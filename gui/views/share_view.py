"""
Shareable Post Generator View for ProductivityCheck.

This view allows users to synthesize ready-to-share social updates,
team standup summaries, or devlogs from their tracked screen intervals.

Architectural Rationale:
- Automates personal branding and team reporting by distilling complex,
  multi-window activity streams into crisp, professional posts.
- Features local AI generation (Ollama) with deterministic fallback,
  one-click clipboard copy, and historical post archive.
"""

from typing import Dict, Any, List
import customtkinter as ctk

from core.database import DatabaseManager
from core.share_generator import SharePostGenerator
from core.reporter import ProductivityReporter
from config import THEME, get_font


class ShareView(ctk.CTkFrame):
    """View providing post generation, tone customization, preview, and clipboard export."""

    INTERVAL_OPTIONS = [
        "Today",
        "Yesterday",
        "Past 1 Hour",
        "Past 4 Hours",
        "Past 7 Days",
    ]

    def __init__(
        self,
        master,
        db_manager: DatabaseManager,
        share_gen: SharePostGenerator,
        reporter: ProductivityReporter,
        **kwargs,
    ):
        """
        Initialize the Share View.

        Args:
            master: Parent container.
            db_manager: Database access.
            share_gen: SharePostGenerator coordinator.
            reporter: Productivity reporting helper.
        """
        super().__init__(master, fg_color="transparent", **kwargs)

        self.db = db_manager
        self.share_gen = share_gen
        self.reporter = reporter

        self._build_ui()
        self._load_recent_posts()

    def _build_ui(self) -> None:
        """Construct visual elements."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(20, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="Standup & Share Creator",
            font=get_font(size=24, weight="bold"),
            text_color=THEME["yellow_title"],
        )
        title_label.pack(anchor="w")

        sub_label = ctk.CTkLabel(
            header_frame,
            text="Bello! Transform your focus sessions into engaging standups, changelogs, or team updates",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
        )
        sub_label.pack(anchor="w", pady=(2, 0))

        # Main 2-Column Split: Generator on Left, Recent Posts History on Right
        main_body = ctk.CTkFrame(self, fg_color="transparent")
        main_body.pack(fill="both", expand=True, padx=25, pady=(5, 20))
        main_body.grid_columnconfigure(0, weight=3)
        main_body.grid_columnconfigure(1, weight=2)
        main_body.grid_rowconfigure(0, weight=1)

        # Left Column: Configuration & Generator Card
        left_card = ctk.CTkFrame(
            main_body,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        left_inner = ctk.CTkFrame(left_card, fg_color="transparent")
        left_inner.pack(fill="both", expand=True, padx=20, pady=18)

        # Options Row: Interval & Tone
        opt_row = ctk.CTkFrame(left_inner, fg_color="transparent")
        opt_row.pack(fill="x", pady=(0, 12))

        # Interval picker
        box_interval = ctk.CTkFrame(opt_row, fg_color="transparent")
        box_interval.pack(side="left", fill="x", expand=True, padx=(0, 8))

        lbl_int = ctk.CTkLabel(
            box_interval,
            text="Time Interval:",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_int.pack(anchor="w", pady=(0, 4))

        self.combo_interval = ctk.CTkComboBox(
            box_interval,
            values=self.INTERVAL_OPTIONS,
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
        self.combo_interval.set("Today")
        self.combo_interval.pack(fill="x")

        # Tone picker
        box_tone = ctk.CTkFrame(opt_row, fg_color="transparent")
        box_tone.pack(side="right", fill="x", expand=True, padx=(8, 0))

        lbl_tone = ctk.CTkLabel(
            box_tone,
            text="Tone / Audience:",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_tone.pack(anchor="w", pady=(0, 4))

        self.combo_tone = ctk.CTkComboBox(
            box_tone,
            values=self.share_gen.TONES,
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
        self.combo_tone.set("Professional (LinkedIn)")
        self.combo_tone.pack(fill="x")

        # Optional Custom Note / Milestone
        lbl_note = ctk.CTkLabel(
            left_inner,
            text="Optional Milestone / Goal Note:",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_note.pack(anchor="w", pady=(8, 4))

        self.txt_note = ctk.CTkEntry(
            left_inner,
            placeholder_text="e.g. Completed chapter draft, finalized Q3 financial model, or finished client review",
            placeholder_text_color=THEME["text_muted"],
            height=36,
            corner_radius=8,
            border_width=1,
            border_color=THEME["input_border"],
            fg_color=THEME["card_bg"],
            text_color=THEME["text_primary"],
            font=get_font(size=13),
        )
        self.txt_note.pack(fill="x", pady=(0, 14))

        # Generate Button
        self.btn_generate = ctk.CTkButton(
            left_inner,
            text="✨ Generate Shareable Post",
            command=self._handle_generate,
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            font=get_font(size=14, weight="bold"),
            height=42,
            corner_radius=8,
            cursor="hand2",
        )
        self.btn_generate.pack(fill="x", pady=(0, 14))

        # Post Preview Area
        preview_header = ctk.CTkFrame(left_inner, fg_color="transparent")
        preview_header.pack(fill="x", pady=(4, 4))

        lbl_prev = ctk.CTkLabel(
            preview_header,
            text="Generated Post Preview:",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_prev.pack(side="left")

        self.lbl_char_count = ctk.CTkLabel(
            preview_header,
            text="0 characters",
            font=get_font(size=11),
            text_color=THEME["text_muted"],
        )
        self.lbl_char_count.pack(side="right")

        self.txt_preview = ctk.CTkTextbox(
            left_inner,
            fg_color=THEME["card_inner"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            font=get_font(size=13),
            wrap="word",
        )
        self.txt_preview.pack(fill="both", expand=True, pady=(0, 10))

        # Action Buttons Row
        action_row = ctk.CTkFrame(left_inner, fg_color="transparent")
        action_row.pack(fill="x")

        self.btn_copy = ctk.CTkButton(
            action_row,
            text="📋 Copy to Clipboard",
            command=self._copy_to_clipboard,
            fg_color=THEME["denim_blue"],
            hover_color=THEME["denim_hover"],
            text_color="#ffffff",
            font=get_font(size=13, weight="bold"),
            height=36,
            corner_radius=8,
            cursor="hand2",
        )
        self.btn_copy.pack(side="right")

        # Right Column: Generated Posts History
        right_card = ctk.CTkFrame(
            main_body,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        right_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)

        right_inner = ctk.CTkFrame(right_card, fg_color="transparent")
        right_inner.pack(fill="both", expand=True, padx=16, pady=18)

        lbl_hist = ctk.CTkLabel(
            right_inner,
            text="Generated Posts Archive",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_hist.pack(anchor="w", pady=(0, 10))

        self.scroll_history = ctk.CTkScrollableFrame(
            right_inner,
            fg_color=THEME["card_inner"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border"],
        )
        self.scroll_history.pack(fill="both", expand=True)

    def _handle_generate(self) -> None:
        """Trigger post generation via Ollama AI."""
        interval = self.combo_interval.get()
        tone = self.combo_tone.get()
        user_milestone = self.txt_note.get().strip()

        start_iso, end_iso = self.reporter.get_time_interval_bounds(interval)

        self.btn_generate.configure(state="disabled", text="⏳ Synthesizing Post...")

        import threading

        def _worker():
            post_content = self.share_gen.generate_post(
                start_iso=start_iso,
                end_iso=end_iso,
                tone=tone,
                user_milestone=user_milestone,
            )
            self.after(0, lambda: self._on_post_generated(post_content, tone))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_post_generated(self, post_content: str, tone: str) -> None:
        """Display generated post in text area and save to archive."""
        self.btn_generate.configure(state="normal", text="✨ Generate Shareable Post")

        # Update text box
        self.txt_preview.delete("1.0", "end")
        self.txt_preview.insert("1.0", post_content)

        # Update char count
        self.lbl_char_count.configure(text=f"{len(post_content)} characters")

        # Save to database
        self.db.save_share_post(tone=tone, content=post_content)

        # Reload archive list
        self._load_recent_posts()

    def _copy_to_clipboard(self) -> None:
        """Copy generated post content to Windows clipboard with visual button confirmation."""
        text = self.txt_preview.get("1.0", "end-1c").strip()
        if not text:
            return

        self.clipboard_clear()
        self.clipboard_append(text)

        # Temporary button confirmation
        self.btn_copy.configure(text="✔ Copied to Clipboard!", fg_color="#059669")
        self.after(2000, lambda: self.btn_copy.configure(text="📋 Copy to Clipboard", fg_color=THEME["denim_blue"]))

    def _load_recent_posts(self) -> None:
        """Populate recent posts in history drawer."""
        for child in self.scroll_history.winfo_children():
            child.destroy()

        posts = self.db.get_recent_posts(limit=15)
        if not posts:
            lbl = ctk.CTkLabel(
                self.scroll_history,
                text="No posts generated yet.\nGenerate your first post on the left!",
                font=get_font(size=12),
                text_color=THEME["text_muted"],
            )
            lbl.pack(pady=30)
            return

        for p in posts:
            card = ctk.CTkFrame(
                self.scroll_history,
                fg_color=THEME["card_bg"],
                corner_radius=8,
                border_width=1,
                border_color=THEME["border"],
            )
            card.pack(fill="x", padx=4, pady=4)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(8, 2))

            tone_lbl = ctk.CTkLabel(
                top,
                text=p["tone"],
                font=get_font(size=11, weight="bold"),
                text_color=THEME["denim_blue"],
            )
            tone_lbl.pack(side="left")

            created_str = p["created_at"][11:16] if len(p["created_at"]) >= 16 else ""
            date_lbl = ctk.CTkLabel(
                top,
                text=created_str,
                font=get_font(size=10),
                text_color=THEME["text_muted"],
            )
            date_lbl.pack(side="right")

            preview_snippet = p["content"][:100].replace("\n", " ") + "..."
            snippet_lbl = ctk.CTkLabel(
                card,
                text=preview_snippet,
                font=get_font(size=11),
                text_color=THEME["text_secondary"],
                wraplength=220,
                justify="left",
                anchor="w",
            )
            snippet_lbl.pack(fill="x", padx=10, pady=(0, 6))

            # Click to load into preview
            btn_load = ctk.CTkButton(
                card,
                text="Load to Preview",
                command=lambda text=p["content"]: self._load_into_preview(text),
                fg_color=THEME["card_inner"],
                hover_color=THEME["card_hover"],
                text_color=THEME["text_primary"],
                border_width=1,
                border_color=THEME["border"],
                height=24,
                font=get_font(size=10, weight="bold"),
                corner_radius=4,
                cursor="hand2",
            )
            btn_load.pack(anchor="e", padx=10, pady=(0, 8))

    def _load_into_preview(self, text: str) -> None:
        """Load selected archived post into active preview editor."""
        self.txt_preview.delete("1.0", "end")
        self.txt_preview.insert("1.0", text)
        self.lbl_char_count.configure(text=f"{len(text)} characters")
