"""
Minion AI Chat View — Clean, Minimalist Productivity Intelligence (Gemini/ChatGPT Style).

This view presents an uncluttered, modern conversational interface:
1. Gemini-Style Hero Landing State (Default):
   - Centered large dynamic Minion greeting header (playful & serious mix).
   - Centered sleek pill-shaped query input bar with model status indicator.
   - Clean, vertically stacked suggestion prompts with icons and soft hover highlights.
2. Active Chat Stream State:
   - Smoothly transitions when the user queries to display full conversational history.
   - Preserves user bubbles (Denim Blue) and Minion AI answers (Dark Slate + Banana tag).
   - Bottom input bar for continuous contextual follow-up questions.
   - Top-right '➕ New Question / Home' button to return to the minimalist landing hero at any time.
3. Asynchronous Inference:
   - Telemetry lookup and local LLM synthesis run in a daemon thread so the UI never blocks.
"""

import random
import threading
import customtkinter as ctk

from config import THEME, get_font
from core.database import DatabaseManager
from core.ai_agent import OllamaAgent
from core.project_intelligence import open_local_server
from gui.views.minion_crew import MinionCrewWidget

# Playful, Charismatic Minion Greetings (Loyal Focus Assistants talking to the Boss)
MINION_GREETINGS = [
    ("Where should we start, boss? 🍌", "Ask your Minions about your focus intervals, apps, or projects today."),
    ("Bello! What are we conquering today, boss?", "The Minion crew is on duty tracking every minute of work."),
    ("Tulaliloo ti amo! Where did the hours go?", "Ask about specific hours, projects, or applications."),
    ("Banana mode engaged! Tracking your output.", "Need a summary of today's deep work or research sprints?"),
    ("Poopaye distractions! Ready to inspect focus?", "Compare real work against distractions with one question."),
    ("Focus mode activated! What did you accomplish today?", "We can break down your active applications and windows."),
]

# Suggestion Prompts formatted as playful, direct boss commands (clean glyphs, zero broken emojis)
SUGGESTION_PROMPTS = [
    ("💡", "How can we improve our active project architecture?"),
    ("🚀", "Check local dev servers & active endpoints"),
    ("🛠️", "What tools am I using and how to 10x velocity?"),
    ("✦", "What did we achieve in our latest sprint?"),
]


class ChatView(ctk.CTkFrame):
    """Conversational focus lounge providing work log exploration and interactive Minion crew."""

    def __init__(
        self,
        master,
        db_manager: DatabaseManager,
        ai_agent: OllamaAgent,
        **kwargs,
    ):
        """
        Initialize the Minion Lounge View.

        Args:
            master: Parent container frame.
            db_manager: Database access for retrieving factual telemetry.
            ai_agent: Ollama local LLM coordinator.
        """
        super().__init__(master, fg_color="transparent", **kwargs)

        self.db = db_manager
        self.ai = ai_agent
        self.is_thinking = False
        self.current_greeting_idx = 0
        self._cycler_timer_id = None
        self._has_visited_once = False
        self.chat_history: list = []

        self._build_ui()
        self._reset_long_cycler_timer()

    def _build_ui(self) -> None:
        """Construct the visual hierarchy with Hero Landing State and Active Chat State."""
        # -------------------------------------------------------------
        # 1. HERO LANDING CONTAINER (Playful Centered Layout)
        # -------------------------------------------------------------
        self.hero_container = ctk.CTkFrame(self, fg_color="transparent")

        # Top discrete greeting cycler button in Hero view
        hero_top_bar = ctk.CTkFrame(self.hero_container, fg_color="transparent")
        hero_top_bar.pack(fill="x", pady=(0, 4))

        btn_cycle = ctk.CTkButton(
            hero_top_bar,
            text="✨ Cycle Greeting",
            command=self._cycle_greeting,
            fg_color="transparent",
            hover_color=THEME["card_hover"],
            text_color=THEME["text_secondary"],
            width=120,
            height=26,
            corner_radius=13,
            font=get_font(size=11),
            cursor="hand2",
        )
        btn_cycle.pack(side="right")

        # Hero Title & Subtitle (Centered)
        g_title, g_sub = MINION_GREETINGS[0]
        self.lbl_hero_greeting = ctk.CTkLabel(
            self.hero_container,
            text=g_title,
            font=get_font(size=26, weight="bold"),
            text_color=THEME["yellow_title"],
            justify="center",
        )
        self.lbl_hero_greeting.pack(pady=(0, 2))

        self.lbl_hero_sub = ctk.CTkLabel(
            self.hero_container,
            text=g_sub,
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
            justify="center",
        )
        self.lbl_hero_sub.pack(pady=(0, 16))

        # Centered Pill-Shaped Input Card
        self.hero_input_card = ctk.CTkFrame(
            self.hero_container,
            fg_color=THEME["card_bg"],
            border_width=1,
            border_color=THEME["border"],
            corner_radius=26,
            height=50,
        )
        self.hero_input_card.pack(fill="x", padx=40, pady=(0, 14))
        self.hero_input_card.pack_propagate(False)

        inner_pill = ctk.CTkFrame(self.hero_input_card, fg_color="transparent")
        inner_pill.pack(fill="both", expand=True, padx=16, pady=5)

        lbl_banana_icon = ctk.CTkLabel(
            inner_pill,
            text="🍌",
            font=get_font(size=16),
        )
        lbl_banana_icon.pack(side="left", padx=(0, 8))

        self.hero_entry = ctk.CTkEntry(
            inner_pill,
            placeholder_text="Ask your Minions about your work logs...",
            placeholder_text_color=THEME["text_muted"],
            font=get_font(size=13),
            fg_color="transparent",
            border_width=0,
            text_color=THEME["text_primary"],
        )
        self.hero_entry.pack(side="left", fill="both", expand=True)
        self.hero_entry.bind("<Return>", lambda event: self._handle_hero_submit())

        # Status badge indicator
        lbl_model_pill = ctk.CTkLabel(
            inner_pill,
            text="● Minions On Duty",
            font=get_font(size=11, weight="bold"),
            text_color="#0284c7",
        )
        lbl_model_pill.pack(side="left", padx=(8, 12))

        # Send Arrow Button
        self.btn_hero_send = ctk.CTkButton(
            inner_pill,
            text="➔",
            command=self._handle_hero_submit,
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            font=get_font(size=14, weight="bold"),
            width=34,
            height=34,
            corner_radius=17,
            cursor="hand2",
        )
        self.btn_hero_send.pack(side="right")

        # Suggestions Container (2x2 Grid for compact elegance)
        self.suggestions_list_frame = ctk.CTkFrame(self.hero_container, fg_color="transparent")
        self.suggestions_list_frame.pack(fill="x", padx=44, pady=(0, 12))
        self.suggestions_list_frame.grid_columnconfigure((0, 1), weight=1, uniform="sug")

        for idx, (icon, text) in enumerate(SUGGESTION_PROMPTS):
            row = idx // 2
            col = idx % 2
            btn_sug = ctk.CTkButton(
                self.suggestions_list_frame,
                text=f"  {icon}   {text}   ›",
                command=lambda p=text: self._send_suggestion(p),
                fg_color=THEME["card_bg"],
                hover_color=THEME["yellow_tint"],
                text_color=THEME["text_primary"],
                border_width=1,
                border_color=THEME["border"],
                font=get_font(size=12, weight="bold"),
                anchor="w",
                height=38,
                corner_radius=10,
                cursor="hand2",
            )
            btn_sug.grid(row=row, column=col, padx=5, pady=4, sticky="ew")

        # -------------------------------------------------------------
        # INTERACTIVE MINION CREW ANIMATION WIDGET (Bottom Center)
        # -------------------------------------------------------------
        self.minion_crew = MinionCrewWidget(self.hero_container, db_manager=self.db)
        self.minion_crew.pack(pady=(24, 0))

        # Place Hero container centrally in the window (adjusted slightly down for balanced spacing)
        self.hero_container.place(relx=0.5, rely=0.52, anchor="center", relwidth=0.88)

        # -------------------------------------------------------------
        # 2. ACTIVE CHAT CONTAINER (Conversation Stream)
        # -------------------------------------------------------------
        self.chat_container = ctk.CTkFrame(self, fg_color="transparent")
        # Kept hidden initially until user sends their first question

        # Chat Top Bar
        chat_top_bar = ctk.CTkFrame(self.chat_container, fg_color="transparent")
        chat_top_bar.pack(fill="x", padx=25, pady=(16, 8))

        self.lbl_chat_title = ctk.CTkLabel(
            chat_top_bar,
            text=g_title,
            font=get_font(size=18, weight="bold"),
            text_color=THEME["yellow_title"],
            anchor="w",
        )
        self.lbl_chat_title.pack(side="left")

        btn_new_chat = ctk.CTkButton(
            chat_top_bar,
            text="➕ New Question / Home",
            command=self._switch_to_hero,
            fg_color=THEME["card_bg"],
            hover_color=THEME["card_hover"],
            text_color=THEME["text_primary"],
            font=get_font(size=11, weight="bold"),
            width=165,
            height=30,
            corner_radius=8,
            border_width=1,
            border_color=THEME["border"],
            cursor="hand2",
        )
        btn_new_chat.pack(side="right")

        # Scrollable Conversation Container
        self.chat_scroll = ctk.CTkScrollableFrame(
            self.chat_container,
            fg_color=THEME["card_inner"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["border"],
        )
        self.chat_scroll.pack(fill="both", expand=True, padx=25, pady=(4, 10))

        # Bottom Input Bar Card
        chat_input_card = ctk.CTkFrame(
            self.chat_container,
            fg_color=THEME["card_bg"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["border"],
            height=58,
        )
        chat_input_card.pack(fill="x", padx=(25, 175), pady=(0, 16))

        chat_input_inner = ctk.CTkFrame(chat_input_card, fg_color="transparent")
        chat_input_inner.pack(fill="x", padx=12, pady=10)

        self.chat_entry = ctk.CTkEntry(
            chat_input_inner,
            placeholder_text="Ask a follow-up or search other time intervals...",
            placeholder_text_color=THEME["text_muted"],
            font=get_font(size=13),
            fg_color=THEME["card_inner"],
            border_width=1,
            border_color=THEME["input_border"],
            text_color=THEME["text_primary"],
            height=38,
            corner_radius=8,
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.chat_entry.bind("<Return>", lambda event: self._handle_chat_submit())

        self.btn_chat_send = ctk.CTkButton(
            chat_input_inner,
            text="Ask Minion 🍌",
            command=self._handle_chat_submit,
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            font=get_font(size=13, weight="bold"),
            height=38,
            width=130,
            corner_radius=8,
            cursor="hand2",
        )
        self.btn_chat_send.pack(side="right")

    # 15 minutes before an automatic idle refresh (very long duration)
    GREETING_CYCLE_INTERVAL_MS = 15 * 60 * 1000

    def _cycle_greeting(self) -> None:
        """Pick a new playful or serious greeting and update labels."""
        available = [i for i in range(len(MINION_GREETINGS)) if i != self.current_greeting_idx]
        self.current_greeting_idx = random.choice(available) if available else 0
        greeting, sub = MINION_GREETINGS[self.current_greeting_idx]
        self.lbl_hero_greeting.configure(text=greeting)
        self.lbl_hero_sub.configure(text=sub)
        self.lbl_chat_title.configure(text=greeting)
        self._reset_long_cycler_timer()

    def on_page_visited(self) -> None:
        """Called whenever the user navigates to the Minion AI chat page."""
        if getattr(self, "_has_visited_once", False):
            self._cycle_greeting()
        else:
            self._has_visited_once = True

    def _reset_long_cycler_timer(self) -> None:
        """Reset the timer that changes greeting only after a very long idle period."""
        if hasattr(self, "_cycler_timer_id") and self._cycler_timer_id:
            try:
                self.after_cancel(self._cycler_timer_id)
            except Exception:
                pass
        self._cycler_timer_id = self.after(self.GREETING_CYCLE_INTERVAL_MS, self._on_long_timer_fired)

    def _on_long_timer_fired(self) -> None:
        """Cycle greeting only after very long duration."""
        self._cycle_greeting()

    def _switch_to_chat(self) -> None:
        """Transition UI from Hero Landing view to Conversation Stream view."""
        self.hero_container.place_forget()
        self.chat_container.pack(fill="both", expand=True)

    def _switch_to_hero(self) -> None:
        """Return to the clean Hero Landing view with a freshly chosen greeting."""
        self._cycle_greeting()
        self.chat_container.pack_forget()
        self.hero_container.place(relx=0.5, rely=0.47, anchor="center", relwidth=0.86)
        self.hero_entry.focus_set()

    def _send_suggestion(self, prompt: str) -> None:
        """Trigger search using clicked suggestion chip."""
        self._switch_to_chat()
        self._dispatch_query(prompt)

    def _handle_hero_submit(self) -> None:
        """Handle submission from the centered Hero pill input."""
        query = self.hero_entry.get().strip()
        if not query or self.is_thinking:
            return
        self.hero_entry.delete(0, "end")
        self._switch_to_chat()
        self._dispatch_query(query)

    def _handle_chat_submit(self) -> None:
        """Handle submission from the bottom chat input bar."""
        query = self.chat_entry.get().strip()
        if not query or self.is_thinking:
            return
        self.chat_entry.delete(0, "end")
        self._dispatch_query(query)

    def _dispatch_query(self, query: str) -> None:
        """Execute the query asynchronously and stream message tokens in real-time."""
        self._add_user_message(query)

        # Show thinking / streaming indicator
        self.is_thinking = True
        self.btn_chat_send.configure(state="disabled", text="Thinking... 🍌")
        self.btn_hero_send.configure(state="disabled")

        # If user asks to open/test local link, trigger browser launch
        q_lower = query.lower()
        if any(k in q_lower for k in ["open & test", "open local link", "test local link", "open app", "localhost:5176"]):
            self.after(200, lambda: open_local_server("http://localhost:5176/"))

        bubble, lbl_stream = self._create_streaming_bubble()

        # Run query in background thread with streaming
        def _worker():
            import time
            last_update = [0.0]

            def on_chunk(token, accumulated_text):
                now = time.time()
                # Throttle Tkinter GUI updates slightly for smooth rendering
                if now - last_update[0] > 0.04:
                    last_update[0] = now
                    clean_text = self._clean_markdown_artifacts(accumulated_text)
                    self.after(0, lambda t=clean_text: self._update_stream_label(lbl_stream, t))

            try:
                response = self.ai.stream_chat_with_context(
                    user_query=query,
                    db_manager=self.db,
                    chat_history=self.chat_history,
                    on_chunk=on_chunk,
                )
            except Exception as e:
                response = f"🍌 Ouch! Minion ran into an error: {str(e)}"

            self.after(0, lambda: self._finalize_stream_response(bubble, lbl_stream, query, response))

        threading.Thread(target=_worker, daemon=True).start()

    def _create_streaming_bubble(self):
        """Create assistant bubble with streaming placeholder."""
        bubble = ctk.CTkFrame(
            self.chat_scroll,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        bubble.pack(anchor="w", padx=(10, 80), pady=6, fill="x")

        header_bar = ctk.CTkFrame(bubble, fg_color="transparent")
        header_bar.pack(fill="x", padx=16, pady=(10, 4))

        tag = ctk.CTkLabel(
            header_bar,
            text="🍌 MINION CREW",
            font=get_font(size=10, weight="bold"),
            text_color=THEME["yellow_title"],
            anchor="w",
        )
        tag.pack(side="left")

        lbl_stream = ctk.CTkLabel(
            bubble,
            text="🍌 Minions are checking your logs...",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
            wraplength=650,
            justify="left",
            anchor="w",
        )
        lbl_stream.pack(fill="x", padx=16, pady=(0, 12))
        self._scroll_to_bottom()
        return bubble, lbl_stream

    def _update_stream_label(self, lbl_stream, clean_text: str):
        """Update streaming label dynamically as tokens arrive."""
        try:
            if lbl_stream.winfo_exists():
                lbl_stream.configure(text=clean_text, text_color=THEME["text_primary"])
                self._scroll_to_bottom()
        except Exception:
            pass

    def _finalize_stream_response(self, bubble, lbl_stream, query: str, full_response: str) -> None:
        """Finalize streamed response, store in chat history, and apply rich card layout."""
        # Record in multi-turn memory
        self.chat_history.append({"role": "user", "content": query})
        self.chat_history.append({"role": "assistant", "content": full_response})
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]

        try:
            if lbl_stream.winfo_exists():
                lbl_stream.destroy()
        except Exception:
            pass

        self._render_bubble_content(bubble, full_response)

        self.is_thinking = False
        self.btn_chat_send.configure(state="normal", text="Ask Minion 🍌")
        self.btn_hero_send.configure(state="normal")
        self.chat_entry.focus_set()

    def _clean_markdown_artifacts(self, text: str) -> str:
        """Strip raw markdown formatting artifacts like ** or ##."""
        import re
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = text.replace('**', '')
        text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'\1', text)
        text = re.sub(r'^[#]+\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'`(.*?)`', r'\1', text)
        return text.strip()

    def _add_user_message(self, text: str):
        """Append user message bubble on the right."""
        bubble = ctk.CTkFrame(
            self.chat_scroll,
            fg_color=THEME["denim_blue"],
            corner_radius=12,
        )
        bubble.pack(anchor="e", padx=(80, 10), pady=6)

        lbl = ctk.CTkLabel(
            bubble,
            text=text,
            font=get_font(size=13),
            text_color="#ffffff",
            wraplength=600,
            justify="left",
        )
        lbl.pack(padx=14, pady=10)
        self._scroll_to_bottom()

    def _add_assistant_message(self, text: str):
        """Append Minion Crew response bubble on the left with rich structured presentation."""
        bubble = ctk.CTkFrame(
            self.chat_scroll,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        bubble.pack(anchor="w", padx=(10, 80), pady=6, fill="x")

        # Top Header Tag with Minion Badge
        header_bar = ctk.CTkFrame(bubble, fg_color="transparent")
        header_bar.pack(fill="x", padx=16, pady=(10, 4))

        tag = ctk.CTkLabel(
            header_bar,
            text="🍌 MINION CREW",
            font=get_font(size=10, weight="bold"),
            text_color=THEME["yellow_title"],
            anchor="w",
        )
        tag.pack(side="left")

        self._render_bubble_content(bubble, text)
        return bubble

    def _render_bubble_content(self, bubble, text: str) -> None:
        """Render rich markdown-free cards and paragraphs inside an assistant bubble."""
        # Sanitize text
        cleaned_text = self._clean_markdown_artifacts(text)

        # Split into semantic blocks
        raw_blocks = [b.strip() for b in cleaned_text.split("\n\n") if b.strip()]

        # If it's a short simple message (e.g. thinking placeholder or 1 line)
        if len(raw_blocks) <= 1 and len(cleaned_text) < 120 and "•" not in cleaned_text:
            lbl = ctk.CTkLabel(
                bubble,
                text=cleaned_text,
                font=get_font(size=13),
                text_color=THEME["text_primary"],
                wraplength=650,
                justify="left",
                anchor="w",
            )
            lbl.pack(fill="x", padx=16, pady=(0, 12))
            self._scroll_to_bottom()
            return bubble

        # Structured Rendering for Multi-Block Responses
        for idx, block in enumerate(raw_blocks):
            # 1. Lead / Greeting Line
            if idx == 0 and (block.startswith("🍌") or "Bello" in block or "Where should" in block):
                lbl_lead = ctk.CTkLabel(
                    bubble,
                    text=block,
                    font=get_font(size=14, weight="bold"),
                    text_color=THEME["yellow_title"],
                    wraplength=650,
                    justify="left",
                    anchor="w",
                )
                lbl_lead.pack(fill="x", padx=16, pady=(2, 6))

            # 2. Key Metrics Card
            elif any(k in block for k in ["Productivity Score", "Active Focus Time", "Idle Time"]):
                metric_card = ctk.CTkFrame(
                    bubble,
                    fg_color=THEME["card_inner"],
                    corner_radius=8,
                    border_width=1,
                    border_color=THEME["border"],
                )
                metric_card.pack(fill="x", padx=16, pady=(4, 8))

                inner = ctk.CTkFrame(metric_card, fg_color="transparent")
                inner.pack(fill="x", padx=14, pady=10)

                for line in block.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if "Productivity Score" in line:
                        lbl_m = ctk.CTkLabel(
                            inner,
                            text=line,
                            font=get_font(size=13, weight="bold"),
                            text_color=THEME["yellow_title"],
                            anchor="w",
                        )
                    elif "Active Focus Time" in line or "Idle Time" in line:
                        lbl_m = ctk.CTkLabel(
                            inner,
                            text=line,
                            font=get_font(size=12, weight="bold"),
                            text_color=THEME["denim_blue"],
                            anchor="w",
                        )
                    else:
                        lbl_m = ctk.CTkLabel(
                            inner,
                            text=line,
                            font=get_font(size=12),
                            text_color=THEME["text_primary"],
                            anchor="w",
                        )
                    lbl_m.pack(fill="x", pady=1)

            # 3. Minion Insight / Recommendation Callout
            elif "Minion Insight" in block or block.startswith("💡"):
                insight_card = ctk.CTkFrame(
                    bubble,
                    fg_color=THEME["yellow_tint"],
                    corner_radius=8,
                    border_width=1,
                    border_color=THEME["yellow_border"],
                )
                insight_card.pack(fill="x", padx=16, pady=(6, 8))

                lbl_ins = ctk.CTkLabel(
                    insight_card,
                    text=block,
                    font=get_font(size=12),
                    text_color=THEME["yellow_text"],
                    wraplength=630,
                    justify="left",
                    anchor="w",
                )
                lbl_ins.pack(fill="x", padx=14, pady=10)

            # 4. List / Bullet Section
            elif "•" in block or any(h in block for h in ["Breakdown:", "Tools Used:", "Summary:"]):
                lines = [l.strip() for l in block.splitlines() if l.strip()]
                if lines:
                    header = lines[0]
                    lbl_hdr = ctk.CTkLabel(
                        bubble,
                        text=header,
                        font=get_font(size=13, weight="bold"),
                        text_color=THEME["yellow_title"] if any(e in header for e in ["🎯", "🚀", "💻", "📊"]) else THEME["text_primary"],
                        anchor="w",
                    )
                    lbl_hdr.pack(fill="x", padx=16, pady=(6, 2))

                    for item in lines[1:]:
                        lbl_item = ctk.CTkLabel(
                            bubble,
                            text=f"  {item}",
                            font=get_font(size=12),
                            text_color=THEME["text_primary"],
                            wraplength=630,
                            justify="left",
                            anchor="w",
                        )
                        lbl_item.pack(fill="x", padx=(20, 16), pady=1)

            # 5. Standard Narrative Paragraph
            else:
                lbl_p = ctk.CTkLabel(
                    bubble,
                    text=block,
                    font=get_font(size=13),
                    text_color=THEME["text_primary"],
                    wraplength=650,
                    justify="left",
                    anchor="w",
                )
                lbl_p.pack(fill="x", padx=16, pady=3)

        # Bottom padding inside bubble
        pad_bottom = ctk.CTkFrame(bubble, fg_color="transparent", height=6)
        pad_bottom.pack(fill="x")

        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self) -> None:
        """Auto-scroll to the newest message."""
        self.after(50, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))
