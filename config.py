"""
Configuration Module for Minion — On-Screen Productivity Intelligence.

This module centralizes system configurations, default polling intervals,
the Minion theme palette (Banana Yellow, Denim Blue, Goggle Slate),
productivity weights, and privacy exclusion rules.
"""

from pathlib import Path

# Branding & Identity
APP_NAME = "Minion"
APP_TAGLINE = "Your Loyal Focus Companion"
APP_SUBTITLE = "v1.0 • Bello! Focus Crew"

import sys
from pathlib import Path

# Base Paths: Support both live Python source and fused standalone executable (PyInstaller)
if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    BASE_DIR = Path(sys.executable).parent
    ASSETS_DIR = BUNDLE_DIR / "assets"
    DATA_DIR = BASE_DIR / "data"
else:
    BASE_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = BASE_DIR
    ASSETS_DIR = BASE_DIR / "assets"
    DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(exist_ok=True, parents=True)
ASSETS_DIR.mkdir(exist_ok=True, parents=True)
ICON_PNG_PATH = ASSETS_DIR / "icon.png"
ICON_ICO_PATH = ASSETS_DIR / "icon.ico"

# Database Configuration: Embedded SQLite file using WAL (Write-Ahead Logging)
DB_PATH = str(DATA_DIR / "minion_productivity.db")

# Polling Intervals (in seconds)
DEFAULT_POLL_INTERVAL = 5
SUPPORTED_INTERVALS = [3, 5, 10, 15, 30, 60]

# Idle Detection Threshold (in seconds)
DEFAULT_IDLE_THRESHOLD_SECONDS = 120

# AI Configuration (Ollama Local Integration)
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"

# Minion Design System Theme Tokens (100% Light Mode, WCAG AAA / AA Compliant)
THEME = {
    # Brand Minion Colors
    "yellow": "#facc15",                    # Vibrant Minion Banana Yellow
    "yellow_hover": "#eab308",              # Deep Banana Amber
    "yellow_text": "#713f12",               # Dark amber text on yellow (7.5:1 WCAG AAA)
    "yellow_tint": "#fef9c3",               # Soft yellow background container
    "yellow_border": "#fde047",             # Yellow accent border
    "yellow_title": "#b45309",              # Warm Amber 700 (4.8:1 contrast on white)
    
    # Denim Accent Colors
    "denim_blue": "#2563eb",                # Minion Overalls Denim Blue
    "blue": "#2563eb",                      # Denim blue alias
    "denim_hover": "#1d4ed8",               # Dark Denim
    "blue_hover": "#1d4ed8",                # Denim hover alias
    "denim_text": "#ffffff",                # White text on denim
    "denim_tint": "#eff6ff",                # Soft sky denim tint
    "denim_border": "#bfdbfe",              # Soft denim edge
    "accent_green": "#059669",              # Emerald green accent

    # Surfaces & Canvas (Zero dark elements)
    "bg": "#f8fafc",                        # Clean, airy slate-50 canvas
    "bg_primary": "#f8fafc",                # Canvas alias
    "surface": "#ffffff",                   # Surface canvas alias
    "surface_subtle": "#f8fafc",            # Subtle recessed surface alias
    "surface_hover": "#f1f5f9",             # Surface hover alias
    "sidebar_bg": "#ffffff",                # Crisp white sidebar
    "sidebar_border": "#e2e8f0",            # Sidebar vertical divider
    "card_bg": "#ffffff",                   # Crisp white card surface
    "card_inner": "#f8fafc",                # Clean subtle recessed inner container
    "card_hover": "#f1f5f9",                # Gentle hover feedback
    "border": "#e2e8f0",                    # Subtle, refined edge border
    "border_focus": "#94a3b8",              # Focus ring border
    "border_subtle": "#f1f5f9",             # Very light container border

    # Input Fields & Controls
    "input_bg": "#ffffff",                  # Pure white input background
    "input_border": "#cbd5e1",              # High contrast input border
    "input_border_focus": "#2563eb",        # Denim blue focus outline

    # High-Contrast Typography (WCAG AAA & AA Compliant)
    "text_primary": "#0f172a",              # Crisp Slate-900 (15.8:1 contrast on white)
    "text_secondary": "#475569",            # Slate-600 (6.2:1 contrast on white, pristine legibility)
    "text_tertiary": "#64748b",             # Slate-500 (4.6:1 contrast on white)
    "text_muted": "#64748b",                # Balanced helper text

    # Semantic Status Badges
    "badge_success_bg": "#ecfdf5",
    "badge_success_text": "#047857",
    "badge_info_bg": "#f0f9ff",
    "badge_info_text": "#0369a1",
    "badge_warning_bg": "#fffbeb",
    "badge_warning_text": "#b45309",
    "badge_danger_bg": "#fef2f2",
    "badge_danger_text": "#b91c1c",
}

# Typography System: Auto-register and load Work Sans with graceful fallback to Segoe UI
import sys
import ctypes
import customtkinter as ctk

FONT_FAMILY = "Segoe UI"
FONTS_DIR = ASSETS_DIR / "fonts"

def _register_application_fonts() -> str:
    """Register custom TTF fonts (Work Sans) into Windows GDI session without admin rights."""
    global FONT_FAMILY
    chosen_family = "Segoe UI"
    if sys.platform == "win32" and FONTS_DIR.exists():
        try:
            FR_PRIVATE = 0x10
            for ttf in FONTS_DIR.glob("*.ttf"):
                ctypes.windll.gdi32.AddFontResourceExW(str(ttf.resolve()), FR_PRIVATE, 0)
            chosen_family = "Work Sans"
        except Exception:
            chosen_family = "Segoe UI"
    return chosen_family

FONT_FAMILY = _register_application_fonts()

_FONT_CACHE: dict = {}

def get_font(*args, **kwargs) -> ctk.CTkFont:
    """Helper factory to instantiate unified design system fonts with caching."""
    size = kwargs.get("size", 13)
    weight = kwargs.get("weight", "normal")
    family = kwargs.get("family", FONT_FAMILY)
    if args:
        if len(args) == 1:
            if isinstance(args[0], int):
                size = args[0]
            elif isinstance(args[0], str) and args[0].isdigit():
                size = int(args[0])
        elif len(args) == 2:
            if isinstance(args[0], int):
                size = args[0]
                weight = args[1]
            else:
                size = args[1] if isinstance(args[1], int) else 13
        elif len(args) >= 3:
            size = args[1] if isinstance(args[1], int) else 13
            weight = args[2] if isinstance(args[2], str) else "normal"

    fam = family or FONT_FAMILY
    key = (fam, size, weight)
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached

    font_obj = ctk.CTkFont(family=fam, size=size, weight=weight)
    _FONT_CACHE[key] = font_obj
    return font_obj


# Multi-Disciplinary Work Profiles & Focus Domains
FOCUS_DOMAINS = {
    "general": {
        "key": "general",
        "title": "General Knowledge Work & Business",
        "icon": "💼",
        "work_label": "Deep Work & Deliverables",
        "tagline": "Cross-functional productivity across spreadsheets, presentations, documents, and planning.",
        "hashtags": ["#Productivity", "#DeepWork", "#Focus", "#Execution", "#ContinuousImprovement"],
    },
    "writing": {
        "key": "writing",
        "title": "Writing, Editorial & Content",
        "icon": "✍️",
        "work_label": "Writing, Manuscripts & Drafting",
        "tagline": "Long-form drafting, publishing, research synthesis, articles, and book authoring.",
        "hashtags": ["#Writing", "#Authors", "#ContentCreation", "#DeepWork", "#Publishing"],
    },
    "design": {
        "key": "design",
        "title": "Design, UI/UX & Creative Media",
        "icon": "🎨",
        "work_label": "Visual Design & Creative Production",
        "tagline": "UI/UX, art direction, 3D modeling, illustration, and digital media production.",
        "hashtags": ["#Design", "#UIUX", "#CreativeProcess", "#DigitalArt", "#DeepWork"],
    },
    "business": {
        "key": "business",
        "title": "Finance, Operations & Strategy",
        "icon": "📊",
        "work_label": "Financial Modeling & Strategy",
        "tagline": "Spreadsheet modeling, financial analysis, executive decks, and operational management.",
        "hashtags": ["#Finance", "#Strategy", "#BusinessOperations", "#Leadership", "#Productivity"],
    },
    "research": {
        "key": "research",
        "title": "Research, Academia & Higher Education",
        "icon": "🔬",
        "work_label": "Scholarly Research & Study",
        "tagline": "Literature review, paper synthesis, scientific analysis, and structured academic study.",
        "hashtags": ["#AcademicChatter", "#Research", "#HigherEd", "#Science", "#DeepWork"],
    },
    "software": {
        "key": "software",
        "title": "Software Engineering & Tech",
        "icon": "💻",
        "work_label": "Software & System Architecture",
        "tagline": "Codebases, system debugging, software architecture, and technical execution.",
        "hashtags": ["#SoftwareEngineering", "#DevLife", "#BuildInPublic", "#DeepWork", "#Tech"],
    },
}

for _d in FOCUS_DOMAINS.values():
    _d["description"] = _d["tagline"]

DEFAULT_FOCUS_DOMAIN = "general"

# Productivity Categories, Weights, and Minion-Harmonized Chart Colors
CATEGORY_CONFIG = {
    "Work / Coding": {
        "weight": 1.0,
        "color": "#f59e0b",       # Amber Gold (High contrast on white)
        "display_name": "Deep Work / Primary Focus",
        "description": "Primary deliverables: documents, financial modeling, design, writing, research, and software",
    },
    "Learning / Research": {
        "weight": 0.8,
        "color": "#0284c7",       # Ocean Sky Blue
        "display_name": "Learning & Research",
        "description": "Documentation, research papers, courses, educational reading, market research",
    },
    "Communication": {
        "weight": 0.5,
        "color": "#6366f1",       # Indigo Pop
        "description": "Slack, Microsoft Teams, emails, video meetings, collaboration",
    },
    "Utilities / System": {
        "weight": 0.0,
        "color": "#64748b",       # Goggle Slate
        "description": "File explorer, terminal utilities, settings, calculators, OS tools",
    },
    "Entertainment / Media": {
        "weight": -0.5,
        "color": "#ea580c",       # Papoy Orange
        "description": "Streaming video, music players, casual gaming, movie portals",
    },
    "Social Media / Distraction": {
        "weight": -1.0,
        "color": "#e11d48",       # Crimson Warning
        "description": "Social networking feeds, short-form video, non-work discussions",
    },
    "Idle / Away": {
        "weight": 0.0,
        "color": "#94a3b8",       # Inactive Goggle Slate
        "description": "User inactive, screen locked, or step away from workstation",
    },
}

# Privacy & Security: Substrings to mask or ignore entirely
DEFAULT_PRIVACY_EXCLUSIONS = [
    "bitwarden",
    "1password",
    "keepass",
    "lastpass",
    "authenticator",
    "private browsing",
    "incognito",
    "banking",
    "credit card",
]

