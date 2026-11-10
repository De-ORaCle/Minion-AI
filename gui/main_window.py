"""
Main Application Window & UI Orchestrator for ProductivityCheck.

This module houses the root CustomTkinter application window, sleek navigation sidebar,
and dynamic view switching between:
1. Tracker / Live Activity Stream
2. Reports & Visual Analytics (Charts & KPIs)
3. Work Segments & Context Timeline
4. Shareable Post Generator
5. AI Agent & Settings Configuration

Architectural Rationale:
- Single-Window Ergonomics: Tab/view navigation prevents window clutter while keeping
  all tools instantly accessible with smooth transitions.
- Asynchronous Thread Safety: Background monitor callbacks post events safely
  to Tkinter's event loop using `root.after()`.
- Clean Shutdown: Traps WM_DELETE_WINDOW to safely terminate background threads
  and close SQLite connections without data corruption.
"""

import sys
import logging
import ctypes
import threading
from typing import Optional
import customtkinter as ctk

from config import ICON_ICO_PATH, ICON_PNG_PATH, THEME, DEFAULT_POLL_INTERVAL, get_font
from core.database import DatabaseManager
from core.monitor import ScreenMonitor
from core.single_instance import SingleInstanceManager
from gui.tray_manager import TrayManager
from core.categorizer import CategorizationEngine
from core.segmenter import ContextSegmenter
from core.reporter import ProductivityReporter
from core.ai_agent import OllamaAgent
from core.share_generator import SharePostGenerator
from core.context_manager import ContextManager
from core.pc_info import detect_and_save_pc_context
from core.sprint_engine import SprintEngine

from gui.views.chat_view import ChatView

logger = logging.getLogger(__name__)

# Configure CustomTkinter design aesthetics (Light Mode preferred default)
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    """Primary application window and navigation controller."""

    def __init__(self, single_instance: Optional[SingleInstanceManager] = None, is_minimized: bool = False):
        super().__init__()

        self.single_instance = single_instance
        self.is_minimized_start = is_minimized
        self.tray_manager: Optional[TrayManager] = None

        # Window Branding & Dimensions
        self.title("Minion — Your Personal Focus Companion")
        self.geometry("1180x760")
        self.minsize(980, 640)

        # Explicit Windows AppUserModelID (Prevents taskbar grouping under generic python.exe)
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Minion.ProductivityIntelligence.App.1.0")
        except Exception as e:
            logger.debug("Could not set AppUserModelID: %s", e)

        # Per-Monitor High-DPI Awareness for crisp rendering across multi-monitors and laptop scaling
        if sys.platform == "win32":
            try:
                ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except Exception:
                    try:
                        ctypes.windll.user32.SetProcessDPIAware()
                    except Exception:
                        pass

        # Apply Window & Taskbar Icon
        self._apply_window_icon()

        # Initialize Core Engines
        self.db = DatabaseManager()

        # Enforce 100% Light Mode Design System across all views
        ctk.set_appearance_mode("Light")
        self.db.set_setting("appearance_mode", "Light")

        self.ai = OllamaAgent()
        self.categorizer = CategorizationEngine(db_manager=self.db, ai_agent=self.ai)
        self.segmenter = ContextSegmenter(ai_agent=self.ai)
        self.reporter = ProductivityReporter(self.db)
        self.share_gen = SharePostGenerator(self.db, self.segmenter, self.ai)
        self.context_manager = ContextManager(self.db)
        self.sprint_engine = SprintEngine(self.db, ai_agent=self.ai, context_manager=self.context_manager)

        # Detect and store PC hardware specs asynchronously in background without delaying startup
        threading.Thread(target=lambda: detect_and_save_pc_context(self.db), daemon=True).start()

        # Background Screen Monitor
        self.monitor = ScreenMonitor(
            on_activity_callback=self._on_monitor_snapshot,
        )

        # Layout Structure: Left Sidebar + Right Main Content Area
        self.grid_columnconfigure(0, weight=0)  # Fixed sidebar
        self.grid_columnconfigure(1, weight=1)  # Expandable content
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_views()
        self._build_floating_toggle()

        # Set default active tab (Minion Lounge)
        self._select_view("chat")

        # Persistent tracking state check ("Except it is paused/stopped before the app is closed")
        # Honors whether user left Minion tracking active or paused in prior session
        tracking_enabled = self.db.get_setting("tracking_enabled", default="true").lower() == "true"
        if tracking_enabled:
            self._toggle_tracking(True)
        else:
            self._toggle_tracking(False)

        # Initialize System Tray Manager for ambient background intelligence
        try:
            self.tray_manager = TrayManager(
                on_show=lambda: self.after(0, self.show_window),
                on_toggle_tracking=lambda state: self.after(0, lambda: self._toggle_tracking(state)),
                on_quit=lambda: self.after(0, self.quit_completely),
                initial_tracking_active=tracking_enabled,
            )
            self.tray_manager.start()
        except Exception as tray_err:
            logger.warning(f"Could not initialize System Tray: {tray_err}")

        # Auto-start local Ollama AI engine on launch (configurable in Preferences)
        auto_start_ollama = self.db.get_setting("auto_start_ollama", default="true").lower() == "true"
        if auto_start_ollama:
            threading.Thread(target=self._auto_start_ollama, daemon=True).start()

        # Check for first-run setup & onboarding wizard
        onboarding_done = self.db.get_setting("onboarding_completed", default="false").lower() == "true"
        if not onboarding_done:
            self.after(350, self.open_onboarding_wizard)

        # Trap close event for close-to-tray background daemon behavior
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # If launched via Windows autostart on reboot (--minimized), withdraw window immediately into tray
        if self.is_minimized_start:
            self.withdraw()

    def open_onboarding_wizard(self) -> None:
        """Display the interactive first-run setup wizard dialog."""
        try:
            from gui.views.onboarding_wizard import OnboardingWizard
            OnboardingWizard(
                self,
                self.db,
                self.ai,
                on_complete_callback=self._on_onboarding_completed,
            )
        except Exception as e:
            logger.error("Error launching onboarding wizard: %s", e)

    def _on_onboarding_completed(self) -> None:
        """Refresh views and profiles once user completes onboarding."""
        try:
            if hasattr(self, "view_context") and self.view_context:
                if hasattr(self.view_context, "_load_existing_profile"):
                    self.view_context._load_existing_profile()
            if hasattr(self, "view_settings") and self.view_settings:
                if hasattr(self.view_settings, "check_ai_status"):
                    self.view_settings.check_ai_status()
        except Exception as e:
            logger.debug("Post-onboarding refresh error: %s", e)

    def _auto_start_ollama(self) -> None:
        """Silently verify or launch local Ollama background service on app launch."""
        try:
            if not self.ai.is_service_running():
                logger.info("🍌 Auto-starting Ollama background service on launch...")
                started = self.ai.start_service(timeout=8.0)
                if started:
                    logger.info("Ollama background service successfully started.")
                    if hasattr(self, "view_settings") and self.view_settings:
                        self.after(500, self.view_settings.check_ai_status)
        except Exception as e:
            logger.debug(f"Auto-start Ollama exception: {e}")

    def _apply_window_icon(self) -> None:
        """Apply high-definition Minion mascot icon to window titlebar, taskbar, and dock."""
        # 1. Tkinter iconphoto with master 512x512 PNG
        if ICON_PNG_PATH.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(ICON_PNG_PATH)
                self._icon_photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._icon_photo)
            except Exception as e:
                logger.debug("Could not apply iconphoto: %s", e)

        # 2. Native Win32 window iconbitmap
        if ICON_ICO_PATH.exists():
            try:
                self.iconbitmap(str(ICON_ICO_PATH))
            except Exception as e:
                logger.debug("Could not apply iconbitmap: %s", e)

        # 3. Direct Win32 WM_SETICON injection to ensure dock/taskbar never grabs 16x16
        self.after(150, self._set_win32_highres_icon)

    def _set_win32_highres_icon(self) -> None:
        """Directly inject high-resolution HICON (256x256) into Win32 top-level window handle."""
        if not ICON_ICO_PATH.exists() or sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            user32.LoadImageW.restype = wintypes.HANDLE

            # Find top-level root window handle (GA_ROOT = 2)
            hwnd = user32.GetAncestor(self.winfo_id(), 2) or self.winfo_id()
            LR_LOADFROMFILE = 0x00000010
            IMAGE_ICON = 1
            WM_SETICON = 0x0080
            ICON_BIG = 1
            ICON_SMALL = 0

            # Load 256x256 / default high-res icon from descending multi-res ICO
            hicon_big = user32.LoadImageW(None, str(ICON_ICO_PATH), IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
            hicon_small = user32.LoadImageW(None, str(ICON_ICO_PATH), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)

            if hicon_big:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
            if hicon_small:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
        except Exception as e:
            logger.debug("Win32 highres icon injection error: %s", e)

    def _build_sidebar(self) -> None:
        """Construct the modern navigation sidebar."""
        self.sidebar_frame = ctk.CTkFrame(
            self,
            width=230,
            corner_radius=0,
            fg_color=THEME["sidebar_bg"],
            border_width=1,
            border_color=THEME["sidebar_border"],
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        # App Brand Header
        brand_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_frame.pack(fill="x", padx=18, pady=(22, 20))

        brand_row = ctk.CTkFrame(brand_frame, fg_color="transparent")
        brand_row.pack(anchor="w")

        if ICON_PNG_PATH.exists():
            try:
                from PIL import Image
                icon_img = Image.open(ICON_PNG_PATH)
                self._sidebar_icon = ctk.CTkImage(light_image=icon_img, dark_image=icon_img, size=(28, 28))
                lbl_icon = ctk.CTkLabel(brand_row, image=self._sidebar_icon, text="")
                lbl_icon.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        lbl_logo = ctk.CTkLabel(
            brand_row,
            text="Minion",
            font=get_font(size=20, weight="bold"),
            text_color=THEME["yellow_title"],
        )
        lbl_logo.pack(side="left")

        lbl_version = ctk.CTkLabel(
            brand_frame,
            text="v1.0 • Your Loyal Focus Crew",
            font=get_font(size=11),
            text_color=THEME["text_secondary"],
        )
        lbl_version.pack(anchor="w", pady=(2, 0))

        # Navigation Buttons Container
        self.nav_buttons = {}
        nav_items = [
            ("chat", "🍌 Minion Lounge"),
            ("insights", "💡 Work Insights"),
            ("context", "🧠 Work Memory"),
            ("tracker", "⏱️ Activity Watcher"),
            ("reports", "📊 Focus Analytics"),
            ("segments", "⚡ Work Sprints"),
            ("share", "📣 Standup & Share"),
            ("settings", "⚙️ Preferences & Lab"),
        ]

        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=label,
                command=lambda k=key: self._select_view(k),
                fg_color="transparent",
                hover_color=THEME["card_hover"],
                text_color=THEME["text_secondary"],
                anchor="w",
                font=get_font(size=13, weight="bold"),
                height=42,
                corner_radius=8,
                cursor="hand2",
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = btn

        # Spacer to push monitor status card to sidebar bottom
        spacer = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Bottom System Card in Sidebar
        bottom_card = ctk.CTkFrame(
            self.sidebar_frame,
            fg_color=THEME["card_inner"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["border"],
        )
        bottom_card.pack(fill="x", padx=12, pady=16)

        lbl_sys = ctk.CTkLabel(
            bottom_card,
            text="Minion Patrol",
            font=get_font(size=11, weight="bold"),
            text_color=THEME["text_secondary"],
        )
        lbl_sys.pack(anchor="w", padx=12, pady=(10, 2))

        self.lbl_sidebar_status = ctk.CTkLabel(
            bottom_card,
            text="● Minions Ready",
            font=get_font(size=12, weight="bold"),
            text_color=THEME["badge_warning_text"],
        )
        self.lbl_sidebar_status.pack(anchor="w", padx=12, pady=(0, 8))

        self.btn_sidebar_toggle = ctk.CTkButton(
            bottom_card,
            text="▶ Start Tracking",
            command=self._toggle_from_sidebar,
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            height=30,
            font=get_font(size=12, weight="bold"),
            corner_radius=6,
            cursor="hand2",
        )
        self.btn_sidebar_toggle.pack(fill="x", padx=10, pady=(0, 10))

    def _build_views(self) -> None:
        """Instantiate view container and initialize primary view with lazy loading."""
        self.container = ctk.CTkFrame(self, fg_color=THEME["bg"], corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew")

        # View registry: primary view instantiated immediately; remaining views instantiated on demand
        self.views = {}

        # 1. Primary landing view (Minion Lounge)
        self.view_chat = ChatView(
            self.container,
            db_manager=self.db,
            ai_agent=self.ai,
        )
        self.views["chat"] = self.view_chat

        # 2. View placeholders for lazy initialization
        self.view_insights = None
        self.view_context = None
        self.view_tracker = None
        self.view_reports = None
        self.view_segments = None
        self.view_share = None
        self.view_settings = None

        # 3. Schedule gentle idle warmup for remaining views so tab transitions are instant
        self.after(1000, self._warmup_background_views)

    def _get_or_create_view(self, key: str):
        """Retrieve existing view or instantiate it lazily on demand."""
        if key in self.views and self.views[key] is not None:
            return self.views[key]

        view = None
        if key == "insights":
            from gui.views.insights_view import WorkInsightsView
            self.view_insights = WorkInsightsView(
                self.container,
                db_manager=self.db,
                context_manager=self.context_manager,
            )
            view = self.view_insights
        elif key == "context":
            from gui.views.context_view import ContextView
            self.view_context = ContextView(
                self.container,
                db_manager=self.db,
                context_manager=self.context_manager,
            )
            view = self.view_context
        elif key == "tracker":
            from gui.views.tracker_view import TrackerView
            self.view_tracker = TrackerView(
                self.container,
                on_toggle_tracking=self._toggle_tracking,
                on_change_interval=self._change_interval,
                db_manager=self.db,
            )
            self.view_tracker.is_tracking = self.monitor.is_running()
            view = self.view_tracker
        elif key == "reports":
            from gui.views.reports_view import ReportsView
            self.view_reports = ReportsView(
                self.container,
                db_manager=self.db,
                reporter=self.reporter,
            )
            view = self.view_reports
        elif key == "segments":
            from gui.views.segments_view import SegmentsView
            self.view_segments = SegmentsView(
                self.container,
                db_manager=self.db,
                segmenter=self.segmenter,
                reporter=self.reporter,
                sprint_engine=self.sprint_engine,
            )
            view = self.view_segments
        elif key == "share":
            from gui.views.share_view import ShareView
            self.view_share = ShareView(
                self.container,
                db_manager=self.db,
                share_gen=self.share_gen,
                reporter=self.reporter,
            )
            view = self.view_share
        elif key == "settings":
            from gui.views.settings_view import SettingsView
            self.view_settings = SettingsView(
                self.container,
                db_manager=self.db,
                ai_agent=self.ai,
                on_rules_changed=self._on_rules_updated,
            )
            view = self.view_settings

        if view is not None:
            self.views[key] = view
        return view

    def _warmup_background_views(self) -> None:
        """Pre-warm secondary views in the background sequentially during idle frames."""
        warmup_queue = ["tracker", "insights", "settings", "context", "segments", "reports", "share"]

        def _warm_step():
            if not warmup_queue:
                return
            nxt = warmup_queue.pop(0)
            if nxt not in self.views or self.views[nxt] is None:
                try:
                    self._get_or_create_view(nxt)
                except Exception as e:
                    logger.debug(f"Idle warmup note for {nxt}: {e}")
            if warmup_queue:
                self.after(350, _warm_step)

        self.after(200, _warm_step)

    def _build_floating_toggle(self) -> None:
        """Create a floating circular play/pause icon button at the bottom right to trigger tracking from any page."""
        self.floating_toggle_btn = ctk.CTkButton(
            self.container,
            text="▶",
            command=self._handle_floating_toggle,
            fg_color=THEME["yellow"],
            hover_color=THEME["yellow_hover"],
            text_color=THEME["yellow_text"],
            font=get_font(size=16, weight="bold"),
            height=44,
            width=44,
            corner_radius=22,
            border_width=1,
            border_color=THEME["yellow_border"],
            bg_color="transparent",
            cursor="hand2",
        )
        self.floating_toggle_btn.grid_columnconfigure(0, minsize=0)
        self.floating_toggle_btn.grid_columnconfigure(4, minsize=0)
        self.floating_toggle_btn.place(relx=0.97, rely=0.96, anchor="se")

    def _handle_floating_toggle(self) -> None:
        """Toggle tracking from the floating action button."""
        new_state = not self.monitor.is_running()
        self._toggle_tracking(new_state)

    def _select_view(self, view_key: str) -> None:
        """Switch active view and update sidebar styling."""
        is_new_view = view_key not in self.views or self.views[view_key] is None
        target_view = self._get_or_create_view(view_key)

        for k, btn in self.nav_buttons.items():
            if k == view_key:
                if target_view:
                    target_view.pack(fill="both", expand=True)
                btn.configure(
                    fg_color=THEME["yellow_tint"],
                    text_color=THEME["yellow_text"],
                )
            else:
                v = self.views.get(k)
                if v is not None:
                    v.pack_forget()
                btn.configure(
                    fg_color="transparent",
                    text_color=THEME["text_secondary"],
                )

        # Keep floating toggle button above whatever view is packed
        if hasattr(self, "floating_toggle_btn"):
            self.floating_toggle_btn.lift()

        # Trigger data refreshes on navigation only if the view was already created previously
        if not is_new_view:
            if view_key == "chat":
                if hasattr(self, "view_chat") and self.view_chat:
                    self.view_chat.on_page_visited()
            elif view_key == "insights":
                if hasattr(self, "view_insights") and self.view_insights:
                    self.view_insights.refresh_insights()
            elif view_key == "context":
                if hasattr(self, "view_context") and self.view_context:
                    self.view_context.on_page_visited()
            elif view_key == "reports":
                if hasattr(self, "view_reports") and self.view_reports:
                    self.view_reports.refresh_data()
            elif view_key == "segments":
                if hasattr(self, "view_segments") and self.view_segments:
                    self.view_segments.refresh_data()

    def _toggle_tracking(self, should_track: bool) -> None:
        """Start or stop the background screen monitor, persist state, and synchronize UI & Tray."""
        if should_track:
            self.monitor.start()
        else:
            self.monitor.stop()

        # Persist user intent to database so restarts and close-to-tray honor it
        self.db.set_setting("tracking_enabled", "true" if should_track else "false")
        self.db.set_setting("auto_start_tracking", "true" if should_track else "false")

        self._update_tracking_ui(should_track)
        if hasattr(self, "tray_manager") and self.tray_manager:
            self.tray_manager.update_tracking_state(should_track)

    def _update_tracking_ui(self, is_tracking: bool) -> None:
        """Synchronize all tracking toggles and badges across views."""
        # 1. Sidebar status & button
        if is_tracking:
            self.lbl_sidebar_status.configure(text="● Minion on Duty", text_color=THEME["badge_success_text"])
            self.btn_sidebar_toggle.configure(
                text="⏹ Pause Minion", fg_color=THEME["denim_blue"], hover_color=THEME["denim_hover"], text_color="#ffffff"
            )
        else:
            self.lbl_sidebar_status.configure(text="○ Minion Resting", text_color=THEME["text_secondary"])
            self.btn_sidebar_toggle.configure(
                text="▶ Start Tracking", fg_color=THEME["yellow"], hover_color=THEME["yellow_hover"], text_color=THEME["yellow_text"]
            )

        # 2. Floating action button (circular icon only)
        if hasattr(self, "floating_toggle_btn"):
            if is_tracking:
                self.floating_toggle_btn.configure(
                    text="⏸",
                    fg_color=THEME["denim_blue"],
                    hover_color=THEME["denim_hover"],
                    text_color="#ffffff",
                    border_color=THEME["denim_border"],
                )
            else:
                self.floating_toggle_btn.configure(
                    text="▶",
                    fg_color=THEME["yellow"],
                    hover_color=THEME["yellow_hover"],
                    text_color=THEME["yellow_text"],
                    border_color=THEME["yellow_border"],
                )
            self.floating_toggle_btn.grid_columnconfigure(0, minsize=0)
            self.floating_toggle_btn.grid_columnconfigure(4, minsize=0)
            self.floating_toggle_btn.lift()

        # 3. Live Tracker view button & badge
        if hasattr(self, "view_tracker") and self.view_tracker is not None:
            self.view_tracker.is_tracking = is_tracking
            if is_tracking:
                self.view_tracker.btn_toggle.configure(
                    text="⏹ Pause Minion", fg_color=THEME["denim_blue"], hover_color=THEME["denim_hover"], text_color="#ffffff"
                )
                self.view_tracker.status_badge.configure(
                    text="● MINION ON DUTY", text_color=THEME["badge_success_text"], fg_color=THEME["badge_success_bg"]
                )
            else:
                self.view_tracker.btn_toggle.configure(
                    text="▶ Start Tracking", fg_color=THEME["yellow"], hover_color=THEME["yellow_hover"], text_color=THEME["yellow_text"]
                )
                self.view_tracker.status_badge.configure(
                    text="○ MINION RESTING", text_color=THEME["text_secondary"], fg_color=THEME["card_inner"]
                )

    def _toggle_from_sidebar(self) -> None:
        """Toggle tracking directly from the sidebar."""
        should_track = not self.monitor.is_running()
        self._toggle_tracking(should_track)

    def _change_interval(self, new_interval: int) -> None:
        """Update monitor interval dynamically."""
        self.monitor.set_interval(new_interval)

    def _on_monitor_snapshot(self, snapshot: dict) -> None:
        """
        Invoked on each monitoring tick by the background thread.
        Schedules database write and GUI update on the main Tkinter thread.
        """
        app = snapshot.get("app_name", "Unknown")
        title = snapshot.get("window_title", "Desktop")
        is_idle = snapshot.get("is_idle", False)
        duration = snapshot.get("interval_seconds", DEFAULT_POLL_INTERVAL)
        action_verb = snapshot.get("action_verb", "")
        target_entity = snapshot.get("target_entity", "")
        workflow_phase = snapshot.get("workflow_phase", "")
        transition_type = snapshot.get("transition_type", "")
        is_stuck = snapshot.get("is_stuck", False)

        # Classify activity
        category, weight = self.categorizer.classify(app, title, is_idle=is_idle)

        # Log to SQLite database
        self.db.log_activity(
            app_name=app,
            window_title=title,
            category=category,
            productivity_score=weight,
            duration_seconds=duration,
            is_idle=is_idle,
            action_verb=action_verb,
            target_entity=target_entity,
            workflow_phase=workflow_phase,
            transition_type=transition_type,
            is_stuck=is_stuck,
        )

        # Update GUI safely via root.after
        if hasattr(self, "view_tracker") and self.view_tracker:
            self.after(0, lambda: self.view_tracker.update_live_snapshot(snapshot, category))

    def _on_rules_updated(self) -> None:
        """Callback when user modifies custom categorization rules."""
        self.categorizer.clear_cache()

    def _on_close(self) -> None:
        """Close-to-tray handler: withdraws window so Minion continues running in the background."""
        close_to_tray = self.db.get_setting("close_to_tray", default="true").lower() == "true"
        if close_to_tray:
            self.withdraw()
            # Inform user on first close that Minion continues working quietly in the tray
            has_seen_notice = self.db.get_setting("has_seen_tray_notice", default="false").lower() == "true"
            if not has_seen_notice and hasattr(self, "tray_manager") and self.tray_manager:
                self.tray_manager.notify(
                    title="Minion AI is Still Working",
                    message="Minion is running quietly in your system tray. Double-click or right-click the mascot icon anytime.",
                )
                self.db.set_setting("has_seen_tray_notice", "true")
        else:
            self.quit_completely()

    def show_window(self) -> None:
        """Restore, unminimize, and bring the Minion window to the foreground."""
        try:
            self.deiconify()
            self.state("normal")
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(200, lambda: self.attributes("-topmost", False))
        except Exception as e:
            logger.debug(f"Error restoring window: {e}")

    def quit_completely(self) -> None:
        """Completely shut down Minion AI, monitor threads, system tray icon, and IPC socket."""
        logger.info("🍌 Shutting down Minion AI completely...")
        try:
            if hasattr(self, "monitor") and self.monitor.is_running():
                self.monitor.stop()
        except Exception as e:
            logger.debug(f"Error stopping monitor: {e}")

        try:
            if hasattr(self, "tray_manager") and self.tray_manager:
                self.tray_manager.stop()
        except Exception as e:
            logger.debug(f"Error stopping tray icon: {e}")

        try:
            if hasattr(self, "single_instance") and self.single_instance:
                self.single_instance.close()
        except Exception as e:
            logger.debug(f"Error closing single instance listener: {e}")

        self.destroy()
        sys.exit(0)
