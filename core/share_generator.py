"""
Shareable Post Generation Engine for ProductivityCheck.

This module coordinates between the database, context segmenter, and the AI agent
to transform raw activity intervals into shareable social updates, team standups,
and devlogs.

Architectural Rationale:
- Users want to showcase what they've built without manually typing out daily logs.
- By pulling the real work segments and productivity metrics from the database,
  the synthesized posts are authentic, quantified, and verifiable.
- Generated posts are archived in SQLite for future reference and continuous portfolio tracking.
"""

from typing import Dict, Any, List, Optional
from core.database import DatabaseManager
from core.segmenter import ContextSegmenter
from core.ai_agent import OllamaAgent


class SharePostGenerator:
    """Creates polished social media and team updates from tracked productivity intervals."""

    TONES = [
        "Professional (LinkedIn)",
        "Executive Summary (Leadership)",
        "Creative & Editorial Log",
        "Developer / Technical (X/Twitter)",
        "Team Standup (Slack/Teams)",
        "Casual Work Journal",
    ]

    def __init__(
        self,
        db_manager: DatabaseManager,
        segmenter: ContextSegmenter,
        ai_agent: OllamaAgent,
    ):
        """
        Initialize the post generator.

        Args:
            db_manager: Database manager to fetch interval logs.
            segmenter: Context segmenter to cluster activities into milestones.
            ai_agent: Ollama local AI agent for synthesis.
        """
        self.db = db_manager
        self.segmenter = segmenter
        self.ai = ai_agent

    def generate_post_for_interval(
        self,
        start_time: str,
        end_time: str,
        tone: str = "Professional (LinkedIn)",
        interval_label: str = "Today",
        custom_note: str = "",
    ) -> Dict[str, Any]:
        """
        Synthesize a shareable post based on activities within the given interval.

        Args:
            start_time: ISO start timestamp.
            end_time: ISO end timestamp.
            tone: One of the supported tone options.
            interval_label: Text label describing the period (e.g. 'This Afternoon').
            custom_note: Optional extra context or milestone note provided by the user.

        Returns:
            Dictionary containing:
            - 'content': str
            - 'post_id': int
            - 'char_count': int
            - 'segment_count': int
            - 'score': float
        """
        # 1. Fetch raw activities
        activities = self.db.get_activities(start_time, end_time, limit=5000)

        # 2. Compute metrics
        metrics = self.db.get_productivity_metrics(start_time, end_time)

        # 3. Cluster activities into work segments
        segments = self.segmenter.segment_activities(activities)

        # 4. Generate post text via AI agent (or fallback)
        domain_key = self.db.get_setting("user_focus_domain", "general")
        post_text = self.ai.generate_shareable_post(
            summary_stats=metrics,
            segments=segments,
            tone=tone,
            interval_desc=interval_label,
            domain_key=domain_key,
        )

        # Append custom note if provided
        if custom_note.strip():
            post_text += f"\n\n💡 Focus Note: {custom_note.strip()}"

        # 5. Persist to database history
        post_id = self.db.save_shareable_post(
            start_time=start_time,
            end_time=end_time,
            tone=tone,
            content=post_text,
        )

        return {
            "content": post_text,
            "post_id": post_id,
            "char_count": len(post_text),
            "segment_count": len(segments),
            "score": metrics.get("productivity_score", 0.0),
        }
