"""
Automated Unit & Integration Tests for ProductivityCheck Core Modules.

Tests:
- DatabaseManager table creation, activity logging, aggregations.
- CategorizationEngine heuristic pattern matching and custom user rules.
- ContextSegmenter work clustering and context labeling.
- ProductivityReporter figure generation and metrics computation.
- SharePostGenerator post synthesis and archiving.
- OllamaAgent connection diagnostics.
"""

import os
import shutil
import tempfile
import unittest
import datetime
import json

from core.database import DatabaseManager
from core.categorizer import CategorizationEngine
from core.segmenter import ContextSegmenter
from core.reporter import ProductivityReporter
from core.ai_agent import OllamaAgent
from core.share_generator import SharePostGenerator
from core.context_manager import ContextManager
from core.pc_info import get_system_telemetry
from core.deep_analyzer import DeepSnapshotAnalyzer
from core.sprint_engine import SprintEngine


class TestProductivityCore(unittest.TestCase):
    def setUp(self):
        """Set up an isolated temporary database for test runs."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_productivity.db")
        self.db = DatabaseManager(self.db_path)
        self.ai = OllamaAgent()
        self.categorizer = CategorizationEngine(db_manager=self.db, ai_agent=self.ai)
        self.segmenter = ContextSegmenter(ai_agent=self.ai)
        self.reporter = ProductivityReporter(self.db)
        self.share_gen = SharePostGenerator(self.db, self.segmenter, self.ai)
        self.context_manager = ContextManager(self.db)
        self.analyzer = DeepSnapshotAnalyzer()
        self.sprint_engine = SprintEngine(self.db, ai_agent=self.ai, context_manager=self.context_manager)

    def tearDown(self):
        """Clean up temporary test files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_logging_and_metrics(self):
        """Test logging activities and computing aggregated productivity metrics."""
        now = datetime.datetime.now()
        t1 = (now - datetime.timedelta(minutes=10)).isoformat()
        t2 = (now - datetime.timedelta(minutes=5)).isoformat()

        # Log 1: Coding (Productive)
        self.db.log_activity(
            app_name="Code.exe",
            window_title="main.py - ProductivityCheck",
            category="Work / Coding",
            productivity_score=1.0,
            duration_seconds=300,
            is_idle=False,
            timestamp=now - datetime.timedelta(minutes=10),
        )

        # Log 2: Research (Learning)
        self.db.log_activity(
            app_name="chrome.exe",
            window_title="Python Documentation - SQLite",
            category="Learning / Research",
            productivity_score=0.8,
            duration_seconds=300,
            is_idle=False,
            timestamp=now - datetime.timedelta(minutes=5),
        )

        # Test metrics calculation
        metrics = self.db.get_productivity_metrics(
            start_time=(now - datetime.timedelta(minutes=15)).isoformat(),
            end_time=(now + datetime.timedelta(minutes=1)).isoformat(),
        )

        self.assertEqual(metrics["total_seconds"], 600)
        self.assertEqual(metrics["active_seconds"], 600)
        self.assertEqual(metrics["idle_seconds"], 0)
        # Average weight is (1.0 * 300 + 0.8 * 300) / 600 = 0.9
        # Normalized score: ((0.9 + 1.0) / 2.0) * 100 = 95.0%
        self.assertAlmostEqual(metrics["productivity_score"], 95.0, places=1)

    def test_app_settings(self):
        """Test persistent settings key-value retrieval and updates."""
        # Default value test
        val = self.db.get_setting("auto_start_tracking", default="true")
        self.assertEqual(val, "true")

        # Update setting
        self.db.set_setting("auto_start_tracking", "false")
        updated = self.db.get_setting("auto_start_tracking")
        self.assertEqual(updated, "false")

    def test_context_and_import_export(self):
        """Test user profile context saving, JSON/Markdown import and export."""
        # 1. Profile persistence
        self.db.save_user_profile({
            "full_name": "Test Alex",
            "profession_role": "Backend Engineer",
            "purpose_why": "Build scalable backends",
            "short_term_goals": "Finish API documentation",
            "long_term_goals": "Master distributed systems",
            "things_to_avoid": "YouTube gaming during work",
            "extra_context": "Uses Windows and Python 3.12",
        })
        p = self.db.get_user_profile()
        self.assertEqual(p["full_name"], "Test Alex")
        self.assertEqual(p["profession_role"], "Backend Engineer")

        # 2. Export to JSON
        json_path = os.path.join(self.temp_dir, "test_context.json")
        self.context_manager.export_to_file(json_path)
        self.assertTrue(os.path.exists(json_path))

        # 3. Import from JSON with modifications
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["full_name"] = "Imported Alex"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        self.context_manager.import_from_file(json_path)
        p_reimported = self.db.get_user_profile()
        self.assertEqual(p_reimported["full_name"], "Imported Alex")

        # 4. Prompt context formatting
        prompt_block = self.context_manager.format_prompt_context()
        self.assertIn("Imported Alex", prompt_block)
        self.assertIn("Backend Engineer", prompt_block)

        # 5. Learned facts
        self.db.add_learned_fact("work_habit", "Observed peak focus in Code.exe")
        facts = self.db.get_learned_facts()
        self.assertEqual(len(facts), 1)
        self.assertIn("Observed peak focus", facts[0]["fact_text"])

    def test_memory_synthesizer_knowledge_graph(self):
        """Test synthesizing focus archetype, projects, tech stack, hobbies, and goal alignment."""
        now = datetime.datetime.now()

        # Log sample activities representing multi-project work and hobbies
        self.db.log_activity(
            app_name="Code.exe",
            window_title="chat_view.py - ProductivityCheck - Visual Studio Code",
            category="Work / Coding",
            productivity_score=1.0,
            duration_seconds=600,
            timestamp=now - datetime.timedelta(minutes=30),
        )
        self.db.log_activity(
            app_name="chrome.exe",
            window_title="Vestitude Partners Limited - Internal System - Google Chrome",
            category="Work / Coding",
            productivity_score=1.0,
            duration_seconds=600,
            timestamp=now - datetime.timedelta(minutes=20),
        )
        self.db.log_activity(
            app_name="Spotify.exe",
            window_title="Ludovico Einaudi - Nuvole Bianche - Spotify",
            category="Entertainment / Media",
            productivity_score=-0.2,
            duration_seconds=300,
            timestamp=now - datetime.timedelta(minutes=10),
        )

        res = self.context_manager.synthesize_deep_memory()

        # Verify Archetype
        self.assertIn("archetype_name", res["focus_style"])
        self.assertIn("peak_window", res["focus_style"])

        # Verify Projects
        proj_names = [p["name"] for p in res["projects_data"]["projects"]]
        self.assertTrue(any("Minion" in name or "ProductivityCheck" in name or "Vestitude" in name for name in proj_names))

        # Verify Tech Stack
        self.assertTrue(any(t in res["projects_data"]["tech_stack"] for t in ["Python", "React JSX", "JavaScript"]))

        # Verify Lifestyle
        self.assertGreater(len(res["lifestyle_data"]["music_tracks"]), 0)

        # Verify Goal Alignment
        self.assertIn("alignment_percentage", res["goal_alignment"])
        self.assertGreater(res["goal_alignment"]["alignment_percentage"], 0)

    def test_categorization_heuristics(self):
        """Test rule-based classification against development, communication, and media."""
        # IDE test
        cat, weight = self.categorizer.classify("Code.exe", "app.py - Visual Studio Code")
        self.assertEqual(cat, "Work / Coding")
        self.assertEqual(weight, 1.0)

        # Learning test
        cat, weight = self.categorizer.classify("chrome.exe", "Stack Overflow - Python threading questions")
        self.assertEqual(cat, "Learning / Research")
        self.assertEqual(weight, 0.8)

        # Communication test
        cat, weight = self.categorizer.classify("slack.exe", "general - Slack")
        self.assertEqual(cat, "Communication")
        self.assertEqual(weight, 0.5)

        # Entertainment test
        cat, weight = self.categorizer.classify("msedge.exe", "YouTube - Tech Documentary")
        self.assertEqual(cat, "Entertainment / Media")
        self.assertEqual(weight, -0.5)

        # Idle test
        cat, weight = self.categorizer.classify("Code.exe", "app.py", is_idle=True)
        self.assertEqual(cat, "Idle / Away")
        self.assertEqual(weight, 0.0)

        # Minion AI / ProductivityCheck window test (Observing Minion AI app itself is Utilities / System, NOT work)
        cat, weight = self.categorizer.classify(
            "python.exe", "ProductivityCheck — On-Screen Productivity Intelligence"
        )
        self.assertEqual(cat, "Utilities / System")
        self.assertEqual(weight, 0.0)

        # Unknown active window (Smart fallback: Never Uncategorized)
        cat, weight = self.categorizer.classify("novel_app_123.exe", "Drafting Report")
        self.assertEqual(cat, "Work / Coding")
        self.assertNotEqual(cat, "Uncategorized")

        # Unknown browser tab (Smart fallback: Learning / Research)
        cat, weight = self.categorizer.classify("chrome.exe", "Reading Interesting Topic")
        self.assertEqual(cat, "Learning / Research")

        # YouTube video with 'CHAT' in the title (Should be Entertainment / Media, NOT Communication)
        cat, weight = self.categorizer.classify(
            "chrome.exe", "SIDEMEN AMONG US PROXIMITY CHAT: SHAPESHIFTER SPECIAL - YouTube - Google Chrome"
        )
        self.assertEqual(cat, "Entertainment / Media")
        self.assertEqual(weight, -0.5)

    def test_custom_user_rule_override(self):
        """Test that user-defined rules take precedence over heuristics."""
        # Add custom rule: map 'customapp.exe' to 'Work / Coding'
        self.db.add_custom_rule(pattern_type="app", pattern="customapp.exe", category="Work / Coding")
        self.categorizer.clear_cache()

        cat, weight = self.categorizer.classify("customapp.exe", "Some Random Window Title")
        self.assertEqual(cat, "Work / Coding")
        self.assertEqual(weight, 1.0)

    def test_context_segmentation(self):
        """Test clustering consecutive related window activities into a single work session."""
        now = datetime.datetime.now()
        activities = [
            {
                "timestamp": (now - datetime.timedelta(minutes=8)).isoformat(),
                "app_name": "Code.exe",
                "window_title": "ProductivityCheck - models.py",
                "category": "Work / Coding",
                "duration_seconds": 60,
                "is_idle": 0,
            },
            {
                "timestamp": (now - datetime.timedelta(minutes=6)).isoformat(),
                "app_name": "chrome.exe",
                "window_title": "ProductivityCheck GitHub Pull Request",
                "category": "Work / Coding",
                "duration_seconds": 60,
                "is_idle": 0,
            },
            {
                "timestamp": (now - datetime.timedelta(minutes=4)).isoformat(),
                "app_name": "wt.exe",
                "window_title": "ProductivityCheck Terminal",
                "category": "Work / Coding",
                "duration_seconds": 60,
                "is_idle": 0,
            },
        ]

        segments = self.segmenter.segment_activities(activities)
        self.assertEqual(len(segments), 1)
        seg = segments[0]
        self.assertEqual(seg["primary_category"], "Work / Coding")
        self.assertIn("Productivitycheck", seg["context_title"])
        self.assertEqual(seg["duration_seconds"], 180)

    def test_reporter_charts(self):
        """Test that reporter produces valid Matplotlib figure instances."""
        now = datetime.datetime.now()
        start = (now - datetime.timedelta(hours=2)).isoformat()
        end = now.isoformat()

        # Generate category chart (empty state)
        fig1 = self.reporter.generate_category_chart(start, end)
        self.assertIsNotNone(fig1)

        # Generate top apps chart (empty state)
        fig2 = self.reporter.generate_top_apps_chart(start, end)
        self.assertIsNotNone(fig2)

    def test_share_post_generation(self):
        """Test generating shareable social posts."""
        now = datetime.datetime.now()
        start = (now - datetime.timedelta(hours=1)).isoformat()
        end = now.isoformat()

        self.db.log_activity(
            app_name="Code.exe",
            window_title="feature.py - Project",
            category="Work / Coding",
            productivity_score=1.0,
            duration_seconds=1800,
            is_idle=False,
            timestamp=now - datetime.timedelta(minutes=30),
        )

        res = self.share_gen.generate_post_for_interval(
            start_time=start,
            end_time=end,
            tone="Professional (LinkedIn)",
            interval_label="This Afternoon",
        )

        self.assertIn("content", res)
        self.assertGreater(len(res["content"]), 40)
        self.assertGreater(res["post_id"], 0)

    def test_ai_chat_with_work_context(self):
        """Test natural language chat querying about user productivity telemetry."""
        now = datetime.datetime.now()
        self.db.log_activity(
            app_name="Code.exe",
            window_title="minion_engine.py - Minion",
            category="Work / Coding",
            productivity_score=1.0,
            duration_seconds=900,
            is_idle=False,
            timestamp=now - datetime.timedelta(minutes=15),
        )

        reply = self.ai.chat_with_work_context(
            user_query="What did I work on today?",
            db_manager=self.db,
        )

        self.assertIsInstance(reply, str)
        self.assertGreater(len(reply), 30)

    def test_deep_snapshot_analyzer(self):
        """Test entity parsing, unsaved marker detection, and state transition analysis."""
        analyzer = DeepSnapshotAnalyzer()

        # 1. Test parsing IDE title with unsaved marker
        parsed = analyzer.parse_snapshot_entities(
            app_name="Code.exe",
            window_title="● chat_view.py - ProductivityCheck - Visual Studio Code",
        )
        self.assertEqual(parsed["file_name"], "chat_view.py")
        self.assertEqual(parsed["file_language"], "Python")
        self.assertEqual(parsed["project_name"], "ProductivityCheck")
        self.assertTrue(parsed["is_dirty"])
        self.assertIn("Editing chat_view.py", parsed["action_verb"])

        # 2. Test transition from Research to Implementation
        snap1 = {
            "app_name": "chrome.exe",
            "window_title": "sqlite3 python docs - Google Search",
            "is_idle": False,
        }
        res1 = analyzer.analyze_and_compare(snap1, None)
        self.assertEqual(res1["workflow_phase"], "Research & Exploration")

        snap2 = {
            "app_name": "Code.exe",
            "window_title": "database.py - ProductivityCheck - Visual Studio Code",
            "is_idle": False,
        }
        res2 = analyzer.analyze_and_compare(snap2, res1)
        self.assertEqual(res2["transition_type"], "Research to Implementation")
        self.assertIn("database.py", res2["deep_insight"])

    def test_sprint_engine_clustering_and_insights(self):
        """Test clustering activities into goal-oriented Sprints with milestones and achievements."""
        now = datetime.datetime.now()

        # Simulate a 45-minute focused sprint on database refactoring
        for i in range(9):
            ts = now - datetime.timedelta(minutes=45 - (i * 5))
            if i < 2:
                # Step 1: Research
                self.db.log_activity(
                    app_name="chrome.exe",
                    window_title="sqlite3 schema python docs - Google Search",
                    category="Learning / Research",
                    productivity_score=0.8,
                    duration_seconds=300,
                    timestamp=ts,
                    action_verb="Researching SQLite schema",
                    workflow_phase="Research & Exploration",
                )
            elif i < 7:
                # Step 2: Implementation
                self.db.log_activity(
                    app_name="Code.exe",
                    window_title="database.py - ProductivityCheck - Visual Studio Code",
                    category="Work / Coding",
                    productivity_score=1.0,
                    duration_seconds=300,
                    timestamp=ts,
                    action_verb="Editing database.py",
                    workflow_phase="Coding / Implementation",
                )
            else:
                # Step 3: Terminal verification
                self.db.log_activity(
                    app_name="powershell.exe",
                    window_title="Windows PowerShell - python -m unittest",
                    category="Work / Coding",
                    productivity_score=1.0,
                    duration_seconds=300,
                    timestamp=ts,
                    action_verb="Running unit tests",
                    workflow_phase="Verification & CLI",
                )

        start_iso = (now - datetime.timedelta(hours=1)).isoformat()
        end_iso = (now + datetime.timedelta(minutes=5)).isoformat()

        # Generate sprints
        sprints = self.sprint_engine.generate_sprints(start_iso, end_iso, save_to_db=True)
        self.assertGreaterEqual(len(sprints), 1)

        s = sprints[0]
        self.assertIn("Sprint", s["sprint_name"])
        self.assertGreater(s["duration_seconds"], 1800)
        self.assertGreaterEqual(s["focus_score"], 80.0)

        # Verify achievements and milestones
        milestones = json.loads(s["milestones_json"])
        self.assertGreaterEqual(len(milestones), 2)

        achievements = json.loads(s["achievements_json"])
        self.assertGreaterEqual(len(achievements), 1)

        # Verify persistence in SQLite
        saved_sprints = self.db.get_sprints(start_iso, end_iso)
        self.assertGreaterEqual(len(saved_sprints), 1)
        self.assertEqual(saved_sprints[0]["sprint_name"], s["sprint_name"])

        # Test querying AI about sprints
        reply = self.ai.chat_with_work_context(
            user_query="What did I achieve in my latest work sprint?",
            db_manager=self.db,
        )
        self.assertIn("Sprint", reply)
        self.assertTrue(any(w in reply.lower() for w in ["accomplish", "achieve", "success", "progress", "completed"]))


if __name__ == "__main__":
    unittest.main()
