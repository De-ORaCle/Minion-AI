"""
Database Management Module for ProductivityCheck.

This module provides persistent, ACID-compliant storage using SQLite.
It stores raw activity snapshots, contextual work segments, custom categorization rules,
and shareable social/team posts.

Architectural Rationale:
- SQLite is zero-configuration, embeds directly into Python, and requires no external daemon.
- We enable Write-Ahead Logging (WAL) mode to allow concurrent non-blocking reads from GUI
  threads while the background monitor writes incoming activity logs.
- Indexed timestamps ensure lightning-fast aggregations across arbitrary date and time intervals.
"""

import sqlite3
import datetime
from typing import List, Dict, Any, Optional, Tuple
from config import DB_PATH, CATEGORY_CONFIG


class DatabaseManager:
    """Manages all database interactions, schema initialization, and analytic queries."""

    def __init__(self, db_path: str = DB_PATH):
        """
        Initialize the database manager and ensure all tables and indexes exist.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Create and return a new SQLite connection with WAL mode enabled.
        
        Why separate connection per call/thread:
        SQLite connections cannot be safely shared across different OS threads.
        Opening lightweight connections on-demand with WAL mode prevents threading crashes.
        """
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row  # Access columns by name: row['app_name']
        conn.execute("PRAGMA journal_mode=WAL;")  # Boost concurrent read/write throughput
        conn.execute("PRAGMA synchronous=NORMAL;")  # High performance safe durability
        return conn

    def _init_db(self) -> None:
        """Create tables and indexes if they do not already exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Activities Table: Granular logs captured at each monitoring tick
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    app_name TEXT NOT NULL,
                    window_title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    productivity_score REAL NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    is_idle INTEGER NOT NULL DEFAULT 0,
                    context_tag TEXT DEFAULT ''
                );
            """)

            # Fast index on timestamp for interval queries (e.g. filter by day/hour range)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activities_timestamp 
                ON activities(timestamp);
            """)

            # Index on category for rapid category filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activities_category 
                ON activities(category);
            """)

            # 2. Work Segments Table: Clustered similar activities forming coherent tasks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    primary_category TEXT NOT NULL,
                    context_title TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    activity_count INTEGER NOT NULL,
                    summary TEXT DEFAULT ''
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_segments_time 
                ON work_segments(start_time, end_time);
            """)

            # 3. Custom Categorization Rules: User-defined overrides
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL, -- 'app' or 'title'
                    pattern TEXT NOT NULL,      -- Substring or regex keyword
                    category TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

            # 4. Shareable Posts: Generated posts and updates
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shareable_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    tone TEXT NOT NULL,
                    content TEXT NOT NULL
                );
            """)

            # 5. App Settings: Persistent user preferences (e.g. auto_start_tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            # Default: auto_start_tracking = true
            cursor.execute("""
                INSERT OR IGNORE INTO app_settings (key, value)
                VALUES ('auto_start_tracking', 'true');
            """)

            # 6. User Profile Context: Goals, purpose, identity, and boundaries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    full_name TEXT DEFAULT '',
                    profession_role TEXT DEFAULT '',
                    purpose_why TEXT DEFAULT '',
                    short_term_goals TEXT DEFAULT '',
                    long_term_goals TEXT DEFAULT '',
                    things_to_avoid TEXT DEFAULT '',
                    extra_context TEXT DEFAULT '',
                    updated_at TEXT DEFAULT ''
                );
            """)

            cursor.execute("""
                INSERT OR IGNORE INTO user_profile 
                (id, full_name, profession_role, purpose_why, short_term_goals, long_term_goals, things_to_avoid, extra_context, updated_at)
                VALUES (1, '', '', '', '', '', '', '', datetime('now'));
            """)

            # 7. PC & Environment Telemetry Context
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pc_context (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    hostname TEXT DEFAULT '',
                    os_info TEXT DEFAULT '',
                    cpu_info TEXT DEFAULT '',
                    ram_info TEXT DEFAULT '',
                    display_info TEXT DEFAULT '',
                    python_env TEXT DEFAULT '',
                    updated_at TEXT DEFAULT ''
                );
            """)

            cursor.execute("""
                INSERT OR IGNORE INTO pc_context 
                (id, hostname, os_info, cpu_info, ram_info, display_info, python_env, updated_at)
                VALUES (1, '', '', '', '', '', '', datetime('now'));
            """)

            # 8. Learned Facts & Behavioral Memory over time
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learned_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    fact_text TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    learned_at TEXT NOT NULL
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_facts_category 
                ON learned_facts(category);
            """)

            # 9. Sprints Table: Meaningful, goal-oriented focused work episodes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sprint_name TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    focus_score REAL NOT NULL,
                    milestones_json TEXT DEFAULT '[]',
                    achievements_json TEXT DEFAULT '[]',
                    files_touched_json TEXT DEFAULT '[]',
                    tools_used_json TEXT DEFAULT '[]',
                    friction_points TEXT DEFAULT '',
                    ai_insight TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sprints_time 
                ON sprints(start_time, end_time);
            """)

            # 10. Insight Memory & History: Tracking strategic recommendations worked on
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS insight_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    insight_key TEXT UNIQUE,
                    project_name TEXT NOT NULL,
                    angle_title TEXT NOT NULL,
                    summary TEXT DEFAULT '',
                    recommendation TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed'
                    time_scope TEXT DEFAULT 'realtime',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT DEFAULT '',
                    notes TEXT DEFAULT ''
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_insight_key 
                ON insight_memory(insight_key);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_insight_proj 
                ON insight_memory(project_name);
            """)

            # Deep Snapshot Activity Migration (Add columns if upgrading existing DB)
            for col, col_type in [
                ("action_verb", "TEXT DEFAULT ''"),
                ("target_entity", "TEXT DEFAULT ''"),
                ("workflow_phase", "TEXT DEFAULT ''"),
                ("transition_type", "TEXT DEFAULT ''"),
                ("is_stuck", "INTEGER DEFAULT 0"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE activities ADD COLUMN {col} {col_type};")
                except sqlite3.OperationalError:
                    pass

            # Retroactive Migration: Ensure no historical records remain Uncategorized
            cursor.execute("""
                UPDATE activities 
                SET category = 'Work / Coding', productivity_score = 1.0 
                WHERE category = 'Uncategorized';
            """)
            cursor.execute("""
                UPDATE work_segments 
                SET primary_category = 'Work / Coding' 
                WHERE primary_category = 'Uncategorized';
            """)

            # Retroactive Migration: Correct media titles mistakenly marked as Communication
            cursor.execute("""
                UPDATE activities 
                SET category = 'Entertainment / Media', productivity_score = -0.5 
                WHERE (LOWER(window_title) LIKE '%youtube%' 
                       OR LOWER(window_title) LIKE '%sidemen%' 
                       OR LOWER(window_title) LIKE '%among us%' 
                       OR LOWER(window_title) LIKE '%twitch%')
                  AND category = 'Communication';
            """)

            conn.commit()

    def log_activity(
        self,
        app_name: str,
        window_title: str,
        category: str,
        productivity_score: float,
        duration_seconds: int,
        is_idle: bool = False,
        context_tag: str = "",
        timestamp: Optional[datetime.datetime] = None,
        action_verb: str = "",
        target_entity: str = "",
        workflow_phase: str = "",
        transition_type: str = "",
        is_stuck: bool = False,
    ) -> int:
        """
        Record an active window snapshot into the activities table.
        
        Args:
            app_name: Executable or process name (e.g., 'Code.exe').
            window_title: Window title text (e.g., 'main.py - Project').
            category: Assigned semantic category.
            productivity_score: Weight (-1.0 to 1.0).
            duration_seconds: Interval duration in seconds.
            is_idle: Flag indicating if user was inactive.
            context_tag: Optional cluster/project tag.
            timestamp: Explicit datetime or current UTC if None.
            action_verb: Granular human-readable action description.
            target_entity: Identified file, doc, or search term.
            workflow_phase: High-level category phase.
            transition_type: Context shift from previous snapshot.
            is_stuck: Cognitive friction / troubleshooting loop flag.
            
        Returns:
            The inserted row ID.
        """
        ts = (timestamp or datetime.datetime.now()).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO activities (
                    timestamp, app_name, window_title, category,
                    productivity_score, duration_seconds, is_idle, context_tag,
                    action_verb, target_entity, workflow_phase, transition_type, is_stuck
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    ts,
                    app_name,
                    window_title,
                    category,
                    productivity_score,
                    duration_seconds,
                    1 if is_idle else 0,
                    context_tag,
                    action_verb,
                    target_entity,
                    workflow_phase,
                    transition_type,
                    1 if is_stuck else 0,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_activities(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve individual activities within a given time range or latest records.
        
        Args:
            start_time: Optional ISO formatted start timestamp.
            end_time: Optional ISO formatted end timestamp.
            category: Optional category filter.
            limit: Maximum records to return.
            
        Returns:
            List of dictionaries representing activity records.
        """
        query = "SELECT * FROM activities WHERE 1=1"
        params: List[Any] = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        if category and category != "All":
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_category_summary(self, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        """
        Aggregate total duration and count grouped by category for visual chart generation.
        
        Args:
            start_time: ISO start timestamp.
            end_time: ISO end timestamp.
            
        Returns:
            List of dictionaries: [{'category': str, 'total_seconds': int, 'percent': float}]
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    category, 
                    SUM(duration_seconds) as total_seconds,
                    COUNT(*) as count
                FROM activities
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY category
                ORDER BY total_seconds DESC;
                """,
                (start_time, end_time),
            )
            rows = cursor.fetchall()

            total_seconds_all = sum(r["total_seconds"] for r in rows) or 1
            result = []
            for r in rows:
                result.append({
                    "category": r["category"],
                    "total_seconds": r["total_seconds"],
                    "count": r["count"],
                    "percent": round((r["total_seconds"] / total_seconds_all) * 100, 1),
                })
            return result

    def get_top_apps(self, start_time: str, end_time: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        Retrieve top applications by cumulative active duration.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    app_name, 
                    category,
                    SUM(duration_seconds) as total_seconds,
                    COUNT(*) as occurrences
                FROM activities
                WHERE timestamp >= ? AND timestamp <= ? AND is_idle = 0
                GROUP BY app_name
                ORDER BY total_seconds DESC
                LIMIT ?;
                """,
                (start_time, end_time, limit),
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_productivity_metrics(self, start_time: str, end_time: str) -> Dict[str, Any]:
        """
        Compute high-level summary metrics:
        - Overall Productivity Score (0% to 100%)
        - Total Time, Active Time, Idle Time
        - Most Used Category
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    SUM(duration_seconds) as total_seconds,
                    SUM(CASE WHEN is_idle = 0 THEN duration_seconds ELSE 0 END) as active_seconds,
                    SUM(CASE WHEN is_idle = 1 THEN duration_seconds ELSE 0 END) as idle_seconds,
                    SUM(CASE WHEN is_idle = 0 THEN productivity_score * duration_seconds ELSE 0 END) as weighted_score_sum
                FROM activities
                WHERE timestamp >= ? AND timestamp <= ?;
                """,
                (start_time, end_time),
            )
            summary = cursor.fetchone()

            total_seconds = summary["total_seconds"] or 0
            active_seconds = summary["active_seconds"] or 0
            idle_seconds = summary["idle_seconds"] or 0
            weighted_score_sum = summary["weighted_score_sum"] or 0.0

            # Normalized Score: Maps [-1.0, 1.0] to [0%, 100%]
            # Base formula: Score = ((average_weight + 1.0) / 2.0) * 100
            if active_seconds > 0:
                avg_weight = weighted_score_sum / active_seconds
                score_pct = max(0.0, min(100.0, ((avg_weight + 1.0) / 2.0) * 100.0))
            else:
                score_pct = 0.0

            return {
                "total_seconds": total_seconds,
                "active_seconds": active_seconds,
                "idle_seconds": idle_seconds,
                "productivity_score": round(score_pct, 1),
            }

    def save_work_segment(
        self,
        start_time: str,
        end_time: str,
        primary_category: str,
        context_title: str,
        duration_seconds: int,
        activity_count: int,
        summary: str = "",
    ) -> int:
        """Store a detected cohesive work segment/session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO work_segments (
                    start_time, end_time, primary_category, context_title,
                    duration_seconds, activity_count, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    start_time,
                    end_time,
                    primary_category,
                    context_title,
                    duration_seconds,
                    activity_count,
                    summary,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_work_segments(
        self, start_time: str, end_time: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve work segments within a given interval."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM work_segments
                WHERE start_time >= ? AND start_time <= ?
                ORDER BY start_time DESC
                LIMIT ?;
                """,
                (start_time, end_time, limit),
            )
            return [dict(r) for r in cursor.fetchall()]

    def save_shareable_post(
        self,
        start_time: str,
        end_time: str,
        tone: str,
        content: str,
    ) -> int:
        """Store a generated shareable post for history tracking."""
        created_at = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO shareable_posts (
                    created_at, start_time, end_time, tone, content
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (created_at, start_time, end_time, tone, content),
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_posts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch previously generated social posts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM shareable_posts
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]

    def add_custom_rule(self, pattern_type: str, pattern: str, category: str) -> int:
        """Add user-defined categorization rule."""
        created_at = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO custom_rules (pattern_type, pattern, category, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (pattern_type.lower(), pattern.strip().lower(), category, created_at),
            )
            conn.commit()
            return cursor.lastrowid

    def get_custom_rules(self) -> List[Dict[str, Any]]:
        """Retrieve all user-configured categorization rules."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM custom_rules ORDER BY id ASC;")
            return [dict(r) for r in cursor.fetchall()]

    def delete_custom_rule(self, rule_id: int) -> bool:
        """Remove a user categorization rule by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM custom_rules WHERE id = ?;", (rule_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_setting(self, key: str, default: str = "") -> str:
        """Retrieve a persistent setting value by key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?;", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Insert or update a persistent setting value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
                """,
                (key, str(value)),
            )
            conn.commit()

    # -------------------------------------------------------------
    # User Profile & Context Persistence
    # -------------------------------------------------------------
    def get_user_profile(self) -> Dict[str, str]:
        """Retrieve the user profile, personal goals, and work context."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profile WHERE id = 1;")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {
                "full_name": "",
                "profession_role": "",
                "purpose_why": "",
                "short_term_goals": "",
                "long_term_goals": "",
                "things_to_avoid": "",
                "extra_context": "",
                "updated_at": "",
            }

    def save_user_profile(self, data: Dict[str, str]) -> None:
        """Save or update user profile context."""
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_profile (
                    id, full_name, profession_role, purpose_why, 
                    short_term_goals, long_term_goals, things_to_avoid, 
                    extra_context, updated_at
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    full_name = excluded.full_name,
                    profession_role = excluded.profession_role,
                    purpose_why = excluded.purpose_why,
                    short_term_goals = excluded.short_term_goals,
                    long_term_goals = excluded.long_term_goals,
                    things_to_avoid = excluded.things_to_avoid,
                    extra_context = excluded.extra_context,
                    updated_at = excluded.updated_at;
                """,
                (
                    data.get("full_name", "").strip(),
                    data.get("profession_role", "").strip(),
                    data.get("purpose_why", "").strip(),
                    data.get("short_term_goals", "").strip(),
                    data.get("long_term_goals", "").strip(),
                    data.get("things_to_avoid", "").strip(),
                    data.get("extra_context", "").strip(),
                    now,
                ),
            )
            conn.commit()

    # -------------------------------------------------------------
    # PC & Environment Context Persistence
    # -------------------------------------------------------------
    def get_pc_context(self) -> Dict[str, str]:
        """Retrieve detected PC environment details."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pc_context WHERE id = 1;")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}

    def save_pc_context(self, data: Dict[str, str]) -> None:
        """Update PC environment telemetry."""
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO pc_context (
                    id, hostname, os_info, cpu_info, ram_info, display_info, python_env, updated_at
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    hostname = excluded.hostname,
                    os_info = excluded.os_info,
                    cpu_info = excluded.cpu_info,
                    ram_info = excluded.ram_info,
                    display_info = excluded.display_info,
                    python_env = excluded.python_env,
                    updated_at = excluded.updated_at;
                """,
                (
                    data.get("hostname", ""),
                    data.get("os_info", ""),
                    data.get("cpu_info", ""),
                    data.get("ram_info", ""),
                    data.get("display_info", ""),
                    data.get("python_env", ""),
                    now,
                ),
            )
            conn.commit()

    # -------------------------------------------------------------
    # Learned Facts & Behavioral Memory Persistence
    # -------------------------------------------------------------
    def get_learned_facts(self, limit: int = 50, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve memory observations learned by Minion over time."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category and category != "All":
                cursor.execute(
                    "SELECT * FROM learned_facts WHERE category = ? ORDER BY learned_at DESC LIMIT ?;",
                    (category, limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM learned_facts ORDER BY learned_at DESC LIMIT ?;",
                    (limit,),
                )
            return [dict(r) for r in cursor.fetchall()]

    def add_learned_fact(self, category: str, fact_text: str, confidence: float = 1.0) -> int:
        """Store a new learned observation or habit into Minion's memory."""
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO learned_facts (category, fact_text, confidence, learned_at)
                VALUES (?, ?, ?, ?);
                """,
                (category.strip(), fact_text.strip(), float(confidence), now),
            )
            conn.commit()
            return cursor.lastrowid

    def delete_learned_fact(self, fact_id: int) -> bool:
        """Remove a specific memory item by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM learned_facts WHERE id = ?;", (fact_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_learned_facts(self) -> None:
        """Clear all learned memory facts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM learned_facts;")
            conn.commit()

    # -------------------------------------------------------------
    # Sprints & Deep Behavioral Insights Persistence
    # -------------------------------------------------------------
    def get_activities_by_interval(
        self, start_time: str, end_time: str, limit: int = 10000
    ) -> List[Dict[str, Any]]:
        """Retrieve individual activities ordered chronologically within an interval."""
        return self.get_activities(start_time, end_time, limit=limit)

    def save_sprint(self, sprint: Dict[str, Any]) -> int:
        """
        Store a structured sprint record in SQLite.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sprints (
                    sprint_name, objective, start_time, end_time,
                    duration_seconds, focus_score, milestones_json,
                    achievements_json, files_touched_json, tools_used_json,
                    friction_points, ai_insight, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    sprint.get("sprint_name", "Untitled Sprint"),
                    sprint.get("objective", "Focused task execution"),
                    sprint.get("start_time", ""),
                    sprint.get("end_time", ""),
                    int(sprint.get("duration_seconds", 0)),
                    float(sprint.get("focus_score", 0.0)),
                    sprint.get("milestones_json", "[]"),
                    sprint.get("achievements_json", "[]"),
                    sprint.get("files_touched_json", "[]"),
                    sprint.get("tools_used_json", "[]"),
                    sprint.get("friction_points", ""),
                    sprint.get("ai_insight", ""),
                    sprint.get("created_at") or datetime.datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_sprints(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve saved sprints, optionally filtered by time window.
        """
        query = "SELECT * FROM sprints"
        params: List[Any] = []

        if start_time and end_time:
            query += " WHERE start_time >= ? AND end_time <= ?"
            params.extend([start_time, end_time])
        elif start_time:
            query += " WHERE start_time >= ?"
            params.append(start_time)

        query += " ORDER BY start_time DESC LIMIT ?;"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def get_latest_sprint(self) -> Optional[Dict[str, Any]]:
        """Retrieve the most recently completed or active sprint."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sprints ORDER BY start_time DESC LIMIT 1;"
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def clear_sprints(self) -> None:
        """Clear all sprint records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sprints;")
            conn.commit()

    # -------------------------------------------------------------
    # 10. Insight Memory & Historical Tracking
    # -------------------------------------------------------------
    def save_insight_status(
        self,
        insight_key: str,
        project_name: str,
        angle_title: str,
        summary: str = "",
        recommendation: str = "",
        status: str = "pending",
        time_scope: str = "realtime",
        notes: str = "",
    ) -> None:
        """
        Record or update the implementation status of a strategic insight.
        Status: 'pending' (to review), 'in_progress' (actively working), 'completed' (worked on).
        """
        now_iso = datetime.datetime.now().isoformat()
        completed_at = now_iso if status == "completed" else ""

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO insight_memory (
                    insight_key, project_name, angle_title, summary, recommendation,
                    status, time_scope, created_at, updated_at, completed_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(insight_key) DO UPDATE SET
                    status = excluded.status,
                    time_scope = excluded.time_scope,
                    updated_at = excluded.updated_at,
                    completed_at = CASE 
                        WHEN excluded.status = 'completed' THEN excluded.updated_at
                        ELSE insight_memory.completed_at
                    END,
                    notes = CASE WHEN excluded.notes != '' THEN excluded.notes ELSE insight_memory.notes END;
                """,
                (
                    insight_key,
                    project_name,
                    angle_title,
                    summary,
                    recommendation,
                    status,
                    time_scope,
                    now_iso,
                    now_iso,
                    completed_at,
                    notes,
                ),
            )
            conn.commit()

    def get_insight_statuses(self, project_name: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve a mapping of insight_key -> insight dictionary for active status lookups.
        """
        query = "SELECT * FROM insight_memory"
        params: List[Any] = []
        if project_name:
            query += " WHERE project_name = ?"
            params.append(project_name)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return {row["insight_key"]: dict(row) for row in rows}

    def get_insight_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve historical insights sorted by most recently updated or completed.
        """
        query = """
            SELECT * FROM insight_memory 
            ORDER BY updated_at DESC LIMIT ?
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, [limit])
            rows = cursor.fetchall()
            return [dict(row) for row in rows]



