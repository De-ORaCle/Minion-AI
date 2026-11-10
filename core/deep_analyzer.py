"""
Deep Snapshot Analyzer & Context Comparison Engine for Minion.

This module analyzes active screen snapshots and compares consecutive states to:
1. Extract granular semantic entities: active file, language, project repository,
   browser search query, doc subject, and unsaved/dirty editing markers.
2. Detect state transitions: Research -> Implementation -> Verification -> Fix.
3. Detect cognitive friction and troubleshooting loops (rapid oscillation between
   code editor and search engine/documentation without progress).
4. Infer concrete user micro-actions and workflow phases.
"""

import re
import os
from typing import Dict, Any, Optional, List, Tuple


class DeepSnapshotAnalyzer:
    """Analyzes and compares screen snapshots to extract deep context and behaviour."""

    # Universal craft file extensions across all professions
    CODE_EXTENSIONS = {
        # Code & Web
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "React JSX",
        ".tsx": "React TSX",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".json": "JSON",
        ".md": "Markdown",
        ".sql": "SQL",
        ".rs": "Rust",
        ".go": "Go",
        ".cpp": "C++",
        ".c": "C",
        ".cs": "C#",
        ".java": "Java",
        ".kt": "Kotlin",
        ".swift": "Swift",
        ".rb": "Ruby",
        ".php": "PHP",
        ".sh": "Shell Script",
        ".ps1": "PowerShell",
        ".bat": "Batch Script",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".toml": "TOML",
        # Documents & Editorial
        ".docx": "Word Document",
        ".doc": "Word Document",
        ".txt": "Text Draft",
        ".rtf": "Rich Text Document",
        ".epub": "eBook Manuscript",
        # Finance & Business Strategy
        ".xlsx": "Excel Spreadsheet",
        ".xls": "Excel Spreadsheet",
        ".csv": "Data Table (CSV)",
        ".pptx": "PowerPoint Deck",
        ".ppt": "PowerPoint Deck",
        ".pbix": "PowerBI Report",
        # Visual & UX Design
        ".fig": "Figma Canvas",
        ".psd": "Photoshop Asset",
        ".ai": "Illustrator Vector",
        ".blend": "Blender 3D Scene",
        ".indd": "InDesign Document",
        ".xd": "Adobe XD Prototype",
        # Research & Scholarship
        ".pdf": "PDF Literature / Paper",
        ".tex": "LaTeX Manuscript",
        ".bib": "BibTeX Bibliography",
    }

    # Known documentation and developer domains
    DEV_DOMAINS = {
        "github.com": "GitHub",
        "gitlab.com": "GitLab",
        "stackoverflow.com": "Stack Overflow",
        "python.org": "Python Docs",
        "developer.mozilla.org": "MDN Web Docs",
        "docs.microsoft.com": "Microsoft Docs",
        "learn.microsoft.com": "Microsoft Learn",
        "arxiv.org": "arXiv",
        "huggingface.co": "Hugging Face",
        "w3schools.com": "W3Schools",
        "geeksforgeeks.org": "GeeksforGeeks",
        "reddit.com": "Reddit",
        "youtube.com": "YouTube",
        "notion.so": "Notion",
        "linear.app": "Linear",
        "jira": "Jira",
        "figma.com": "Figma",
    }

    def __init__(self, history_buffer_size: int = 15):
        """
        Initialize analyzer.
        
        Args:
            history_buffer_size: Maximum rolling history of snapshots kept for loop detection.
        """
        self.history_buffer_size = history_buffer_size
        self._history: List[Dict[str, Any]] = []

    def parse_snapshot_entities(self, app_name: str, window_title: str) -> Dict[str, Any]:
        """
        Extract detailed entities from window title and executable name.
        
        Returns:
            Dictionary containing:
            - project_name: Inferred workspace or project folder
            - file_name: Specific file being edited or viewed
            - file_language: Programming/markup language of file
            - is_dirty: Whether unsaved/editing markers are present
            - search_query: Extracted search query if browser search
            - web_service: Detected web service/domain
            - workflow_phase: High-level category phase
            - action_verb: Human-readable action description
        """
        clean_title = window_title.strip()
        app_lower = (app_name or "").lower()
        title_lower = clean_title.lower()

        is_dirty = any(marker in clean_title for marker in ["●", "•", " * ", "[modified]"]) or clean_title.startswith("*")
        # Remove dirty marker for cleaner entity extraction
        norm_title = re.sub(r"^[●•\*]\s*", "", clean_title)
        norm_title = re.sub(r"\s*-\s*\[modified\]", "", norm_title, flags=re.IGNORECASE)

        project_name = ""
        file_name = ""
        file_language = ""
        search_query = ""
        web_service = ""
        workflow_phase = "General / Miscellaneous"
        action_verb = f"Using {app_name}"

        # 0. Minion AI Interface: Observing Minion AI is a system utility (NOT work, never implementation)
        is_editor = any(ed in app_lower for ed in ["code", "cursor", "pycharm", "idea", "sublime", "notepad++", "devenv", "atom", "vim", "antigravity", "rider", "webstorm"])
        is_minion_app = (
            app_lower in ("minion.exe", "productivitycheck.exe")
            or "minion.exe" in app_lower
            or "productivitycheck.exe" in app_lower
            or any(mt in title_lower for mt in ["minion —", "minion setup", "minion workshop", "minion ai focus", "minion productivity"])
            or (("minion" in title_lower or "productivitycheck" in title_lower) and not is_editor)
        )
        if is_minion_app:
            return {
                "project_name": "",
                "file_name": "",
                "file_language": "",
                "is_dirty": False,
                "search_query": "",
                "web_service": "",
                "workflow_phase": "Utilities / System",
                "action_verb": "Reviewing Minion AI companion & productivity dashboard",
            }

        # 1. Code Editors (VS Code, Cursor, Antigravity IDE, JetBrains, Sublime, Notepad++, Visual Studio)
        if is_editor:
            workflow_phase = "Coding / Implementation"
            # Patterns for VS Code / Cursor: "file.ext - ProjectName - IDE" or "ProjectName - IDE - file.ext"
            parts = [p.strip() for p in re.split(r" - | – | — ", norm_title) if p.strip()]
            editor_kw = ["visual studio", "code", "cursor", "jetbrains", "antigravity", "ide", "pycharm", "sublime"]
            
            # Check if any part matches a filename with known extension
            file_part_idx = -1
            for i, p in enumerate(parts):
                match = re.search(r"([\w\-\.\/\\\:]+\.[a-zA-Z0-9]+)$", p)
                if match:
                    raw_fn = match.group(1).replace("\\", "/")
                    file_name = raw_fn.split("/")[-1]
                    ext = os.path.splitext(file_name)[1].lower()
                    file_language = self.CODE_EXTENSIONS.get(ext, ext.replace(".", "").upper())
                    file_part_idx = i
                    break

            # Infer project name from remaining non-editor, non-file parts
            for i, p in enumerate(parts):
                if i != file_part_idx:
                    p_lower = p.lower()
                    if not any(ed in p_lower for ed in editor_kw) and len(p) > 1:
                        project_name = p
                        break

            # Fallback project name from known words if still empty
            if not project_name:
                if "minion" in title_lower or "productivitycheck" in title_lower:
                    project_name = "Minion AI"
            
            # If no explicit file found, check for welcome / search / settings
            if not file_name:
                if "welcome" in title_lower:
                    action_verb = "Navigating IDE Welcome Page"
                elif "search" in title_lower:
                    action_verb = "Searching codebase across project"
                else:
                    action_verb = f"Navigating workspace in {app_name}"
            else:
                edit_state = " (Unsaved Edits)" if is_dirty else ""
                proj_context = f" in {project_name}" if project_name else ""
                action_verb = f"Editing {file_name}{proj_context}{edit_state}"

        # 2. Terminals & CLI (PowerShell, Command Prompt, Windows Terminal, Bash)
        elif any(term in app_lower for term in ["powershell", "cmd", "windowsterminal", "wt", "bash", "mintty", "conhost"]):
            workflow_phase = "Verification & CLI"
            if "python" in title_lower or "unittest" in title_lower or "pytest" in title_lower:
                action_verb = "Running Python unit tests & test suite"
            elif "git" in title_lower:
                action_verb = "Executing Git version control commands"
            elif "npm" in title_lower or "yarn" in title_lower or "node" in title_lower:
                action_verb = "Managing Node.js packages & runtime"
            else:
                action_verb = f"Executing terminal commands in {app_name}"

        # 3. Web Browsers (Chrome, Edge, Firefox, Brave, Opera)
        elif any(br in app_lower for br in ["chrome", "msedge", "firefox", "brave", "opera"]):
            # Check for Search Queries
            search_match = re.search(r"^(.*?)\s*-\s*Google Search", norm_title, re.IGNORECASE)
            if not search_match:
                search_match = re.search(r"^(.*?)\s*-\s*Bing", norm_title, re.IGNORECASE)
            if not search_match:
                search_match = re.search(r"^(.*?)\s*-\s*DuckDuckGo", norm_title, re.IGNORECASE)

            # Check for Local Development Testing (localhost, 127.0.0.1, :5176, :3000, etc.)
            local_url_match = re.search(r"(https?://(?:localhost|127\.0\.0\.1)(?::\d{2,5})?(?:/[^\s]*)?)", norm_title, re.IGNORECASE)
            port_match = re.search(r"(?:localhost|127\.0\.0\.1):(\d{2,5})", norm_title, re.IGNORECASE)
            is_local_dev = local_url_match or port_match or "localhost" in title_lower or "127.0.0.1" in title_lower

            if is_local_dev:
                active_port = port_match.group(1) if port_match else "3000"
                local_url = local_url_match.group(1) if local_url_match else f"http://localhost:{active_port}/"
                web_service = "Local Dev Server"
                workflow_phase = "Testing & Verification"
                action_verb = f"Testing web application live at {local_url}"
                # Dynamically extract potential title project
                parts = [p.strip() for p in re.split(r"[-–—|•]", norm_title) if len(p.strip()) > 2]
                if parts and not any(k in parts[0].lower() for k in ["localhost", "127.0.0.1", "google chrome", "microsoft edge"]):
                    project_name = parts[0]

            elif search_match:
                search_query = search_match.group(1).strip()
                web_service = "Search Engine"
                workflow_phase = "Research & Exploration"
                action_verb = f"Researching: '{search_query}'"
            elif "github" in title_lower:
                web_service = "GitHub"
                workflow_phase = "Version Control & Review"
                # Extract repo / PR if available
                action_verb = f"Browsing GitHub: {norm_title.split('·')[0].strip()}"
            elif "stack overflow" in title_lower:
                web_service = "Stack Overflow"
                workflow_phase = "Troubleshooting & Problem Solving"
                action_verb = f"Consulting Stack Overflow: {norm_title.split('-')[0].strip()}"
            elif "youtube" in title_lower:
                web_service = "YouTube"
                workflow_phase = "Media & Distraction"
                # Strip YouTube suffix
                yt_title = re.sub(r"\s*-\s*YouTube.*$", "", norm_title, flags=re.IGNORECASE)
                action_verb = f"Watching YouTube: '{yt_title}'"
            elif any(doc_kw in title_lower for doc_kw in ["doc", "docs", "documentation", "api", "reference", "tutorial", "guide"]):
                web_service = "Documentation"
                workflow_phase = "Learning & Documentation"
                doc_topic = norm_title.split(" - ")[0].strip()
                action_verb = f"Reading Documentation: {doc_topic}"
            else:
                workflow_phase = "Web Browsing"
                site_name = norm_title.split(" - ")[0].strip() if " - " in norm_title else norm_title
                action_verb = f"Browsing web: {site_name[:40]}"

        # 4. Universal Office, Creative, Finance, Research & Communication
        elif any(comm in app_lower for comm in ["slack", "teams", "discord", "outlook", "thunderbird", "whatsapp"]):
            workflow_phase = "Communication & Sync"
            action_verb = f"Communicating on {app_name}"

        # A. Finance & Business Modeling (Excel, PowerBI)
        elif any(fin in app_lower for fin in ["excel", "calc"]) or ".xlsx" in title_lower or ".xls" in title_lower or ".csv" in title_lower:
            workflow_phase = "Financial Modeling & Analysis"
            fn_match = re.search(r"([\w\-\_\s]{2,40}\.(?:xlsx?|csv))", norm_title, re.IGNORECASE)
            fn_str = fn_match.group(1).strip() if fn_match else "Financial Spreadsheet"
            file_name = fn_str
            file_language = "Excel Spreadsheet"
            action_verb = f"Quantitative modeling & data analysis in {fn_str}"

        # B. Strategy & Executive Presentation (PowerPoint, Keynote)
        elif any(prs in app_lower for prs in ["powerpnt", "powerpoint", "keynote"]) or ".pptx" in title_lower or ".ppt" in title_lower:
            workflow_phase = "Strategy & Executive Presentation"
            fn_match = re.search(r"([\w\-\_\s]{2,40}\.(?:pptx?))", norm_title, re.IGNORECASE)
            fn_str = fn_match.group(1).strip() if fn_match else "Strategy Deck"
            file_name = fn_str
            file_language = "Presentation Deck"
            action_verb = f"Designing executive presentation in {fn_str}"

        # C. Writing, Editorial & Manuscripts (Word, Scrivener, Notion, Obsidian)
        elif any(w in app_lower for w in ["winword", "word", "scrivener", "notion", "obsidian"]) or ".docx" in title_lower or ".doc" in title_lower:
            workflow_phase = "Writing & Content Authoring"
            fn_match = re.search(r"([\w\-\_\s]{2,40}\.(?:docx?|txt|md|epub))", norm_title, re.IGNORECASE)
            fn_str = fn_match.group(1).strip() if fn_match else "Editorial Manuscript"
            file_name = fn_str
            file_language = "Word Document" if "word" in app_lower else "Manuscript Draft"
            action_verb = f"Authoring manuscript & content in {fn_str}"

        # D. Visual, UI/UX & Creative Design (Figma, Photoshop, Illustrator, Blender, Canva)
        elif any(dsgn in app_lower for dsgn in ["figma", "photoshop", "illustrator", "blender", "canva", "indesign"]):
            workflow_phase = "Visual & UI/UX Design"
            artboard = norm_title.split(" - ")[0].strip() if " - " in norm_title else "Design Canvas"
            file_name = artboard
            file_language = "Design Asset / Canvas"
            action_verb = f"Designing visual canvas & assets in {artboard}"

        # E. Scholarly, Literature & PDF Research (Acrobat, Sumatra, Foxit, Zotero)
        elif any(pdf in app_lower for pdf in ["acrobat", "sumatra", "foxit", "zotero", "mendeley"]) or ".pdf" in title_lower:
            workflow_phase = "Scholarly & Literature Research"
            fn_match = re.search(r"([\w\-\_\s]{2,40}\.pdf)", norm_title, re.IGNORECASE)
            fn_str = fn_match.group(1).strip() if fn_match else "Research Study"
            file_name = fn_str
            file_language = "PDF Literature / Paper"
            action_verb = f"Reviewing academic literature in {fn_str}"

        return {
            "project_name": project_name,
            "file_name": file_name,
            "file_language": file_language,
            "is_dirty": is_dirty,
            "search_query": search_query,
            "web_service": web_service,
            "workflow_phase": workflow_phase,
            "action_verb": action_verb,
            "local_url": locals().get("local_url", ""),
        }

    def analyze_and_compare(
        self,
        current_snapshot: Dict[str, Any],
        previous_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compare current snapshot against previous snapshot and history buffer.
        
        Returns enriched dictionary with:
        - parsed entity fields
        - transition_type
        - is_stuck flag
        - stuck_reason
        - deep_insight
        """
        app = current_snapshot.get("app_name", "Unknown")
        title = current_snapshot.get("window_title", "Desktop")
        is_idle = current_snapshot.get("is_idle", False)

        entities = self.parse_snapshot_entities(app, title)

        transition_type = "Initial Snapshot"
        is_stuck = False
        stuck_reason = ""
        deep_insight = entities["action_verb"]

        if is_idle:
            transition_type = "Idle / Workstation Inactive"
            deep_insight = "User is away from keyboard or workstation is idle"
            enriched = {
                **current_snapshot,
                **entities,
                "transition_type": transition_type,
                "is_stuck": is_stuck,
                "stuck_reason": stuck_reason,
                "deep_insight": deep_insight,
            }
            self._record_history(enriched)
            return enriched

        if previous_snapshot:
            prev_app = previous_snapshot.get("app_name", "")
            prev_title = previous_snapshot.get("window_title", "")
            prev_phase = previous_snapshot.get("workflow_phase", "")
            prev_file = previous_snapshot.get("file_name", "")
            prev_idle = previous_snapshot.get("is_idle", False)

            curr_phase = entities["workflow_phase"]
            curr_file = entities["file_name"]

            if prev_idle:
                transition_type = "Resumption from Break"
                deep_insight = f"Resumed work: {entities['action_verb']}"
            elif prev_app == app and prev_file == curr_file and curr_file:
                transition_type = "Deep Focus Continuation"
                deep_insight = f"Sustained coding on {curr_file}"
            elif prev_app == app and prev_file != curr_file and curr_file and prev_file:
                transition_type = "File Navigation"
                deep_insight = f"Switched context from {prev_file} to {curr_file}"
            elif "Research" in prev_phase and "Coding" in curr_phase:
                transition_type = "Research to Implementation"
                deep_insight = f"Applying researched solutions into {curr_file or 'codebase'}"
            elif "Coding" in prev_phase and "Verification" in curr_phase:
                transition_type = "Implementation to Verification"
                deep_insight = "Testing and verifying code execution in terminal"
            elif "Verification" in prev_phase and "Coding" in curr_phase:
                transition_type = "Verification to Implementation"
                deep_insight = f"Returned to editor to iterate on {curr_file or 'code'}"
            elif "Coding" in prev_phase and "Research" in curr_phase:
                transition_type = "Implementation to Research"
                deep_insight = f"Lookup / Problem solving: {entities['search_query'] or entities['action_verb']}"
            elif "Media" in curr_phase or "Distraction" in curr_phase:
                transition_type = "Context Drift"
                deep_insight = f"Distraction interruption: {entities['action_verb']}"
            else:
                transition_type = f"Workflow Shift ({curr_phase})"
                deep_insight = entities["action_verb"]

        # Loop / Stuck Detection:
        # Check if the user is repeatedly oscillating between IDE and search/docs
        is_stuck, stuck_reason = self._detect_troubleshooting_loop(app, title, entities)
        if is_stuck:
            deep_insight = f"⚠️ Troubleshooting Loop: {stuck_reason} — {entities['action_verb']}"

        enriched = {
            **current_snapshot,
            **entities,
            "transition_type": transition_type,
            "is_stuck": is_stuck,
            "stuck_reason": stuck_reason,
            "deep_insight": deep_insight,
        }
        self._record_history(enriched)
        return enriched

    def _record_history(self, snapshot: Dict[str, Any]) -> None:
        """Keep a rolling window of recent snapshots for sequence analysis."""
        self._history.append(snapshot)
        if len(self._history) > self.history_buffer_size:
            self._history.pop(0)

    def _detect_troubleshooting_loop(
        self, app: str, title: str, entities: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Analyze recent snapshot window to detect rapid oscillations between docs/search and code.
        """
        if len(self._history) < 6:
            return False, ""

        recent = self._history[-6:]
        switches = 0
        research_count = 0
        coding_count = 0

        for i in range(1, len(recent)):
            p = recent[i - 1].get("workflow_phase", "")
            c = recent[i].get("workflow_phase", "")
            if ("Coding" in p and "Research" in c) or ("Research" in p and "Coding" in c):
                switches += 1
            if "Research" in c:
                research_count += 1
            if "Coding" in c:
                coding_count += 1

        # If oscillating back and forth 3+ times in the last 6 ticks
        if switches >= 3 and research_count >= 2 and coding_count >= 2:
            return True, "Repeated back-and-forth debugging between search/docs and code"

        return False, ""
