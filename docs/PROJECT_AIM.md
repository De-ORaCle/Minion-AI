# PROJECT AIM & ARCHITECTURE: Minion — On-Screen Productivity Intelligence

## 1. Executive Summary & Project Aim
**Minion** is a playful yet powerful, privacy-first desktop productivity measurement and work-journaling companion built in Python. Inspired by the loyal and hardworking Minions, it acts as your personal focus assistant, tirelessly keeping track of your screen activities, segmenting your workflows, and distilling your work hours into actionable analytics and shareable updates.

The core aims of the project are:
1. **Accurate, Non-Intrusive Activity Tracking**:
   - Poll active foreground windows, process executables, and window titles at configurable intervals (3s, 5s, 10s, 15s, 30s, 60s).
   - Detect user absence/inactivity (idle detection) using Windows `GetLastInputInfo` so unattended screens do not inflate productivity metrics.
   - Ultra-low system footprint (<0.01% CPU) using native Windows `ctypes` and `psutil`.

2. **Smart Multi-Tier Scored Categorization**:
   - Categorize every activity into distinct categories:
     - `Work / Coding` (Productivity Score: 1.0)
     - `Learning / Research` (Productivity Score: 0.8)
     - `Communication` (Productivity Score: 0.5)
     - `Utilities / System` (Productivity Score: 0.0)
     - `Entertainment / Media` (Productivity Score: -0.5)
     - `Social Media / Distraction` (Productivity Score: -1.0)
     - `Idle / Away` (User Inactive / Screen Locked)
   - Multi-feature scored matching engine:
     - **User-Defined Custom Overrides**: Absolute priority.
     - **Platform & Domain Authority**: High-confidence signatures (e.g. `- YouTube`, `github.com`, `stackoverflow.com`, `slack.com`) take precedence over ambiguous keywords.
     - **Cross-Domain Contextual Guards**: Prevents generic keywords (e.g. "chat" in "Proximity Chat" or "call" in "Call of Duty") from hijacking video streaming sessions.
     - **Local AI Agent (Ollama)**: Offline local LLMs (`llama3.2:3b`) for deep semantic classification and context extraction.
     - **Smart Contextual Fallback**: Guarantees zero uncategorized records.

3. **Temporal Filtering & Visual Reporting**:
   - Filter productivity metrics across arbitrary timeframes: Today, Yesterday, Past 1 Hour, Past 4 Hours, Past 7 Days, Past 30 Days.
   - Compute normalized Productivity Scores (0% to 100%).
   - Embed dynamic Minion-themed visual charts (Donut charts, Top application bar charts) natively within the desktop user interface.
   - Export reports directly to CSV and JSON formats.

4. **Context & Similarity Work Segmentation**:
   - Cluster contiguous and semantically similar window activities into cohesive "Work Sessions" or "Context Threads" (e.g., grouping IDE, documentation tabs, and terminal commands into a single feature-building session).
   - Prevent fragmentation in productivity logs by understanding workflow transitions.

5. **AI-Powered Shareable Work Summaries & Social Posts**:
   - Transform raw interval logs into formatted, engaging work updates suitable for professional sharing (LinkedIn updates, X/Twitter threads, Slack/Teams standup updates, or personal devlogs).
   - Offer customizable tones (Professional, Developer/Technical, Casual Devlog, Team Standup).

6. **100% Offline, Privacy-Preserving AI**:
   - All logging is stored locally in an embedded SQLite database with Write-Ahead Logging (WAL).
   - AI summarization and semantic classification run locally via **Ollama**.
   - No telemetry, no external cloud dependencies, and automatic masking for password managers, banking, and incognito sessions.

7. **Conversational AI Chatbot Landing (Claude / Gemini Style)**:
   - Primary landing page of Minion: An interactive chat assistant allowing users to interrogate their work logs with natural language.
   - Dynamic Minion Greetings Header: Periodically updates with playful and serious Minion greetings ("Bello! What did we accomplish today, boss?", "Tulaliloo ti amo!", "Poopaye distractions!").
   - Suggestion Chat Chips: Clickable prompt cards providing quick exploratory queries ("What did I focus on today?", "Break down my work between 2 PM and 4 PM", "Compare work vs distractions").
   - Deep Retrieval-Augmented Synthesis: Injects factual SQLite screen telemetry into the local Ollama LLM to answer questions with mathematical precision.

8. **Minion-Branded Desktop GUI**:
   - Built with `CustomTkinter` featuring a signature **Minion Yellow** and **Denim Blue** aesthetic on a sleek dark slate background.

---

## 2. Technical Stack & Rationale
| Layer | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.12+ | Rich ecosystem for data processing, OS system calls, and AI integrations. |
| **GUI Framework** | `CustomTkinter` + `Tkinter` | Modern aesthetic, dark-mode native, lightweight, cross-platform compatibility, no heavy electron overhead. |
| **Theme & Palette** | Minion Banana Yellow (`#FACC15`) & Denim Blue (`#2563EB`) | Distinctive, playful, yet professional visual design. |
| **Visualization** | `Matplotlib` (TkAgg Canvas) | Native embedding inside Python GUI, customized Minion color palettes, zero browser dependencies. |
| **OS Window & Activity Inspection** | `ctypes` (`user32.dll`) + `psutil` | Native Windows API calls (`GetForegroundWindow`, `GetWindowTextW`, `GetLastInputInfo`) for sub-millisecond overhead. |
| **Storage Engine** | `SQLite3` (WAL mode) | Embedded, zero-maintenance, ACID-compliant, lightning-fast queries, local privacy. |
| **AI / LLM Engine** | `Ollama` (Local REST API) | Offline, sovereign AI (`llama3.2:3b`, `qwen2.5:3b`, etc.) running directly on the user's hardware. |
| **Data Analysis** | `pandas` + `numpy` | Efficient time-series aggregation, rolling averages, and context grouping. |

---

## 3. Data Flow Diagram
```
[User Active Screen]
        │
        ▼ (Configurable Interval Polling: 3s - 60s)
[Screen Monitor (user32 + psutil)] ───► [Idle Detector (Inactivity check)]
        │
        ▼
[Scored Categorization Engine]
  ├── User-Defined Custom Rules (Priority 1)
  ├── Platform & Domain Signatures (+60 pts)
  ├── Thematic Regex Heuristics (+25 pts / +10 pts)
  ├── Contextual Guards (-80 pts cross-domain penalty)
  └── Local Ollama Model (Ambiguous or Deep Context)
        │
        ▼
[SQLite Storage (WAL Mode)]
  ├── Raw Activity Logs
  ├── Context Clusters / Work Sessions
  └── Generated Posts & Reports
        │
        ├──► [Analytics & Visual Charts Engine] ──► GUI Reports Tab
        ├──► [Context Clustering Engine]       ──► GUI Work Segments Tab
        └──► [Post Synthesis Engine (Ollama)] ──► GUI Shareable Posts Tab
```
