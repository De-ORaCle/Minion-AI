"""
Interactive Minion Crew Widget — Cohesive Mascot Trio.

Features:
1. Unified Mascot Art Style:
   - Kevin (Tall, sprout hair, dual goggles, confident smirk)
   - Stuart (Medium, parted combed hair, single cyclops goggle, playful smirk)
   - Bob (Short, round, bald dome, green & brown heterochromia eyes, holding banana)
2. True Multi-Frame Animations (ZERO Shaking):
   - Solid, stable grounding: NO widget jitter or pady shaking!
   - Prominent, optical scale suited for the central hero dashboard.
   - Snappy cartoon keyframes (poke -> swat -> POW! -> dizzy -> settle).
3. Spontaneous Idle Shenanigans:
   - Slap Fight: Stuart pokes -> Kevin slaps -> Comic POW! -> Stuart dizzy spiral -> Bob laughs!
   - Banana Taunt: Bob presents banana -> Stuart reaches -> Bob pulls back giggling!
   - Natural, independent eye blinking.
4. Silent by Default & Dynamic Click-To-Talk:
   - Hidden speech bubble when unclicked.
   - Pops up on click with authentic Minionese + boss productivity reminder.
   - Complete quote strings (no single-letter bugs).
5. 100% Zero-Distortion Fixed Geometry.
"""

import random
import tkinter as tk
import customtkinter as ctk
from PIL import Image

from config import ASSETS_DIR, THEME, get_font

def get_personalized_quotes(speaker: str, db_manager=None) -> list[str]:
    """Return tailored quotes reflecting the user's profile and tools, with ZERO emojis."""
    profile = {}
    if db_manager:
        try:
            profile = db_manager.get_user_profile() or {}
        except Exception:
            profile = {}

    raw_name = (profile.get("full_name") or "").strip()
    if raw_name and raw_name.lower() != "boss":
        display_boss = f"Boss {raw_name}"
        short_name = raw_name
    else:
        display_boss = "Boss"
        short_name = "Boss"

    goal = (profile.get("short_term_goals") or "").strip()
    if not goal or len(goal) > 30:
        goal = "your task"

    if speaker == "Kevin":
        return [
            f"Bello {display_boss}! But... you should be working!",
            f"Bapples! Me see zero typing for 5 minutes, {short_name}!",
            f"Poka! {display_boss}, time is ticking! Focus on {goal}!",
            f"Bi-do! No slacking in Minion lab! Back to code!",
            f"Kampai! Finish your sprint, then banana party for everyone!",
            f"Stuart, stop poking {display_boss}! {short_name} is working hard!",
            f"Tulaliloo ti amo! But {display_boss} need to finish tasks first!",
            f"Para tu! Kevin keeps the team on schedule! Back to work, {short_name}!",
            f"Kevin checked the sprint board, {display_boss}. Time to focus!",
            f"Stay sharp, {short_name}! Minion crew is counting on you!",
        ]
    elif speaker == "Stuart":
        return [
            f"Bello! Me want banana... and {display_boss} need focus!",
            f"Poopaye procrastination! Hello deep focus, {short_name}!",
            f"Baboi! Stop clicking me and finish your code, {short_name}!",
            f"Tatata bala tu! Me play ukulele while {display_boss} builds great things!",
            f"Muak muak muak! You got this, {display_boss}! Now type fast!",
            f"Pwede na? Can we take a banana break yet, {display_boss}?",
            f"Underwear! Me mean, stay focused, {short_name}!",
            f"BEE-DO BEE-DO! Procrastination police detected! Back to work!",
            f"Hehe, Kevin is looking! Pretend to type fast, {short_name}!",
            f"Stuart is on guard duty! No slacking allowed, {short_name}!",
        ]
    else:  # Bob
        return [
            f"Bello {display_boss}! Me love banana! Does {short_name} love work?",
            f"Luk at tu! {display_boss} looking super focused and productive today!",
            f"Tank yu! But {display_boss}... should not you be typing right now?",
            f"Gelato! Work hard now, ice cream celebration later, {short_name}!",
            f"Para tu! Me guard {display_boss}'s focus with my life!",
            f"Bananaaaa! {short_name} focus score is rising high today!",
            f"Choko! Me thought {display_boss} was in a deep work sprint?",
            f"Muak! Tim the teddy bear says {display_boss} is the best!",
            f"Bob is cheering for you, {short_name}! Keep going strong!",
        ]


class MinionCrewWidget(ctk.CTkFrame):
    """Living, cohesive Minion mascot trio with multi-frame animated interactions."""

    def __init__(self, master, db_manager=None, **kwargs):
        # Strict dimensions guarantee 0px layout reflow or page jitter
        super().__init__(
            master,
            fg_color="transparent",
            width=520,
            height=180,
            **kwargs,
        )
        self.pack_propagate(False)

        self.db_manager = db_manager
        if self.db_manager is None:
            try:
                from core.database import DatabaseManager
                self.db_manager = DatabaseManager()
            except Exception:
                self.db_manager = None

        self.banana_count = 0
        self.is_busy = False
        self.current_speaker = "Kevin"
        self._bubble_timer = None
        self._shenanigan_timer = None
        self._blink_timer = None
        self._hovered_minion = None

        self._load_sprites()
        self._build_ui()
        self._schedule_natural_blinks()
        self._schedule_next_shenanigan(3000)

    def _load_sprites(self) -> None:
        """Load unified, cohesive mascot sprites scaled to prominent hero proportions."""
        # Visual display sizes (scaled up for prominent, crisp hero presence)
        self.dim_kevin = (96, 133)
        self.dim_stuart = (96, 133)
        self.dim_bob = (96, 112)

        def _get(filename: str):
            p = ASSETS_DIR / filename
            return Image.open(p) if p.exists() else Image.open(ASSETS_DIR / "icon.png")

        # Kevin Sprites
        img_k_idle = _get("kevin_idle.png")
        img_k_blink = _get("kevin_blink.png")
        img_k_talk = _get("kevin_talk.png")
        img_k_poked = _get("kevin_poked.png")
        img_k_slap = _get("kevin_slap.png")

        self.sp_k_idle = ctk.CTkImage(light_image=img_k_idle, dark_image=img_k_idle, size=self.dim_kevin)
        self.sp_k_blink = ctk.CTkImage(light_image=img_k_blink, dark_image=img_k_blink, size=self.dim_kevin)
        self.sp_k_talk = ctk.CTkImage(light_image=img_k_talk, dark_image=img_k_talk, size=self.dim_kevin)
        self.sp_k_poked = ctk.CTkImage(light_image=img_k_poked, dark_image=img_k_poked, size=self.dim_kevin)
        self.sp_k_slap = ctk.CTkImage(light_image=img_k_slap, dark_image=img_k_slap, size=self.dim_kevin)

        # Stuart Sprites
        img_s_idle = _get("stuart_idle.png")
        img_s_blink = _get("stuart_blink.png")
        img_s_talk = _get("stuart_talk.png")
        img_s_dizzy = _get("stuart_dizzy.png")
        img_s_poke = _get("stuart_poke.png")

        self.sp_s_idle = ctk.CTkImage(light_image=img_s_idle, dark_image=img_s_idle, size=self.dim_stuart)
        self.sp_s_blink = ctk.CTkImage(light_image=img_s_blink, dark_image=img_s_blink, size=self.dim_stuart)
        self.sp_s_talk = ctk.CTkImage(light_image=img_s_talk, dark_image=img_s_talk, size=self.dim_stuart)
        self.sp_s_dizzy = ctk.CTkImage(light_image=img_s_dizzy, dark_image=img_s_dizzy, size=self.dim_stuart)
        self.sp_s_poke = ctk.CTkImage(light_image=img_s_poke, dark_image=img_s_poke, size=self.dim_stuart)

        # Bob Sprites
        img_b_idle = _get("bob_idle.png")
        img_b_banana = _get("bob_banana.png")
        img_b_blink = _get("bob_blink.png")
        img_b_talk = _get("bob_talk.png")

        self.sp_b_idle = ctk.CTkImage(light_image=img_b_idle, dark_image=img_b_idle, size=self.dim_bob)
        self.sp_b_banana = ctk.CTkImage(light_image=img_b_banana, dark_image=img_b_banana, size=self.dim_bob)
        self.sp_b_blink = ctk.CTkImage(light_image=img_b_blink, dark_image=img_b_blink, size=self.dim_bob)
        self.sp_b_talk = ctk.CTkImage(light_image=img_b_talk, dark_image=img_b_talk, size=self.dim_bob)

        # Comic FX Overlays
        img_pow = _get("comic_pow.png")
        img_poke = _get("comic_poke.png")
        self.sp_pow = ctk.CTkImage(light_image=img_pow, dark_image=img_pow, size=(54, 36))
        self.sp_poke = ctk.CTkImage(light_image=img_poke, dark_image=img_poke, size=(54, 36))

    def _build_ui(self) -> None:
        """Construct the fixed-dimension stage, characters, and dynamic speech bubble."""
        # Top Header Slot: Fixed height (44px) for comic speech balloon
        self.bubble_slot = ctk.CTkFrame(self, fg_color="transparent", height=44, width=520)
        self.bubble_slot.pack_propagate(False)
        self.bubble_slot.pack(pady=(0, 0))

        # Comic Speech Bubble (HIDDEN by default per user requirement 1)
        self.speech_bubble = ctk.CTkFrame(
            self.bubble_slot,
            fg_color=THEME["card_bg"],
            corner_radius=14,
            border_width=2,
            border_color=THEME["yellow"],
        )

        bubble_inner = ctk.CTkFrame(self.speech_bubble, fg_color="transparent")
        bubble_inner.pack(padx=14, pady=4)

        self.lbl_quote = ctk.CTkLabel(
            bubble_inner,
            text="",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["text_primary"],
            wraplength=420,
            justify="center",
        )
        self.lbl_quote.pack()

        # Downward indicator arrow
        self.lbl_tail = ctk.CTkLabel(
            self.bubble_slot,
            text="▼",
            font=get_font(size=9, weight="bold"),
            text_color=THEME["yellow"],
            height=8,
        )

        # Middle Container: Mascot Stage (Fixed Height: 135px, Width: 320px for tight close crew)
        self.stage_frame = ctk.CTkFrame(self, fg_color="transparent", height=135, width=320)
        self.stage_frame.pack_propagate(False)
        self.stage_frame.pack()

        # 1. KEVIN (Left) — Standing shoulder-to-shoulder with Stuart
        self.box_kevin = ctk.CTkFrame(self.stage_frame, fg_color="transparent", width=96, height=135)
        self.box_kevin.pack_propagate(False)
        self.box_kevin.pack(side="left", padx=(0, 2))

        self.lbl_kevin = ctk.CTkLabel(
            self.box_kevin,
            image=self.sp_k_idle,
            text="",
            cursor="hand2",
        )
        self.lbl_kevin.pack(side="bottom", anchor="s")
        self.lbl_kevin.bind("<Enter>", lambda e: self._on_hover_enter("Kevin"))
        self.lbl_kevin.bind("<Leave>", lambda e: self._on_hover_leave("Kevin"))
        self.lbl_kevin.bind("<Button-1>", lambda e: self._on_minion_clicked("Kevin"))

        # Comic FX Overlay (POKE! and POW! bursts)
        self.lbl_fx = ctk.CTkLabel(self.stage_frame, image=self.sp_pow, text="")

        # 2. STUART (Center) — Tight gap right next to Kevin & Bob
        self.box_stuart = ctk.CTkFrame(self.stage_frame, fg_color="transparent", width=96, height=135)
        self.box_stuart.pack_propagate(False)
        self.box_stuart.pack(side="left", padx=(2, 2))

        self.lbl_stuart = ctk.CTkLabel(
            self.box_stuart,
            image=self.sp_s_idle,
            text="",
            cursor="hand2",
        )
        self.lbl_stuart.pack(side="bottom", anchor="s")
        self.lbl_stuart.bind("<Enter>", lambda e: self._on_hover_enter("Stuart"))
        self.lbl_stuart.bind("<Leave>", lambda e: self._on_hover_leave("Stuart"))
        self.lbl_stuart.bind("<Button-1>", lambda e: self._on_minion_clicked("Stuart"))

        # 3. BOB (Right) — Tight gap next to Stuart
        self.box_bob = ctk.CTkFrame(self.stage_frame, fg_color="transparent", width=96, height=135)
        self.box_bob.pack_propagate(False)
        self.box_bob.pack(side="left", padx=(2, 0))

        self.lbl_bob = ctk.CTkLabel(
            self.box_bob,
            image=self.sp_b_banana,
            text="",
            cursor="hand2",
        )
        self.lbl_bob.pack(side="bottom", anchor="s")
        self.lbl_bob.bind("<Enter>", lambda e: self._on_hover_enter("Bob"))
        self.lbl_bob.bind("<Leave>", lambda e: self._on_hover_leave("Bob"))
        self.lbl_bob.bind("<Button-1>", lambda e: self._on_minion_clicked("Bob"))

    # ==========================================================================
    # TRUE IDLE BLINKING (Completely Stably Grounded - No Shaking!)
    # ==========================================================================
    def _schedule_natural_blinks(self) -> None:
        """Periodic, natural eye blinking without any image shaking."""
        delay = random.randint(2800, 4200)
        self._blink_timer = self.after(delay, self._perform_blink)

    def _perform_blink(self) -> None:
        """Trigger an eye blink on a random minion or all three."""
        if not self.is_busy:
            target = random.choice(["Kevin", "Stuart", "Bob", "all"])
            if target in ("Kevin", "all"):
                self.lbl_kevin.configure(image=self.sp_k_blink)
                self.after(140, lambda: self.lbl_kevin.configure(image=self.sp_k_idle))
            if target in ("Stuart", "all"):
                self.after(60, lambda: self.lbl_stuart.configure(image=self.sp_s_blink))
                self.after(200, lambda: self.lbl_stuart.configure(image=self.sp_s_idle))
            if target in ("Bob", "all"):
                self.after(120, lambda: self.lbl_bob.configure(image=self.sp_b_blink))
                self.after(260, lambda: self.lbl_bob.configure(image=self.sp_b_banana))

        self._schedule_natural_blinks()

    # ==========================================================================
    # INTERACTION: HOVER & CLICK
    # ==========================================================================
    def _on_hover_enter(self, name: str) -> None:
        """Gentle lift inside fixed container on hover (zero external page shift)."""
        self._hovered_minion = name
        if not self.is_busy:
            lbl = self._get_label(name)
            lbl.pack_configure(pady=(0, 4))

    def _on_hover_leave(self, name: str) -> None:
        """Reset internal pad on mouse leave."""
        self._hovered_minion = None
        if not self.is_busy:
            lbl = self._get_label(name)
            lbl.pack_configure(pady=(0, 0))

    def _on_minion_clicked(self, name: str) -> None:
        """Handle clicking any Minion: talks, smiles, and pops up speech bubble."""
        self.banana_count += 1
        self.current_speaker = name
        self.is_busy = True

        # Personalized Quote Selection (Reflects boss profile, ZERO emojis, no generic jargon)
        speaker_quotes = get_personalized_quotes(name, self.db_manager)
        quote_text = random.choice(speaker_quotes)

        # Mount and display speech bubble directly above the specific clicked speaker
        self.lbl_quote.configure(text=quote_text)

        # Dynamic horizontal alignment pointing directly at the clicked Minion's head
        if name == "Kevin":
            rel_tail = 0.31    # Directly above Kevin's head / sprout hair
            rel_bubble = 0.38  # Shifted left towards Kevin
        elif name == "Bob":
            rel_tail = 0.69    # Directly above Bob's round bald head
            rel_bubble = 0.62  # Shifted right towards Bob
        else:  # Stuart (Center)
            rel_tail = 0.50    # Directly above Stuart's cyclops goggle
            rel_bubble = 0.50  # Centered

        self.speech_bubble.place(relx=rel_bubble, y=0, anchor="n")
        self.lbl_tail.place(relx=rel_tail, y=33, anchor="n")

        if self._bubble_timer:
            self.after_cancel(self._bubble_timer)
        self._bubble_timer = self.after(4500, self._hide_bubble)

        # Switch sprite to talking expression
        lbl = self._get_label(name)
        talk_sp = self._get_sprite(name, "talk")
        idle_sp = self._get_sprite(name, "idle")

        lbl.configure(image=talk_sp)
        lbl.pack_configure(pady=(0, 6))

        def _settle():
            lbl.configure(image=idle_sp)
            lbl.pack_configure(pady=(0, 0))
            self.is_busy = False

        self.after(1400, _settle)

    def _hide_bubble(self) -> None:
        """Dismiss speech bubble cleanly."""
        self.speech_bubble.place_forget()
        self.lbl_tail.place_forget()
        self.lbl_quote.configure(text="")

    # ==========================================================================
    # AUTONOMOUS IDLE SHENANIGANS (Actual Frame Swaps - No Shaking!)
    # ==========================================================================
    def _schedule_next_shenanigan(self, delay_ms: int = None) -> None:
        """Schedule the next spontaneous comedy sketch."""
        if delay_ms is None:
            delay_ms = random.randint(4000, 6500)

        if self._shenanigan_timer:
            try:
                self.after_cancel(self._shenanigan_timer)
            except Exception:
                pass
        self._shenanigan_timer = self.after(delay_ms, self._perform_random_shenanigan)

    def _perform_random_shenanigan(self) -> None:
        """Trigger one of the comedic Minion sketches."""
        if self.is_busy:
            self._schedule_next_shenanigan(2500)
            return

        actions = [
            self._trick_slap_fight,
            self._trick_banana_taunt,
            self._trick_bob_wave,
        ]
        chosen = random.choice(actions)
        chosen()

    # --------------------------------------------------------------------------
    # Sketch 1: Snappy Slap Fight (With Poked Reaction & Full Comic Timing!)
    # --------------------------------------------------------------------------
    def _trick_slap_fight(self) -> None:
        """Stuart pokes Kevin -> Kevin gets poked (shock!) -> Kevin swats Stuart -> POW! -> Stuart dizzy -> Bob laughs!"""
        self.is_busy = True

        # Frame 1 (0ms): Stuart leans in and pokes Kevin! Comic *POKE!* appears
        self.lbl_stuart.configure(image=self.sp_s_poke)
        self.lbl_fx.configure(image=self.sp_poke)
        self.lbl_fx.place(x=78, y=55)

        # Frame 2 (160ms): Kevin GETS POKED! Jolt of shock, wide eyes, gasping 'O' mouth!
        def _f2():
            self.lbl_kevin.configure(image=self.sp_k_poked)

        # Frame 3 (620ms): POKE clears, Kevin gets annoyed and swats back! Comic POW!
        def _f3():
            self.lbl_fx.place_forget()
            self.lbl_kevin.configure(image=self.sp_k_slap)
            self.lbl_fx.configure(image=self.sp_pow)
            self.lbl_fx.place(x=96, y=28)

        # Frame 4 (920ms): POW clears, Kevin smug idle, Stuart spins dizzy, Bob laughs!
        def _f4():
            self.lbl_fx.place_forget()
            self.lbl_kevin.configure(image=self.sp_k_idle)
            self.lbl_stuart.configure(image=self.sp_s_dizzy)
            self.lbl_bob.configure(image=self.sp_b_talk)

        # Frame 5 (1900ms): Stuart shakes off dizziness, Bob holds banana, all settle cleanly
        def _f5():
            self.lbl_stuart.configure(image=self.sp_s_idle)
            self.lbl_bob.configure(image=self.sp_b_banana)
            self.is_busy = False
            self._schedule_next_shenanigan()

        self.after(160, _f2)
        self.after(620, _f3)
        self.after(920, _f4)
        self.after(1900, _f5)

    # --------------------------------------------------------------------------
    # Sketch 2: Banana Taunt
    # --------------------------------------------------------------------------
    def _trick_banana_taunt(self) -> None:
        """Bob shows his banana, Stuart reaches for it, Bob giggles and pulls it back!"""
        self.is_busy = True

        # Bob raises banana
        self.lbl_bob.configure(image=self.sp_b_banana)

        # Stuart turns and reaches
        def _f2():
            self.lbl_stuart.configure(image=self.sp_s_poke)

        # Bob winks and pulls it away
        def _f3():
            self.lbl_bob.configure(image=self.sp_b_talk)

        # Reset cleanly
        def _f4():
            self.lbl_stuart.configure(image=self.sp_s_idle)
            self.lbl_bob.configure(image=self.sp_b_banana)
            self.is_busy = False
            self._schedule_next_shenanigan()

        self.after(280, _f2)
        self.after(650, _f3)
        self.after(1350, _f4)

    # --------------------------------------------------------------------------
    # Sketch 3: Bob's Cheerful Wave
    # --------------------------------------------------------------------------
    def _trick_bob_wave(self) -> None:
        """Bob winks cheerfully, Kevin smiles approvingly."""
        self.is_busy = True

        self.lbl_bob.configure(image=self.sp_b_talk)
        self.lbl_kevin.configure(image=self.sp_k_talk)

        def _reset():
            self.lbl_bob.configure(image=self.sp_b_banana)
            self.lbl_kevin.configure(image=self.sp_k_idle)
            self.is_busy = False
            self._schedule_next_shenanigan()

        self.after(1100, _reset)

    # ==========================================================================
    # HELPER RESOLVERS
    # ==========================================================================
    def _get_label(self, name: str) -> ctk.CTkLabel:
        if name == "Kevin":
            return self.lbl_kevin
        elif name == "Bob":
            return self.lbl_bob
        return self.lbl_stuart

    def _get_sprite(self, name: str, state: str) -> ctk.CTkImage:
        if name == "Kevin":
            if state == "talk":
                return self.sp_k_talk
            elif state == "blink":
                return self.sp_k_blink
            elif state == "poked":
                return self.sp_k_poked
            elif state == "slap":
                return self.sp_k_slap
            return self.sp_k_idle
        elif name == "Bob":
            if state == "talk":
                return self.sp_b_talk
            elif state == "blink":
                return self.sp_b_blink
            return self.sp_b_banana
        else:
            if state == "talk":
                return self.sp_s_talk
            elif state == "blink":
                return self.sp_s_blink
            elif state == "dizzy":
                return self.sp_s_dizzy
            elif state == "poke":
                return self.sp_s_poke
            return self.sp_s_idle
