"""
Sprint Clustering & Deep Insights Engine for Minion.

This module aggregates granular screen snapshots and deep activity transitions into
meaningful, goal-oriented "Sprints" (focused work episodes of 20-90 minutes).

It analyzes what the user accomplished across time:
1. Clusters activities into Sprints bounded by task continuity and natural breaks.
2. Identifies the primary Sprint Objective & Workspace Project.
3. Generates chronological Sprint Milestones from snapshot state transitions.
4. Synthesizes concrete achievements (files modified, tools used, tests verified).
5. Detects cognitive friction points (debugging loops, context switching, distractions).
6. Computes Focus & Flow State scores.
7. Feeds insights directly into Minion's learned memory and user profile context.
"""

import json
import datetime
from collections import Counter
from typing import List, Dict, Any, Optional

from core.database import DatabaseManager
from core.deep_analyzer import DeepSnapshotAnalyzer


class SprintEngine:
    """Detects, structures, and synthesizes work sprints and behavioural insights."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        ai_agent=None,
        context_manager=None,
    ):
        """
        Initialize the Sprint Engine.
        
        Args:
            db_manager: Database manager instance.
            ai_agent: Optional OllamaAgent for local LLM sprint synthesis.
            context_manager: Optional ContextManager to record learned facts.
        """
        self.db = db_manager
        self.ai = ai_agent
        self.context_manager = context_manager
        self.analyzer = DeepSnapshotAnalyzer()

    def generate_sprints(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        max_break_minutes: int = 15,
        save_to_db: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Query activities within the time window and cluster them into Sprints.
        
        Args:
            start_time: ISO timestamp string or None for today.
            end_time: ISO timestamp string or None for now.
            max_break_minutes: Idle/gap minutes that demarcate a sprint boundary.
            save_to_db: Whether to persist the generated sprints into the SQLite database.
            
        Returns:
            List of structured Sprint dictionaries.
        """
        if not start_time:
            now = datetime.datetime.now()
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        if not end_time:
            end_time = datetime.datetime.now().isoformat()

        activities = self.db.get_activities_by_interval(start_time, end_time)
        if not activities:
            return []

        # Sort activities chronologically
        activities = sorted(activities, key=lambda a: a["timestamp"])

        raw_sprints = self._cluster_activities_into_sprints(
            activities, max_break_seconds=max_break_minutes * 60
        )

        structured_sprints: List[Dict[str, Any]] = []

        for cluster in raw_sprints:
            sprint = self._synthesize_sprint_data(cluster)
            if sprint and sprint["duration_seconds"] >= 180:  # Ignore trivial micro-clusters < 3 mins
                structured_sprints.append(sprint)

        if save_to_db and structured_sprints:
            for s in structured_sprints:
                self.db.save_sprint(s)

            # Update Minion's learned facts and context memory
            self._update_learned_sprint_memory(structured_sprints)

        return structured_sprints

    def _cluster_activities_into_sprints(
        self,
        activities: List[Dict[str, Any]],
        max_break_seconds: int = 900,
    ) -> List[List[Dict[str, Any]]]:
        """Group activities into sprint clusters based on time gap and flow continuity."""
        clusters: List[List[Dict[str, Any]]] = []
        current_cluster: List[Dict[str, Any]] = [activities[0]]

        for i in range(1, len(activities)):
            prev = activities[i - 1]
            curr = activities[i]

            try:
                t_prev = datetime.datetime.fromisoformat(prev["timestamp"])
                t_curr = datetime.datetime.fromisoformat(curr["timestamp"])
                gap_seconds = (t_curr - t_prev).total_seconds()
            except Exception:
                gap_seconds = 0

            # Condition to break sprint:
            # 1. Extended idle gap or time break > max_break_seconds
            # 2. Transition from deep work into long sustained idle/away (> 10 mins)
            is_break = gap_seconds > max_break_seconds or (curr.get("is_idle", 0) and gap_seconds > 600)

            if is_break:
                clusters.append(current_cluster)
                current_cluster = [curr]
            else:
                current_cluster.append(curr)

        if current_cluster:
            clusters.append(current_cluster)

        return clusters

    def _synthesize_sprint_data(self, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesize deep entities, milestones, and achievements for a sprint cluster."""
        if not cluster:
            return {}

        start_time = cluster[0]["timestamp"]
        end_time = cluster[-1]["timestamp"]
        total_duration = sum(a.get("duration_seconds", 10) for a in cluster)

        # 1. Categorization and Flow Analysis
        active_duration = sum(
            a.get("duration_seconds", 10)
            for a in cluster
            if not a.get("is_idle", 0) and "Distraction" not in a.get("category", "")
        )
        distraction_duration = sum(
            a.get("duration_seconds", 10)
            for a in cluster
            if "Distraction" in a.get("category", "") or "Media" in a.get("category", "")
        )

        flow_score = round(
            max(0.0, min(100.0, (active_duration / max(1, total_duration)) * 100)), 1
        )

        # 2. Extract files, projects, searches, tools
        files_touched: List[str] = []
        projects: List[str] = []
        search_queries: List[str] = []
        tools: List[str] = []
        workflow_phases: List[str] = []
        stuck_loops: List[str] = []

        for a in cluster:
            app = a.get("app_name", "")
            title = a.get("window_title", "")
            if app and app not in tools:
                tools.append(app)

            parsed = self.analyzer.parse_snapshot_entities(app, title)
            if parsed["file_name"] and parsed["file_name"] not in files_touched:
                files_touched.append(parsed["file_name"])
            if parsed["project_name"] and parsed["project_name"] not in projects:
                projects.append(parsed["project_name"])
            if parsed["search_query"] and parsed["search_query"] not in search_queries:
                search_queries.append(parsed["search_query"])
            if parsed["workflow_phase"]:
                workflow_phases.append(parsed["workflow_phase"])

            if a.get("is_stuck", 0) or parsed.get("is_stuck", False):
                reason = a.get("stuck_reason") or "Debugging loop"
                if reason not in stuck_loops:
                    stuck_loops.append(reason)

        # 3. Determine Dominant Project & Sprint Name
        primary_project = projects[0] if projects else "General Workspace"
        top_tool = Counter(a.get("app_name", "") for a in cluster).most_common(1)[0][0]

        if files_touched:
            sprint_name = f"Sprint: {primary_project} ({', '.join(files_touched[:2])})"
            objective = f"Feature Implementation & Code Refinement in {primary_project}"
        elif search_queries:
            sprint_name = f"Research Sprint: {search_queries[0][:30]}"
            objective = f"Technical Discovery & Problem Solving on {search_queries[0]}"
        elif "Communication" in Counter(workflow_phases).most_common(1)[0][0]:
            sprint_name = f"Collaboration Sprint: {top_tool}"
            objective = "Team Communication & Planning Sync"
        else:
            sprint_name = f"Focus Sprint: {top_tool}"
            objective = f"Focused Task Execution in {top_tool}"

        # 4. Generate Chronological Milestones
        milestones = self._build_chronological_milestones(cluster)

        # 5. Extract Concrete Achievements
        achievements = self._extract_concrete_achievements(
            cluster, files_touched, projects, search_queries, total_duration, flow_score
        )

        # 6. Friction Points
        friction = []
        if stuck_loops:
            friction.extend(stuck_loops)
        if distraction_duration > 180:
            friction.append(
                f"Context switch into media/distraction for {distraction_duration // 60}m"
            )
        friction_points_str = "; ".join(friction) if friction else "Seamless flow with zero notable roadblocks"

        # 7. AI Insight Generation
        ai_insight = self._generate_sprint_insight(
            sprint_name=sprint_name,
            objective=objective,
            duration_minutes=total_duration // 60,
            flow_score=flow_score,
            files=files_touched,
            achievements=achievements,
            friction=friction_points_str,
        )

        return {
            "sprint_name": sprint_name,
            "objective": objective,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": total_duration,
            "focus_score": flow_score,
            "milestones_json": json.dumps(milestones),
            "achievements_json": json.dumps(achievements),
            "files_touched_json": json.dumps(files_touched),
            "tools_used_json": json.dumps(tools),
            "friction_points": friction_points_str,
            "ai_insight": ai_insight,
            "created_at": datetime.datetime.now().isoformat(),
        }

    def _build_chronological_milestones(
        self, cluster: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Group granular activities into 3-5 distinct progression milestones."""
        if not cluster:
            return []

        # Divide cluster into chunks (e.g. up to 5 phases)
        num_milestones = min(5, max(2, len(cluster) // 4))
        chunk_size = max(1, len(cluster) // num_milestones)

        milestones = []
        for i in range(0, len(cluster), chunk_size):
            chunk = cluster[i : i + chunk_size]
            if not chunk:
                continue

            chunk_time = chunk[0]["timestamp"].split("T")[-1][:5] if "T" in chunk[0]["timestamp"] else chunk[0]["timestamp"]
            
            # Determine dominant phase & action
            app_counts = Counter(a.get("app_name", "") for a in chunk)
            top_app = app_counts.most_common(1)[0][0]
            
            # Find representative action
            sample = chunk[len(chunk) // 2]
            parsed = self.analyzer.parse_snapshot_entities(sample.get("app_name", ""), sample.get("window_title", ""))
            
            milestones.append({
                "time": chunk_time,
                "phase": parsed["workflow_phase"],
                "action": parsed["action_verb"],
                "tool": top_app,
                "duration_min": max(1, sum(a.get("duration_seconds", 10) for a in chunk) // 60),
            })

        return milestones

    def _extract_concrete_achievements(
        self,
        cluster: List[Dict[str, Any]],
        files: List[str],
        projects: List[str],
        searches: List[str],
        total_duration: int,
        flow_score: float,
    ) -> List[str]:
        """Formulate concrete achievement bullet points."""
        achievements = []

        dur_min = total_duration // 60
        if files:
            file_str = ", ".join(f"`{f}`" for f in files[:4])
            proj_str = f" in {projects[0]}" if projects else ""
            achievements.append(f"Authored and edited {len(files)} files ({file_str}){proj_str}.")

        if searches:
            achievements.append(f"Researched key technical topics including: '{searches[0]}'.")

        terminal_acts = [a for a in cluster if "powershell" in a.get("app_name", "").lower() or "cmd" in a.get("app_name", "").lower()]
        if terminal_acts:
            achievements.append("Executed verification tests and commands in the terminal environment.")

        if flow_score >= 85:
            achievements.append(f"Maintained an exceptional flow state of {flow_score}% focus over {dur_min} minutes.")
        else:
            achievements.append(f"Logged {dur_min} minutes of mixed work and task exploration.")

        return achievements

    def _generate_sprint_insight(
        self,
        sprint_name: str,
        objective: str,
        duration_minutes: int,
        flow_score: float,
        files: List[str],
        achievements: List[str],
        friction: str,
    ) -> str:
        """Generate high-level Minion behavioral summary, optionally with Ollama."""
        # 1. Try local Ollama if available
        if self.ai and self.ai.is_available():
            prompt = (
                f"You are Minion, an intelligent and encouraging productivity assistant. "
                f"Analyze this completed work sprint and provide a crisp 2-3 sentence insight into what the user achieved, "
                f"their velocity, and how they handled flow/distractions.\n\n"
                f"Sprint: {sprint_name}\n"
                f"Objective: {objective}\n"
                f"Duration: {duration_minutes} minutes\n"
                f"Flow Score: {flow_score}%\n"
                f"Files Modified: {', '.join(files) if files else 'None'}\n"
                f"Achievements: {'; '.join(achievements)}\n"
                f"Friction / Roadblocks: {friction}\n\n"
                f"Keep your tone sharp, helpful, and appreciative of their hard work."
            )
            try:
                insight = self.ai.generate_post(prompt, tone="Technical / Devlog")
                if insight and len(insight.strip()) > 30:
                    return insight.strip()
            except Exception:
                pass

        # 2. Rule-Based Fallback Synthesis
        if flow_score >= 85:
            return (
                f"Bello! High-velocity sprint detected on '{sprint_name}'. "
                f"You maintained a sharp {flow_score}% flow state across {duration_minutes} minutes, "
                f"successfully touching {len(files)} files with minimal distraction. Excellent deep work cadence!"
            )
        else:
            return (
                f"Completed {duration_minutes}-minute work cycle on '{sprint_name}'. "
                f"Recorded a {flow_score}% focus score with intermittent context transitions. "
                f"Primary milestone achieved: {achievements[0] if achievements else objective}."
            )

    def _update_learned_sprint_memory(self, sprints: List[Dict[str, Any]]) -> None:
        """Feed sprint accomplishments into Minion's long-term memory facts."""
        for s in sprints:
            files = json.loads(s.get("files_touched_json", "[]"))
            flow = s.get("focus_score", 0.0)
            dur = s.get("duration_seconds", 0) // 60

            fact_content = (
                f"Completed {dur}m sprint '{s.get('sprint_name')}' with {flow}% focus. "
                f"Key files: {', '.join(files[:3]) if files else 'Exploration'}."
            )
            self.db.add_learned_fact(
                category="sprint_achievement",
                fact_text=fact_content,
                confidence=0.9,
            )
