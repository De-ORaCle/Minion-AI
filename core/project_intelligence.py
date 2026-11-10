"""
Universal Project Intelligence, Tool Mastery & Deliverable Monitoring for Minion AI.

This module ensures that Minion provides the exact same high-depth intelligence,
active workspace linking, tool optimization, and multi-angle strategic improvement
across ALL user types and professions:
1. Writers & Authors (Word documents, manuscripts, articles, Substack)
2. Designers & Artists (Figma boards, Photoshop, Illustrator, 3D scenes)
3. Business & Finance Executives (Excel financial models, PowerPoint decks, spreadsheets)
4. Researchers & Scholars (Academic papers, literature reviews, PDF studies)
5. Software Engineers & DevOps (Localhost web servers, repositories, code stacks)
6. General Knowledge Workers & Managers (Core deliverables, task documents, project trackers)
"""

import os
import re
import sys
import logging
import webbrowser
import subprocess
from typing import Dict, Any, List, Optional
import psutil

logger = logging.getLogger(__name__)

# Standard development server port candidates
COMMON_DEV_PORTS = [5176, 5173, 5174, 5175, 5177, 3000, 3001, 8000, 8080, 5000, 4200, 8888]


# =============================================================================
# 1. UNIVERSAL DELIVERABLE & WORKSPACE DETECTOR
# =============================================================================
def detect_active_deliverable(
    activities: Optional[List[Dict[str, Any]]] = None,
    domain: str = "general",
    project_hint: str = "",
) -> Dict[str, Any]:
    """
    Detect the user's primary active deliverable and quick-access link/file
    across ANY profession:
    - Writers: Active Word manuscript, draft, or article (.docx)
    - Financial Analysts: Active Excel financial model or PowerPoint deck (.xlsx, .pptx)
    - Designers: Active Figma artboard or creative asset (.fig, .psd)
    - Researchers: Active academic literature study or PDF paper (.pdf)
    - Software Developers: Active local dev server (http://localhost:5176/)
    
    Returns a unified deliverable dictionary:
    - title: Human-readable deliverable name
    - type: Deliverable category
    - icon: Appropriate craft glyph
    - action_label: Label for the desktop button
    - action_type: 'url' or 'file' or 'focus'
    - target: URL or filename or process
    - status: Current state
    - summary: Actionable deliverable summary
    """
    domain_clean = (domain or "general").lower().strip()
    is_software = any(k in domain_clean for k in ["software", "engineer", "dev", "developer", "code", "coding"])
    is_writing = any(k in domain_clean for k in ["write", "writer", "writing", "author", "editorial", "journalis", "content"])
    is_business = any(k in domain_clean for k in ["busines", "finance", "analyst", "bank", "invest", "exec", "strateg", "manager"])
    is_design = any(k in domain_clean for k in ["design", "ui", "ux", "artist", "creative", "illustrat"])
    is_research = any(k in domain_clean for k in ["research", "academic", "scholar", "scien", "phd", "student"])

    # 1. Project-Specific Deliverable Match
    p_lower = (project_hint or "").lower()
    if "minion" in p_lower or "productivitycheck" in p_lower:
        return {
            "title": "Minion AI Desktop Application",
            "type": "Desktop Focus Intelligence System",
            "icon": "🤖",
            "action_label": "⚡ Focus / Inspect Minion AI",
            "action_type": "focus",
            "target": "main.py",
            "status": "Active CustomTkinter GUI & Telemetry Store",
            "summary": "Core desktop focus companion running with real-time screen activity watcher and local SQLite context store.",
        }

    # For Web Dev & Localhost Servers (Active dev port or live web apps)
    local_server = detect_active_local_server()
    if local_server:
        server_hint = local_server.get("project_hint", "")
        # Only attach to this project if project_hint matches the web server, or if project_hint is empty/generic
        is_web_project = (
            not p_lower
            or "dealroom" in p_lower
            or "web" in p_lower
            or (server_hint and server_hint.lower() in p_lower)
            or any(s in p_lower for s in ["react", "vite", "frontend", "cms", "app", "ui"])
        )
        if is_web_project and (is_software or not (is_writing or is_business or is_design or is_research)):
            hint = server_hint or project_hint or "Web Application"
            return {
                "title": f"Live Web App ({hint})",
                "type": "Live Web Development Server",
                "icon": "🌐",
                "action_label": f"🚀 Launch in Browser ({local_server['port']})",
                "action_type": "url",
                "target": local_server["url"],
                "status": f"Online (Listening on Port {local_server['port']})",
                "summary": "Active local web server ready for live testing and review.",
            }

    # 2. Extract deliverable from recent activities or window titles across all professions
    if activities:
        for a in activities[:15]:
            title = a.get("window_title", "")
            app = a.get("app_name", "").lower()
            title_lower = title.lower()

            # A. WRITERS, AUTHORS & EDITORIAL
            if any(w in app for w in ["winword", "word.", "scrivener", "notion"]) or any(ext in title_lower for ext in [".docx", ".doc", "draft", "manuscript", "chapter"]):
                doc_name = _extract_file_or_title(title, [".docx", ".doc"]) or "Manuscript Draft"
                return {
                    "title": f"Editorial Manuscript: {doc_name}",
                    "type": "Document & Manuscript Authoring",
                    "icon": "📄",
                    "action_label": f"📄 Focus / Open Document",
                    "action_type": "focus",
                    "target": doc_name,
                    "status": "Active in Microsoft Word / Editor",
                    "summary": "Primary written deliverable. Focus on narrative flow, pacing, and chapter progression.",
                }

            # B. FINANCE & BUSINESS STRATEGY (Spreadsheets & Decks)
            if any(e in app for e in ["excel", "calc"]) or any(ext in title_lower for ext in [".xlsx", ".xls", ".csv", "model", "budget", "p&l", "forecast"]):
                sheet_name = _extract_file_or_title(title, [".xlsx", ".xls", ".csv"]) or "Financial Model"
                return {
                    "title": f"Financial Model: {sheet_name}",
                    "type": "Spreadsheet Architecture & Financial Modeling",
                    "icon": "📊",
                    "action_label": f"📊 Focus / Open Spreadsheet",
                    "action_type": "focus",
                    "target": sheet_name,
                    "status": "Active in Microsoft Excel",
                    "summary": "Active quantitative model. Verify formula integrity, unit economics, and scenario sensitivity.",
                }

            if any(p in app for p in ["powerpnt", "powerpoint", "keynote"]) or any(ext in title_lower for ext in [".pptx", ".ppt", "deck", "pitch", "slides"]):
                deck_name = _extract_file_or_title(title, [".pptx", ".ppt"]) or "Executive Strategy Deck"
                return {
                    "title": f"Strategy Deck: {deck_name}",
                    "type": "Executive Presentation & Strategy",
                    "icon": "🖥️",
                    "action_label": f"🖥️ Focus / Review Presentation",
                    "action_type": "focus",
                    "target": deck_name,
                    "status": "Active in PowerPoint",
                    "summary": "Core pitch deck. Ensure executive takeaway and core value proposition are clear upfront.",
                }

            # C. DESIGNERS & CREATIVE ARTISTS
            if "figma" in app or "figma" in title_lower or any(ext in title_lower for ext in [".fig", ".psd", ".ai", ".blend"]):
                artboard = title.split(" - ")[0].strip() if " - " in title else "Design Canvas"
                return {
                    "title": f"Design Canvas: {artboard}",
                    "type": "UI/UX & Visual Design Canvas",
                    "icon": "🎨",
                    "action_label": f"🎨 Focus / Inspect Artboard",
                    "action_type": "focus",
                    "target": artboard,
                    "status": "Active in Figma / Creative Tool",
                    "summary": "Primary visual artboard. Audit typography hierarchy, spatial grids, and touch contrast.",
                }

            # D. RESEARCHERS & SCHOLARS
            if any(pdf in app for pdf in ["acrobat", "sumatra", "foxit", "zotero", "mendeley"]) or any(ext in title_lower for ext in [".pdf", "literature", "study", "journal"]):
                paper_name = _extract_file_or_title(title, [".pdf"]) or "Research Literature"
                return {
                    "title": f"Scholarly Paper: {paper_name}",
                    "type": "Academic Literature & Research Study",
                    "icon": "📚",
                    "action_label": f"📚 Focus / Read Literature",
                    "action_type": "focus",
                    "target": paper_name,
                    "status": "Active in Literature Reader",
                    "summary": "Key research source. Verify citation validity, methodology rigor, and peer findings.",
                }

            # E. CODE & SOFTWARE FILES (Hero.jsx, app.py, etc.)
            if any(ext in title_lower for ext in [".jsx", ".tsx", ".js", ".ts", ".py", ".html", ".css", "antigravity", "visual studio code"]):
                code_file = _extract_file_or_title(title, [".jsx", ".tsx", ".js", ".ts", ".py", ".html"]) or "Source Code"
                local_server = detect_active_local_server()
                if local_server:
                    return {
                        "title": f"Live Web App ({local_server['project_hint']})",
                        "type": "Live Web Development Server",
                        "icon": "🌐",
                        "action_label": f"🚀 Launch in Browser ({local_server['port']})",
                        "action_type": "url",
                        "target": local_server["url"],
                        "status": f"Online (Listening on Port {local_server['port']})",
                        "summary": f"Active local dev server running while editing {code_file}.",
                    }
                return {
                    "title": f"Source Code: {code_file}",
                    "type": "Software Architecture & Code",
                    "icon": "💻",
                    "action_label": f"💻 Focus Editor ({code_file})",
                    "action_type": "focus",
                    "target": code_file,
                    "status": "Active in Code Editor",
                    "summary": "Primary source code file. Modular component structure and automated tests maximize velocity.",
                }

    # 3. Check for local development server if running on machine and applicable
    local_server = detect_active_local_server()
    if local_server and ("minion" not in p_lower and "productivitycheck" not in p_lower):
        server_hint = local_server.get("project_hint", "")
        hint = server_hint or project_hint or "Web Application"
        return {
            "title": f"Live Web App ({hint})",
            "type": "Live Web Development Server",
            "icon": "🌐",
            "action_label": f"🚀 Launch in Browser ({local_server['port']})",
            "action_type": "url",
            "target": local_server["url"],
            "status": f"Online (Listening on Port {local_server['port']})",
            "summary": "Active local web server ready for live testing and review.",
        }

    # 4. Domain Fallback Deliverable
    domain_fallbacks = {
        "writing": ("Editorial Draft & Manuscript", "Document Authoring", "📄", "📄 Review Active Manuscript", "Manuscript.docx"),
        "design": ("UI/UX Design Artboard", "Visual Design Canvas", "🎨", "🎨 Inspect Design Board", "DesignCanvas.fig"),
        "business": ("Financial Model & Strategy Deck", "Executive Modeling", "📊", "📊 Open Financial Model", "FinancialModel.xlsx"),
        "research": ("Research Study & Literature", "Academic Review", "📚", "📚 Review Research Paper", "LiteratureStudy.pdf"),
        "software": ("Active Codebase & Web Server", "Software Systems", "💻", "🚀 Test Code on Localhost", "http://localhost:5176/"),
        "general": ("Core Active Deliverable", "Primary Work Deliverable", "📁", "📁 Focus Deliverable", "Deliverable"),
    }

    target_key = "general"
    if is_writing:
        target_key = "writing"
    elif is_design:
        target_key = "design"
    elif is_business:
        target_key = "business"
    elif is_research:
        target_key = "research"
    elif is_software:
        target_key = "software"

    title_fb, type_fb, icon_fb, label_fb, target_fb = domain_fallbacks.get(target_key, domain_fallbacks["general"])
    act_type = "url" if target_fb.startswith("http") else "focus"
    return {
        "title": project_hint or title_fb,
        "type": type_fb,
        "icon": icon_fb,
        "action_label": label_fb,
        "action_type": act_type,
        "target": target_fb,
        "status": "Tracking Focused Work",
        "summary": "Main active focus target. Sustained focus without context switching yields highest velocity.",
    }


def activate_deliverable(deliverable: Dict[str, Any]) -> bool:
    """
    Launch, focus, or open the user's primary deliverable across ANY profession:
    - If URL -> opens in default browser (web testing).
    - If file -> opens in default OS application (Word, Excel, Figma, PDF reader).
    - If focus -> opens application or activates window.
    """
    if not deliverable:
        return False

    target = str(deliverable.get("target", "")).strip()
    action_type = deliverable.get("action_type", "focus")

    # 1. URL / Web Application
    if action_type == "url" or target.startswith("http://") or target.startswith("https://"):
        return open_local_server(target)

    # 2. Existing File on Disk
    if os.path.exists(target):
        try:
            os.startfile(target)
            logger.info(f"Opened deliverable file: {target}")
            return True
        except Exception as e:
            logger.debug(f"Could not open file with os.startfile: {e}")

    # 3. Application Launcher by Deliverable Type
    deliv_type = deliverable.get("type", "").lower()
    try:
        c_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0
        if "word" in deliv_type or "manuscript" in deliv_type:
            subprocess.Popen(["start", "winword"], shell=True, creationflags=c_flags)
            return True
        elif "excel" in deliv_type or "spreadsheet" in deliv_type or "financial" in deliv_type:
            subprocess.Popen(["start", "excel"], shell=True, creationflags=c_flags)
            return True
        elif "presentation" in deliv_type or "powerpoint" in deliv_type:
            subprocess.Popen(["start", "powerpnt"], shell=True, creationflags=c_flags)
            return True
        elif "design" in deliv_type or "figma" in deliv_type:
            # Open web Figma or desktop Figma if available
            webbrowser.open("https://www.figma.com", new=2)
            return True
    except Exception as e:
        logger.debug(f"Could not launch app for deliverable: {e}")

    return False


def _extract_file_or_title(title: str, extensions: List[str]) -> Optional[str]:
    """Helper to extract a clean filename from window title."""
    for ext in extensions:
        m = re.search(r"([\w\-\_\s]{2,50}" + re.escape(ext) + r")", title, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    parts = [p.strip() for p in re.split(r"[-–—|•]", title) if len(p.strip()) > 2]
    return parts[0] if parts else None


def detect_active_local_server() -> Optional[Dict[str, Any]]:
    """
    Detect if any local development server is actively listening on localhost.
    Checks ports like 5176 (Vite), 5173, 3000 (React/Next), etc.
    """
    try:
        connections = psutil.net_connections(kind="inet")
        listening = [c for c in connections if c.status == "LISTEN" and c.laddr and c.laddr.port in COMMON_DEV_PORTS]
        
        if not listening:
            return None

        # Prioritize 5176 (active project port) then lowest standard port
        listening.sort(key=lambda c: 0 if c.laddr.port == 5176 else 1)
        target_conn = listening[0]
        port = target_conn.laddr.port
        pid = target_conn.pid

        proc_name = "Node / Web Dev Server"
        project_hint = ""
        cmdline_str = ""

        if pid:
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
                cmd = proc.cmdline()
                cmdline_str = " ".join(cmd)
                # Dynamically extract project hint from working directory
                try:
                    cwd = proc.cwd()
                    if cwd:
                        project_hint = os.path.basename(os.path.normpath(cwd))
                except Exception:
                    pass
                if not project_hint and cmd:
                    for arg in cmd:
                        if os.path.isabs(arg) and os.path.exists(arg):
                            project_hint = os.path.basename(os.path.normpath(arg))
                            break
            except Exception:
                pass

        url = f"http://localhost:{port}/"
        return {
            "url": url,
            "port": port,
            "pid": pid,
            "process": proc_name,
            "project_hint": project_hint or "Local Web Application",
            "is_listening": True,
        }
    except Exception as e:
        logger.debug(f"Error checking local server ports: {e}")
        return None


def open_local_server(url: str = "http://localhost:5176/") -> bool:
    """Launch the local development URL in the user's default browser."""
    try:
        webbrowser.open(url, new=2)
        logger.info(f"Opened local development server in browser: {url}")
        return True
    except Exception as e:
        logger.error(f"Failed to open local link {url}: {e}")
        return False


# =============================================================================
# 2. UNIVERSAL STRATEGIC PROJECT IMPROVEMENT ANGLES
# =============================================================================
def _finalize_angles(angles: List[Dict[str, str]], project_name: str, scope: str) -> List[Dict[str, str]]:
    """Enrich angles with time-horizon specific recommendations and stable keys."""
    enriched = list(angles)
    if scope == "today":
        enriched.insert(0, {
            "angle": "⚡ Today's Sprint Velocity & Execution",
            "summary": "Single High-Impact Deliverable Completion Target",
            "recommendation": f"Focus today's active session exclusively on advancing {project_name}. Commit code and verify local build stability on localhost:5176 before context switching.",
        })
    elif scope == "week":
        enriched.insert(0, {
            "angle": "🗓️ Weekly Architecture & Release Health",
            "summary": "Technical Debt Paydown & Weekly Cadence",
            "recommendation": f"Audit {project_name} against this week's sprint milestones. Ensure component decoupling and data contracts are tested and documented for clean release.",
        })
    elif scope == "alltime":
        enriched.insert(0, {
            "angle": "🏆 Long-Term Scalability & Governance Moat",
            "summary": "Institutional Value & Modular Extensibility",
            "recommendation": f"Strengthen {project_name} for durable long-term maintainability. Ensure zero-dependency portability and audit-ready data models.",
        })

    for ang in enriched:
        if "key" not in ang:
            ang["key"] = f"{project_name}::{ang.get('summary') or ang.get('angle')}"
    return enriched


def generate_strategic_project_angles(
    project_name: str,
    category: str,
    stack: List[str],
    domain: str = "general",
    time_scope: str = "realtime",
) -> List[Dict[str, str]]:
    """
    Generate deep, multi-perspective strategic improvement angles tailored to the
    user's profession, specific deliverable, and time horizon (realtime, today, week, alltime).
    """
    p_lower = (project_name + " " + category).lower()
    d_lower = (domain or "general").lower().strip()
    scope = (time_scope or "realtime").lower()

    angles = []

    # 1. SPECIFIC PROJECT OVERRIDE: Healthcare / Debt Syndication Platforms
    if any(k in p_lower for k in ["healthcare", "debt", "syndication", "dealroom"]):
        angles.append({
            "angle": "🛡️ Regulatory Compliance & Clinical Data Privacy",
            "summary": "HIPAA & Private Debt Audit Integrity",
            "recommendation": (
                "Ensure dealroom documentation adheres to healthcare compliance standards. "
                "Implement granular role-based access control (RBAC) separating Lead Arrangers, Participant Lenders, and Healthcare Borrowers. "
                "Enforce immutable audit trails for sensitive loan terms, balance sheet disclosures, and credit memo downloads."
            ),
        })
        angles.append({
            "angle": "📈 Investor Syndication UX & Conversion Velocity",
            "summary": "Frictionless Tranche Modeling & Clear Yield Visualizations",
            "recommendation": (
                "Simplify debt tranche participation for institutional partners: add an interactive yield calculator and visual repayment waterfall. "
                "Ensure lenders can simulate loan-to-value (LTV) scenarios and cash flow debt service coverage (DSCR) before committing capital."
            ),
        })
        if any(k in d_lower for k in ["business", "finance", "analyst", "bank"]):
            angles.append({
                "angle": "📊 Financial Covenant & Tranche Waterfall Modeling",
                "summary": "Stress-Testing DSCR, Senior Debt Tranches & Yield Waterfall",
                "recommendation": (
                    "Build automated debt service coverage ratio (DSCR) stress tests under 10% and 25% clinical revenue downturns. "
                    "Ensure senior secured debt tranches have clear collateral priority over mezzanine notes, and model principal repayment timing accurately."
                ),
            })
        elif any(k in d_lower for k in ["design", "creative", "ui", "ux"]):
            angles.append({
                "angle": "🎨 Dealroom UI/UX, Data Hierarchy & WCAG Contrast",
                "summary": "High-Trust Typography, Chart Legibility & Scannable Metrics",
                "recommendation": (
                    "Audit dealroom financial charts and tranche progress bars for high contrast and executive legibility. "
                    "Ensure institutional participants can parse loan terms, maturity dates, and risk ratings within 5 seconds of scanning."
                ),
            })
        elif any(k in d_lower for k in ["write", "writer", "writing", "editorial"]):
            angles.append({
                "angle": "✍️ Investment Memorandum & Pitch Narrative Precision",
                "summary": "Clear Executive Summaries & Impact Storytelling",
                "recommendation": (
                    "Structure the credit memorandum with an executive summary that leads with debt coverage safety and clinical mission impact. "
                    "Eliminate ambiguous jargon in borrower profiles to accelerate investment committee approvals."
                ),
            })
        elif any(k in d_lower for k in ["research", "academic", "scholar"]):
            angles.append({
                "angle": "🔬 Clinical Evidence Base & Health Economics Outcomes (HEOR)",
                "summary": "Peer-Reviewed Medical Literature & Efficacy Data Backing",
                "recommendation": (
                    "Anchor the syndication borrower narrative against clinical evidence and Health Economics and Outcomes Research (HEOR) metrics. "
                    "Cite peer-reviewed literature showing treatment efficacy and cost-effectiveness of the medical equipment and clinical facilities being financed."
                ),
            })
        else:
            angles.append({
                "angle": "⚡ Frontend Architecture & Performance (React JSX)",
                "summary": "Component Decoupling & Deal Table Virtualization",
                "recommendation": (
                    "Decouple heavy presentation views (like Hero.jsx and TrustAndImpact.jsx) into reusable atomic components. "
                    "Use virtualization for long debt asset tables and lazy-load third-party trust certifications to maintain instant 60fps responsiveness on localhost:5176."
                ),
            })

        angles.append({
            "angle": "🤝 Trust, Social Proof & Clinical Impact Narrative",
            "summary": "Bridge Financial ROI with Real Healthcare Outcomes",
            "recommendation": (
                "Reinforce the 'Trust & Impact' narrative: demonstrate how private debt facilities directly finance medical equipment, clinical expansion, and patient care capacity. "
                "Display audited repayment history badges prominently on deal overview cards."
            ),
        })
        return _finalize_angles(angles, project_name, scope)

    # 2. WRITERS, AUTHORS, JOURNALISTS & EDITORIAL
    if any(k in d_lower for k in ["write", "writer", "writing", "author", "editorial"]) or any(w in p_lower for w in ["editorial", "author", "manuscript", "draft", "book", "article", "content"]):
        angles.append({
            "angle": "📖 Narrative Arc & Reader Engagement Pacing",
            "summary": "Hook Strength & Mid-Section Energy Retention",
            "recommendation": (
                "Ensure the opening hook establishes immediate stakes within the first 2 paragraphs. "
                "Audit chapter transitions for active narrative questions that compel the reader to turn the page rather than pause."
            ),
        })
        angles.append({
            "angle": "✍️ Stylistic Precision & Voice Consistency",
            "summary": "Eliminating Passive Construction & Tightening Verbs",
            "recommendation": (
                "Scan for passive voice, repeated adjectives, and unnecessary qualifiers ('very', 'really', 'somewhat'). "
                "Strengthen primary action verbs to maintain a crisp, authoritative tone tailored to your target audience."
            ),
        })
        angles.append({
            "angle": "🎯 Audience Clarity & Readability Index",
            "summary": "Sentence Cadence & Complex Terminology Simplification",
            "recommendation": (
                "Vary sentence lengths to create a rhythmic reading cadence. "
                "When introducing complex domain concepts or specialized terminology, ground them in relatable metaphors before deep exposition."
            ),
        })
        angles.append({
            "angle": "📢 Publishing & Distribution Strategy",
            "summary": "Header Structure, Pull Quotes & Reader Retention",
            "recommendation": (
                "Structure formatting with scannable subheadings, memorable pull quotes, and clear executive summaries. "
                "Include a distinct, high-impact concluding call-to-action or open synthesis question."
            ),
        })
        return _finalize_angles(angles, project_name, scope)

    # 3. DESIGNERS, UI/UX & CREATIVE ARTISTS
    if any(k in d_lower for k in ["design", "ui", "ux", "artist", "creative"]) or any(w in p_lower for w in ["design", "ui", "ux", "figma", "artboard", "brand", "visual"]):
        angles.append({
            "angle": "👁️ Visual Hierarchy & Focal Point Guidance",
            "summary": "Guiding the Eye Across Layout Layers",
            "recommendation": (
                "Verify the primary call-to-action is unmistakable within 2 seconds of scanning. "
                "Use size contrast, subtle elevations, and deliberate whitespace rather than busy decorative elements to establish priority."
            ),
        })
        angles.append({
            "angle": "📐 Design System & Token Rigor",
            "summary": "Consistent Spacing Grids & Typography Scales",
            "recommendation": (
                "Audit the artboard against an 8pt spatial grid to eliminate arbitrary margins. "
                "Standardize typography tokens (H1, H2, body, caption) and color palettes across all modal and page states."
            ),
        })
        angles.append({
            "angle": "♿ Accessibility & Touch Target Standards",
            "summary": "WCAG AA Contrast & Ergonomic Interaction",
            "recommendation": (
                "Ensure all text against colored surfaces satisfies a minimum 4.5:1 contrast ratio. "
                "Guarantee interactive buttons and tap targets meet the 44x44px minimum for seamless mobile and desktop usability."
            ),
        })
        angles.append({
            "angle": "📱 Responsive Fluidity & Edge Cases",
            "summary": "Behavior on Mobile, Tablet & High-DPI Displays",
            "recommendation": (
                "Test component wrapping on narrow viewports (375px) and ultra-wide screens (1440px+). "
                "Design intentional empty and loading skeleton states so the UI never feels broken during data transitions."
            ),
        })
        return _finalize_angles(angles, project_name, scope)

    # 4. BUSINESS STRATEGISTS, FINANCE ANALYSTS & EXECUTIVES
    if any(k in d_lower for k in ["business", "finance", "analyst", "bank", "invest"]) or any(w in p_lower for w in ["finance", "business", "model", "deck", "budget", "p&l", "strategy"]):
        angles.append({
            "angle": "🔢 Unit Economics & Cash Flow Sensitivity",
            "summary": "Stress-Testing Assumptions & Margin Vulnerability",
            "recommendation": (
                "Incorporate baseline, best-case, and conservative downside scenarios into financial projections. "
                "Identify high-sensitivity variables (churn rate, customer acquisition cost, gross margin compression) and model contingency buffers."
            ),
        })
        angles.append({
            "angle": "📊 Executive Storytelling & Data Clarity",
            "summary": "Actionable Takeaways Upfront in Decks",
            "recommendation": (
                "Follow the pyramid principle in slide presentations: place the key conclusion in the slide header rather than burying it beneath charts. "
                "Strip redundant gridlines and secondary data points so leadership can absorb the core metric immediately."
            ),
        })
        angles.append({
            "angle": "⚖️ Risk Governance & Model Integrity",
            "summary": "Eliminating Hardcoded Traps & Audit Gaps",
            "recommendation": (
                "Segregate model input parameters from calculation engines. Never hardcode numbers inside calculation formulas. "
                "Include automated balance check rows to flag out-of-balance balance sheets or circular references."
            ),
        })
        angles.append({
            "angle": "🚀 Operational Scalability & Resource Allocation",
            "summary": "Clear Milestone Accountability & Execution Timeline",
            "recommendation": (
                "Map planned deliverables to direct revenue or cost savings milestones. "
                "Establish clear department owners and 30-60-90 day review gates to avoid scope creep."
            ),
        })
        return _finalize_angles(angles, project_name, scope)

    # 5. RESEARCHERS, SCHOLARS & SCIENTISTS
    if any(k in d_lower for k in ["research", "academic", "scholar", "scien", "phd"]) or any(w in p_lower for w in ["research", "academic", "literature", "study", "paper", "scientific"]):
        angles.append({
            "angle": "🔬 Methodological Rigor & Internal Validity",
            "summary": "Sample Representation & Confounder Controls",
            "recommendation": (
                "Explicitly address potential selection biases and uncontrolled confounding variables in your methodology section. "
                "Ensure sample sizes satisfy statistical power criteria and that measurement procedures are fully replicable."
            ),
        })
        angles.append({
            "angle": "📑 Literature Synthesis & Gap Identification",
            "summary": "Corroboration with Recent Peer-Reviewed Findings",
            "recommendation": (
                "Anchor core hypotheses against landmark papers while citing recent peer-reviewed advances from the past 24 months. "
                "Clearly demarcate where current scientific consensus ends and your unique investigation begins."
            ),
        })
        angles.append({
            "angle": "💡 Novel Contribution & Theoretical Significance",
            "summary": "Highlighting Original Empirical Findings",
            "recommendation": (
                "Synthesize complex raw data into a standalone conceptual diagram or summary matrix. "
                "Ensure the abstract and discussion clearly state the practical and theoretical implications of your findings."
            ),
        })
        angles.append({
            "angle": "🏛️ Peer-Review & Publication Readiness",
            "summary": "Adherence to Target Journal Standards & Citation Formats",
            "recommendation": (
                "Format citations and bibliography rigorously according to target journal guidelines (APA, IEEE, Nature, Harvard). "
                "Prepare supplementary data appendices and open science repository links in advance."
            ),
        })
        return _finalize_angles(angles, project_name, scope)

    # 6. SOFTWARE ENGINEERS & DEVOPS
    if any(k in d_lower for k in ["software", "engineer", "dev", "developer", "code", "coding"]) or any(w in p_lower for w in ["code", "software", "developer", "engineering", "minion", "api"]):
        angles.append({
            "angle": "⚡ Architecture, Modularity & Decoupling",
            "summary": "Clean Separation of Concerns & Clean Code",
            "recommendation": (
                "Ensure core domain logic remains strictly decoupled from UI components and storage layers. "
                "Introduce automated tests and clean interfaces to make future refactoring painless."
            ),
        })
        angles.append({
            "angle": "🛡️ Security, Input Sanitization & State Durability",
            "summary": "ACID Compliance & Robust Error Handling",
            "recommendation": (
                "Sanitize all external inputs and enforce parameterized queries on database layers. "
                "Implement graceful error recovery with user-friendly toast messages instead of unhandled exceptions."
            ),
        })
        angles.append({
            "angle": "🚀 Performance Optimization & Low Latency",
            "summary": "Async Concurrency & Resource Efficiency",
            "recommendation": (
                "Offload disk I/O and network operations to background threads to prevent UI freezes. "
                "Profile memory consumption and optimize render cycles using memoization and virtualized lists."
            ),
        })
        angles.append({
            "angle": "📦 Zero-Dependency Portability & Packaging",
            "summary": "Embedded Runtimes & 1-Click Installers",
            "recommendation": (
                "Package standalone distribution binaries with embedded runtimes so end users require zero manual setup. "
                "Provide automated one-click Windows installers with desktop shortcuts and clean uninstallation."
            ),
        })
        return _finalize_angles(angles, project_name, scope)

    # 7. GENERAL KNOWLEDGE WORKERS & PRODUCERS
    angles.append({
        "angle": "🎯 Goal Alignment & High-Leverage Output",
        "summary": "Prioritizing the Most Critical 20% Deliverable",
        "recommendation": (
            "Identify the single highest-impact deliverable that unblocks all secondary tasks today. "
            "Protect dedicated 45-minute sprint intervals to make progress before checking inbox messages."
        ),
    })
    angles.append({
        "angle": "⏱️ Bottleneck Removal & Execution Velocity",
        "summary": "Streamlining Multi-Step Workflow Dependencies",
        "recommendation": (
            "Break down vague milestones into concrete 15-minute sub-actions. "
            "Resolve external dependencies early in the morning so colleagues can unblock work asynchronously."
        ),
    })
    angles.append({
        "angle": "🛡️ Distraction Shielding & Flow Maintenance",
        "summary": "Minimizing Rapid Context Switching",
        "recommendation": (
            "Batch incoming email and messaging notifications into scheduled 15-minute review windows. "
            "Keep active workspace documents full-screen to prevent unintentional tab drift."
        ),
    })
    return _finalize_angles(angles, project_name, scope)


# =============================================================================
# 3. UNIVERSAL TOOL MASTERY & VELOCITY ACCELERATORS
# =============================================================================
def generate_tool_optimizations(stack: List[str], domain: str = "general") -> List[Dict[str, str]]:
    """
    Generate actionable techniques and power tips for the user's active tools
    across ANY software suite to 10x workflow velocity.
    """
    optimizations = []
    stack_lower = [s.lower() for s in stack]
    d_lower = (domain or "general").lower().strip()

    # 1. Microsoft Word / Google Docs / Editorial Tools
    if any(w in s for s in stack_lower for w in ["word", "doc", "editorial", "manuscript", "draft"]):
        optimizations.append({
            "tool": "📝 Microsoft Word / Drafting Tools",
            "tip": (
                "Use Navigation Pane (Ctrl+F > Headings) to outline chapters visually. "
                "Apply built-in Heading Styles (Ctrl+Alt+1, 2) rather than manual font sizing to allow 1-click restructuring."
            ),
        })
        optimizations.append({
            "tool": "✍️ Editorial Revision Velocity",
            "tip": (
                "Toggle Track Changes (Ctrl+Shift+E) for multi-pass editing. "
                "Use the 'Read Aloud' accessibility feature (Alt+Ctrl+Space) to catch awkward phrasing that the eye misses."
            ),
        })

    # 2. Microsoft Excel / Spreadsheets / Financial Modeling
    if any(e in s for s in stack_lower for e in ["excel", "sheet", "csv", "spreadsheet", "model"]):
        optimizations.append({
            "tool": "📊 Microsoft Excel & Financial Modeling",
            "tip": (
                "Replace legacy VLOOKUP with XLOOKUP or INDEX/MATCH for robust column reordering. "
                "Use dynamic array formulas (UNIQUE, FILTER, SORT) to build self-updating data summaries with zero manual drag-down."
            ),
        })
        optimizations.append({
            "tool": "🔢 Model Auditing & Error Shields",
            "tip": (
                "Use Trace Precedents (Ctrl+[) and Trace Dependents (Ctrl+]) to navigate formula chains instantly without touching the mouse. "
                "Color-code inputs (blue text), calculations (black text), and external links (green text) to maintain institutional modeling standards."
            ),
        })

    # 3. PowerPoint / Keynote / Strategy Decks
    if any(p in s for s in stack_lower for p in ["powerpoint", "presentation", "deck", "slides"]):
        optimizations.append({
            "tool": "🖥️ PowerPoint & Executive Presentations",
            "tip": (
                "Follow the 6x6 rule: no more than 6 bullet points with 6 words each per slide. "
                "Leverage the Slide Master (View > Slide Master) to lock corporate typography and margins across all 50+ slides automatically."
            ),
        })

    # 4. Figma / UI/UX / Creative Design Tools
    if any(f in s for s in stack_lower for f in ["figma", "photoshop", "illustrator", "design", "canvas"]):
        optimizations.append({
            "tool": "🎨 Figma & Design System Architecture",
            "tip": (
                "Wrap elements in Auto-Layout (Shift+A) with 8pt padding increments for responsive components that resize flawlessly. "
                "Use Component Variants with boolean component properties to reduce artboard variant clutter by 70%."
            ),
        })
        optimizations.append({
            "tool": "📐 Visual Hierarchy & Spatial Grid",
            "tip": (
                "Enable Layout Grid (Shift+G) and set an 8-column or 12-column responsive grid. "
                "Use Figma Tokens / Variables for color modes and typography to test light and high-contrast themes in 1 click."
            ),
        })

    # 5. Academic Literature / PDF Readers / Research Tools
    if any(r in s for s in stack_lower for r in ["pdf", "literature", "research", "acrobat", "zotero"]):
        optimizations.append({
            "tool": "📚 Academic Literature & Citation Tools",
            "tip": (
                "Connect Zotero or Mendeley for automatic DOI reference extraction and instant citation bibtex generation. "
                "Color-code PDF annotations: Yellow for core findings, Green for methodology details, and Pink for counter-evidence."
            ),
        })

    # 6. React JSX / Vite / Web Stacks
    if any(t in s for s in stack_lower for t in ["react", "jsx", "javascript", "vite", "web"]):
        optimizations.append({
            "tool": "⚛️ React JSX & Component Hierarchy",
            "tip": (
                "Extract presentation badges and deal cards into atomic components. "
                "Use React.memo on static presentation blocks to prevent unnecessary re-renders during state changes."
            ),
        })
        optimizations.append({
            "tool": "⚡ Vite Dev Server (localhost:5176)",
            "tip": (
                "Leverage Vite's instant Hot Module Replacement (HMR). Keep CSS modular and test production bundles early with 'npx vite preview'."
            ),
        })

    # 7. Python / SQLite / Desktop Applications
    if any(py in s for s in stack_lower for py in ["python", "sqlite", "customtkinter", "tkinter"]):
        optimizations.append({
            "tool": "🐍 Python & Async Background Concurrency",
            "tip": (
                "Never run network requests (Ollama, HTTP APIs) or disk I/O on the Tkinter main thread. "
                "Always dispatch worker threads and synchronize back with root.after() to keep the UI completely smooth."
            ),
        })
        optimizations.append({
            "tool": "🗄️ SQLite Database Tuning",
            "tip": (
                "Keep Write-Ahead Logging (WAL) and synchronous=NORMAL enabled. "
                "Always query using indexed timestamp columns when filtering activity ranges for instant dashboard loads."
            ),
        })

    # Universal Workspace Ergonomics
    optimizations.append({
        "tool": "💻 Workstation Ergonomics & Dual-Window Workflow",
        "tip": (
            "Split your desktop screen (Windows Key + Left/Right Arrow) with your active document or code on one half "
            "and research/preview on the other half to eliminate repetitive Alt-Tab context switching."
        ),
    })

    return optimizations


# =============================================================================
# 4. UNIVERSAL ACTIONABLE MILESTONES
# =============================================================================
def generate_actionable_milestones(project_name: str, domain: str = "general") -> List[str]:
    """Generate domain-specific high-impact milestones."""
    p_lower = project_name.lower()
    d_lower = (domain or "general").lower().strip()

    if "syndication" in p_lower or "dealroom" in p_lower:
        return [
            "Test local web application and verify layout responsiveness across mobile and desktop viewports.",
            "Refine Trust & Impact hero narrative to emphasize security and verified capital deployment.",
            "Implement confidentiality gating / NDA click-through before room access.",
            "Add interactive financial simulation for institutional partners.",
        ]
    elif "minion" in p_lower:
        return [
            "Verify deep insights and project improvement recommendations on every screen snapshot.",
            "Ensure 1-click launch of active local test links directly from desktop Work Memory and Activity Watcher.",
            "Complete standalone packaging so users can install Minion without python.",
            "Finalize Minion AI chat coaching to provide proactive multi-angle suggestions.",
        ]
    elif d_lower == "writing":
        return [
            "Complete draft for current chapter or article section without stopping to self-edit during flow.",
            "Perform second-pass tightening pass: eliminate passive verbs and repeated qualifiers.",
            "Audit chapter ending for an active narrative hook that pulls reader into next section.",
            "Prepare distribution synopsis, article subtitle, and primary call-to-action.",
        ]
    elif d_lower == "design":
        return [
            "Audit component spacing against the 8pt grid across all active artboard frames.",
            "Verify WCAG AA text-to-background contrast ratios for primary CTA buttons.",
            "Create interactive prototype transitions between main screen and secondary detail modals.",
            "Extract repeated UI cards into reusable master components with variants.",
        ]
    elif d_lower == "business":
        return [
            "Stress-test financial model cash flow against a 20% downside revenue sensitivity case.",
            "Refine executive presentation: place key takeaway in slide title for first 3 slides.",
            "Verify that all formula inputs are segregated into an Assumptions tab with zero hardcoded values.",
            "Review 30-60-90 day milestone roadmap with project stakeholders.",
        ]
    elif d_lower == "research":
        return [
            "Synthesize empirical findings into a structured summary comparison table.",
            "Cross-reference methodology against recent peer-reviewed studies to address confounding variables.",
            "Format bibliography and citations to strictly adhere to target journal requirements.",
            "Draft abstract highlighting novel contribution and primary quantitative takeaway.",
        ]
    else:
        return [
            "Complete the core deliverable draft and eliminate blocking external dependencies.",
            "Review deliverable against high-impact project goals and success criteria.",
            "Streamline formatting and remove unnecessary visual or textual clutter.",
            "Plan prioritized next milestones for upcoming 45-minute focus session.",
        ]
