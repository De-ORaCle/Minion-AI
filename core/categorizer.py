"""
Activity Categorization Engine for ProductivityCheck.

This module classifies raw window activities and application names into
productivity categories:
- 'Work / Coding'
- 'Learning / Research'
- 'Communication'
- 'Utilities / System'
- 'Entertainment / Media'
- 'Social Media / Distraction'
- 'Idle / Away'

Architectural Design (Scored Multi-Feature Classification & Domain Authority):
1. User-Defined Custom Rules (Priority 1): Exact user overrides always take absolute precedence.
2. Platform & Domain Signatures: Authoritative platform identifiers (e.g., '- YouTube',
   'github.com', 'stackoverflow.com', 'slack.com') take precedence over ambiguous keywords.
3. Multi-Feature Scored Matching: Instead of an early-exit loop where generic words like
   'chat' (e.g. in 'Proximity Chat' on YouTube) accidentally hijack the classification,
   features are scored with weights and contextual guards:
   - Dedicated application process: +100
   - Platform/domain signature: +60
   - Strong thematic keywords: +25
   - Secondary keywords: +10
   - Negative cross-domain penalties: e.g. -50 to Communication if on a video streaming platform.
4. Local AI (Ollama): For unlisted or novel window titles without strong signatures.
5. Smart Contextual Fallback: Guarantees no activity is ever left 'Uncategorized'.
"""

import re
from typing import Dict, Any, Tuple, Optional, List
from config import CATEGORY_CONFIG

# Platform & Domain Signatures (High Confidence: +60 points)
PLATFORM_SIGNATURES = {
    "Entertainment / Media": [
        r"- youtube\b", r"\byoutube\.com\b", r"\byoutu\.be\b",
        r"- twitch\b", r"\btwitch\.tv\b",
        r"\bnetflix\.com\b", r"- netflix\b",
        r"\bdisneyplus\.com\b", r"\bdisney\+\b",
        r"\bhulu\.com\b", r"\bprimevideo\.com\b", r"\bprime video\b",
        r"\bcrunchyroll\.com\b", r"\bspotify\.com\b", r"- spotify\b",
        r"\bsoundcloud\.com\b", r"\bsteampowered\.com\b",
    ],
    "Work / Coding": [
        r"\bgithub\.com\b", r"\bgitlab\.com\b", r"\bbitbucket\.org\b",
        r"\blocalhost\b", r"127\.0\.0\.1", r":\d{4,5}\b",
        r"\bjira\..*\b", r"\btrello\.com\b", r"\blinear\.app\b",
        r"\bfigma\.com\b", r"\bnotion\.so\b", r"\basana\.com\b",
        r"\badmin\b", r"\bcms\b", r"\bdashboard\b", r"\binternal system\b",
    ],
    "Learning / Research": [
        r"\bstackoverflow\.com\b", r"\bstackexchange\.com\b",
        r"\bdocs\.python\.org\b", r"\bdeveloper\.mozilla\.org\b",
        r"\bw3schools\.com\b", r"\barxiv\.org\b", r"\bwikipedia\.org\b",
        r"\bcoursera\.org\b", r"\budemy\.com\b", r"\bedx\.org\b",
        r"\bleetcode\.com\b", r"\bgeeksforgeeks\.org\b",
        r"\bgoogle\.com/search\b", r"\bduckduckgo\.com\b",
    ],
    "Communication": [
        r"\bteams\.microsoft\.com\b", r"\bapp\.slack\.com\b",
        r"\bdiscord\.com/channels\b", r"\bweb\.whatsapp\.com\b",
        r"\bweb\.telegram\.org\b", r"\bmail\.google\.com\b",
        r"\boutlook\.live\.com\b", r"\boutlook\.office\.com\b",
        r"\bzoom\.us/j/\b", r"\bmeet\.google\.com\b",
    ],
    "Social Media / Distraction": [
        r"\btwitter\.com\b", r"\bx\.com\b", r"\breddit\.com\b",
        r"\binstagram\.com\b", r"\btiktok\.com\b", r"\bthreads\.net\b",
        r"\bpinterest\.com\b", r"\b9gag\.com\b",
    ],
}

# Thematic Keywords (+25 points) and Secondary Keywords (+10 points)
THEMATIC_RULES = {
    "Work / Coding": {
        "apps": [
            r"python.*\.exe", r"pythonw.*\.exe", r"py\.exe", r"node.*\.exe",
            r"cargo.*\.exe", r"rustc.*\.exe", r"java.*\.exe", r"dotnet.*\.exe",
            r"go.*\.exe", r"code.*\.exe", r"cursor.*\.exe", r"pycharm.*\.exe",
            r"idea.*\.exe", r"devenv.*\.exe", r"sublime_text.*\.exe",
            r"notepad\+\+.*\.exe", r"atom.*\.exe", r"windsurf.*\.exe",
            r"zed.*\.exe", r"neovim.*\.exe", r"powershell.*\.exe",
            r"cmd\.exe", r"wt\.exe", r"bash\.exe", r"git.*\.exe",
            r"docker.*\.exe", r"postman.*\.exe", r"dbeaver.*\.exe",
            r"figma.*\.exe", r"winword\.exe", r"excel\.exe", r"powerpnt\.exe",
            r"obsidian\.exe", r"notion\.exe", r"photoshop.*\.exe",
            r"blender.*\.exe", r"unity.*\.exe", r"unreal.*\.exe",
            r"antigravity.*\.exe",
        ],
        "strong_keywords": [
            r"\bvisual studio\b", r"\bpull request\b",
            r"\bcommit\b", r"\brepository\b", r"\bterminal\b", r"\bcompiler\b",
            r"\bdebug\b", r"\bapi\b", r"\bschema\b", r"\bsqlite\b",
            r"\.py\b", r"\.ts\b", r"\.js\b", r"\.html\b", r"\.css\b",
            r"\.cpp\b", r"\.rs\b", r"\.go\b", r"\.json\b", r"\.sql\b",
            r"\.md\b", r"\.docx?\b", r"\.xlsx?\b", r"\.pptx?\b",
        ],
        "minor_keywords": [
            r"\bcode\b", r"\bbuild\b", r"\btest\b", r"\bproject\b",
            r"\bworkspace\b", r"\bdocument\b", r"\bsheet\b",
        ],
    },
    "Learning / Research": {
        "apps": [
            r"acrobat\.exe", r"foxitreader\.exe", r"sumatrapdf\.exe", r"kindle\.exe",
        ],
        "strong_keywords": [
            r"\bdocumentation\b", r"\bdocs\b", r"\bstack\s*overflow\b",
            r"\bstack\s*exchange\b", r"\barxiv\b", r"\bwikipedia\b",
            r"\bcoursera\b", r"\budemy\b", r"\bedx\b", r"\bleetcode\b",
            r"\bw3schools\b", r"\bmdn\b", r"\btutorial\b", r"\breference manual\b",
            r"\bgoogle search\b", r"\bdeep learning\b", r"\bmachine learning\b",
        ],
        "minor_keywords": [
            r"\bguide\b", r"\bhowto\b", r"\bhow to\b", r"\bresearch\b",
            r"\bpaper\b", r"\bstudy\b", r"\blearn\b", r"\barticle\b",
        ],
    },
    "Entertainment / Media": {
        "apps": [
            r"spotify\.exe", r"vlc\.exe", r"netflix\.exe", r"steam\.exe",
            r"epicgames.*\.exe", r"origin\.exe", r"gog_galaxy\.exe",
            r"mpv\.exe", r"wmplayer\.exe", r"riotclientservices\.exe",
        ],
        "strong_keywords": [
            r"\byoutube\b", r"\btwitch\b", r"\bnetflix\b", r"\bspotify\b",
            r"\bgameplay\b", r"\btrailer\b", r"\bamong us\b", r"\bwalkthrough\b",
            r"\bsidemen\b", r"\blet's play\b", r"\blivestream\b", r"\bspeedrun\b",
            r"\bhighlight\b", r"\bofficial video\b", r"\bofficial audio\b",
        ],
        "minor_keywords": [
            r"\bgame\b", r"\bgaming\b", r"\bvideo\b", r"\bwatch\b",
            r"\bmusic\b", r"\bsong\b", r"\bstream\b", r"\bplay\b",
        ],
    },
    "Communication": {
        "apps": [
            r"slack\.exe", r"teams\.exe", r"discord\.exe", r"zoom\.exe",
            r"outlook\.exe", r"thunderbird\.exe", r"telegram\.exe",
            r"whatsapp.*\.exe", r"skype\.exe", r"wechat\.exe", r"signal\.exe",
        ],
        "strong_keywords": [
            r"\bmicrosoft teams\b", r"\bdiscord\b", r"\bzoom meeting\b",
            r"\bgoogle meet\b", r"\bwhatsapp\b", r"\btelegram\b",
            r"\bgmail\b", r"\boutlook\b", r"\bwebmail\b",
            r"\bteam standup\b", r"\bconference call\b", r"\bgroup chat\b",
            r"\bteams chat\b", r"\bslack chat\b", r"\bgoogle chat\b",
        ],
        "minor_keywords": [
            r"\binbox\b", r"\bmessenger\b", r"\bvoice call\b", r"\bvideo call\b",
        ],
    },
    "Social Media / Distraction": {
        "apps": [
            r"tiktok\.exe", r"instagram\.exe", r"twitter\.exe",
        ],
        "strong_keywords": [
            r"\btwitter\b", r"\bx\.com\b", r"\binstagram\b", r"\bfacebook\b",
            r"\breddit\b", r"\btiktok\b", r"\bthreads\.net\b", r"\bpinterest\b",
            r"\b9gag\b", r"\btumblr\b", r"\bsnapchat\b",
        ],
        "minor_keywords": [
            r"\bfeed\b", r"\btweet\b", r"\bpost\b",
        ],
    },
    "Utilities / System": {
        "apps": [
            r"minion.*\.exe", r"explorer\.exe", r"taskmgr\.exe", r"regedit\.exe", r"calc\.exe",
            r"control\.exe", r"systemsettings\.exe", r"snippingtool\.exe",
            r"notepad\.exe", r"cleanmgr\.exe", r"mmc\.exe", r"svchost\.exe",
        ],
        "strong_keywords": [
            r"\bfile explorer\b", r"\btask manager\b", r"\bdevice manager\b",
            r"\bcontrol panel\b", r"\bcalculator\b",
        ],
        "minor_keywords": [
            r"\bsettings\b", r"\bproperties\b", r"\brun\b",
        ],
    },
}

BROWSER_PROCESSES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe",
    "opera.exe", "vivaldi.exe", "safari.exe", "arc.exe",
}


class CategorizationEngine:
    """Classifies window activities using scored features, domain authority, and AI."""

    def __init__(self, db_manager=None, ai_agent=None):
        """
        Initialize the classification engine.
        
        Args:
            db_manager: Optional DatabaseManager to load custom user-configured rules.
            ai_agent: Optional OllamaAgent for semantic offline fallback.
        """
        self.db_manager = db_manager
        self.ai_agent = ai_agent
        self._cache: Dict[str, Tuple[str, float]] = {}

    def classify(
        self,
        app_name: str,
        window_title: str,
        is_idle: bool = False,
    ) -> Tuple[str, float]:
        """
        Determine category and productivity weight for a given window snapshot.
        Guaranteed to NEVER return 'Uncategorized'.

        Args:
            app_name: Process/executable name.
            window_title: Window title text.
            is_idle: Boolean user inactivity flag.

        Returns:
            Tuple of (category_name: str, productivity_weight: float)
        """
        # If user is idle, immediately assign 'Idle / Away'
        if is_idle:
            weight = CATEGORY_CONFIG["Idle / Away"]["weight"]
            return "Idle / Away", weight

        app_lower = (app_name or "").lower()
        title_lower = (window_title or "").lower()

        # Minion AI Interface: Observing Minion AI itself is a system utility (NOT work, weight 0.0)
        is_minion_window = (
            app_lower in ("minion.exe", "productivitycheck.exe")
            or "minion" in app_lower
            or "productivitycheck" in app_lower
            or any(mt in title_lower for mt in ["minion —", "minion setup", "minion workshop", "minion ai focus", "minion productivity"])
            or (("minion" in title_lower or "productivitycheck" in title_lower) and not any(ed in app_lower for ed in ["code", "cursor", "pycharm", "idea", "sublime", "notepad++", "devenv", "atom", "vim", "antigravity", "rider", "webstorm"]))
        )
        if is_minion_window:
            weight = CATEGORY_CONFIG["Utilities / System"]["weight"]
            return "Utilities / System", weight

        cache_key = f"{app_lower}:::{title_lower}"
        if cache_key in self._cache:
            cached_cat, cached_weight = self._cache[cache_key]
            if cached_cat in CATEGORY_CONFIG and cached_cat != "Uncategorized":
                return cached_cat, cached_weight

        # 1. Check User-Defined Custom Rules (Highest Priority: User is always right)
        if self.db_manager:
            try:
                user_rules = self.db_manager.get_custom_rules()
                for rule in user_rules:
                    ptype = rule["pattern_type"]
                    pattern = rule["pattern"].lower()
                    target = app_name.lower() if ptype == "app" else window_title.lower()

                    if pattern in target:
                        cat = rule["category"]
                        if cat in CATEGORY_CONFIG and cat != "Uncategorized":
                            weight = CATEGORY_CONFIG[cat]["weight"]
                            self._cache[cache_key] = (cat, weight)
                            return cat, weight
            except Exception:
                pass

        # 2. Multi-Feature Scored Matching with Platform Authority
        app_clean = app_name.lower()
        title_clean = (window_title or "").lower()

        scores: Dict[str, int] = {cat: 0 for cat in CATEGORY_CONFIG if cat != "Idle / Away"}

        # Feature A: Dedicated Application Executable (+100 points)
        for cat, data in THEMATIC_RULES.items():
            for app_pat in data.get("apps", []):
                if re.search(app_pat, app_clean, re.IGNORECASE):
                    scores[cat] += 100
                    break

        # Feature B: High-Confidence Platform & Domain Signatures (+60 points)
        is_media_platform = False
        for cat, sigs in PLATFORM_SIGNATURES.items():
            for sig in sigs:
                if re.search(sig, title_clean, re.IGNORECASE):
                    scores[cat] += 60
                    if cat == "Entertainment / Media":
                        is_media_platform = True
                    break

        # Feature C: Thematic Keywords (+25 strong, +10 minor)
        for cat, data in THEMATIC_RULES.items():
            for kw in data.get("strong_keywords", []):
                if re.search(kw, title_clean, re.IGNORECASE):
                    scores[cat] += 25
                    break
            for kw in data.get("minor_keywords", []):
                if re.search(kw, title_clean, re.IGNORECASE):
                    scores[cat] += 10
                    break

        # Feature D: Cross-Domain Guards & Negative Penalties
        # Guard 1: If on a video platform (YouTube, Twitch, Netflix), penalize Communication
        # so video titles with words like "chat" or "call" are not hijacked!
        if is_media_platform:
            scores["Communication"] = max(0, scores["Communication"] - 80)
            # Exception: Educational YouTube videos (e.g. "Python Tutorial - YouTube")
            if any(term in title_clean for term in ["tutorial", "course", "lecture", "how to code", "documentation"]):
                scores["Learning / Research"] += 45

        # Find best scored category
        best_cat = max(scores, key=lambda c: scores[c])
        highest_score = scores[best_cat]

        if highest_score >= 20:
            weight = CATEGORY_CONFIG[best_cat]["weight"]
            self._cache[cache_key] = (best_cat, weight)
            return best_cat, weight

        # 3. AI Semantic Classification Fallback (if Ollama Agent is available)
        if self.ai_agent and self.ai_agent.is_available():
            try:
                ai_cat = self.ai_agent.classify_activity(app_name, window_title)
                if ai_cat in CATEGORY_CONFIG and ai_cat != "Uncategorized":
                    weight = CATEGORY_CONFIG[ai_cat]["weight"]
                    self._cache[cache_key] = (ai_cat, weight)
                    return ai_cat, weight
            except Exception:
                pass

        # 4. Smart Contextual Fallback
        resolved_cat = self._infer_smart_category(app_clean, title_clean)
        resolved_weight = CATEGORY_CONFIG[resolved_cat]["weight"]
        self._cache[cache_key] = (resolved_cat, resolved_weight)
        return resolved_cat, resolved_weight

    def _infer_smart_category(self, app_lower: str, title_lower: str) -> str:
        """
        Deep contextual inference when an application or title is completely novel.
        Guarantees zero Uncategorized.
        """
        # If running inside a web browser
        if app_lower in BROWSER_PROCESSES:
            if any(term in title_lower for term in ["search", "google", "bing", "docs", "wiki", "read", "article"]):
                return "Learning / Research"
            return "Learning / Research"

        # Check for system/background processes
        system_terms = ["system", "svchost", "dwm", "explorer", "shellexperience", "runtimebroker", "services"]
        if any(term in app_lower for term in system_terms) or not title_lower or title_lower == "desktop":
            return "Utilities / System"

        # Any other user foreground application with active window title
        return "Work / Coding"

    def clear_cache(self) -> None:
        """Clear classification cache (useful when user updates custom rules)."""
        self._cache.clear()
