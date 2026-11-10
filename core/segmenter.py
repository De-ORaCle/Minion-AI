"""
Context Segmentation & Work Session Clustering Engine for ProductivityCheck.

This module clusters granular screen activity logs into cohesive "Work Segments".
For example, switching between an IDE, documentation tabs, and terminal commands
while working on the same repository is merged into a single logical session:
"Developing ProductivityCheck Feature".

Architectural Rationale:
- Real-world productivity is rarely spent inside a single isolated window.
- Raw activity logs are too fragmented for human review and social sharing.
- This engine performs temporal proximity grouping, title similarity analysis,
  and context synthesis, with optional offline LLM summarization.
"""

import re
from typing import List, Dict, Any, Optional
from collections import Counter


class ContextSegmenter:
    """Clusters and labels work activities by context, similarity, and temporal continuity."""

    def __init__(self, ai_agent=None):
        """
        Initialize the segmenter.
        
        Args:
            ai_agent: Optional OllamaAgent for semantic session titling and summarization.
        """
        self.ai_agent = ai_agent

    def segment_activities(
        self,
        activities: List[Dict[str, Any]],
        max_break_seconds: int = 300,
    ) -> List[Dict[str, Any]]:
        """
        Partition a chronological list of activity logs into coherent work sessions.

        Args:
            activities: List of activity dictionaries, ordered chronologically.
            max_break_seconds: Max idle/gap time before splitting into a new segment.

        Returns:
            List of segmented sessions with context titles, durations, and summaries.
        """
        if not activities:
            return []

        # Sort activities chronologically by timestamp
        sorted_acts = sorted(activities, key=lambda a: a["timestamp"])
        segments: List[Dict[str, Any]] = []

        current_cluster: List[Dict[str, Any]] = [sorted_acts[0]]

        for i in range(1, len(sorted_acts)):
            prev_act = sorted_acts[i - 1]
            curr_act = sorted_acts[i]

            # Condition 1: Category consistency (e.g., Work vs Entertainment)
            same_category_family = self._are_compatible_categories(
                prev_act["category"], curr_act["category"]
            )

            # Condition 2: Idle transition
            idle_transition = (prev_act.get("is_idle", 0) != curr_act.get("is_idle", 0))

            # Condition 3: Contextual keyword overlap
            sim_score = self._compute_title_similarity(
                prev_act["window_title"], curr_act["window_title"]
            )

            # If compatible and not a stark idle break, keep in current cluster
            if same_category_family and not idle_transition and (sim_score > 0.15 or prev_act["category"] == curr_act["category"]):
                current_cluster.append(curr_act)
            else:
                # Seal current cluster and start new one
                segment = self._create_segment_summary(current_cluster)
                if segment["duration_seconds"] >= 10:  # Filter out trivial micro-switches
                    segments.append(segment)
                current_cluster = [curr_act]

        # Final cluster
        if current_cluster:
            segment = self._create_segment_summary(current_cluster)
            if segment["duration_seconds"] >= 10:
                segments.append(segment)

        return segments

    def _are_compatible_categories(self, cat1: str, cat2: str) -> bool:
        """Determine if two categories can co-exist within the same work context."""
        if cat1 == cat2:
            return True

        # Work and Learning/Research frequently complement each other (e.g. coding + reading docs)
        work_synergy = {"Work / Coding", "Learning / Research", "Utilities / System"}
        if cat1 in work_synergy and cat2 in work_synergy:
            return True

        return False

    def _extract_keywords(self, text: str) -> set:
        """Extract meaningful alphanumeric tokens from window titles, removing noise."""
        if not text:
            return set()
        clean = re.sub(r"[^\w\s-]", " ", text.lower())
        tokens = clean.split()
        stopwords = {
            "the", "and", "or", "to", "in", "a", "of", "for", "on", "with",
            "at", "by", "from", "google", "chrome", "edge", "visual", "studio",
            "code", "window", "tab", "document", "untitled"
        }
        return {t for t in tokens if len(t) > 2 and t not in stopwords}

    def _compute_title_similarity(self, title1: str, title2: str) -> float:
        """Compute Jaccard similarity between title keyword sets."""
        kw1 = self._extract_keywords(title1)
        kw2 = self._extract_keywords(title2)
        if not kw1 or not kw2:
            return 0.0
        intersection = kw1.intersection(kw2)
        union = kw1.union(kw2)
        return len(intersection) / len(union) if union else 0.0

    def _create_segment_summary(self, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesize a structured segment dictionary from a group of activities."""
        start_time = cluster[0]["timestamp"]
        end_time = cluster[-1]["timestamp"]
        total_duration = sum(a.get("duration_seconds", 10) for a in cluster)
        activity_count = len(cluster)

        # Determine dominant category
        cat_counts = Counter(a["category"] for a in cluster)
        primary_category = cat_counts.most_common(1)[0][0]

        # Extract top application
        app_counts = Counter(a["app_name"] for a in cluster)
        top_app = app_counts.most_common(1)[0][0]

        # Extract dominant context keywords
        all_kw: List[str] = []
        for a in cluster:
            all_kw.extend(self._extract_keywords(a["window_title"]))

        kw_counts = Counter(all_kw)
        top_keywords = [kw for kw, _ in kw_counts.most_common(3)]
        kw_str = ", ".join(top_keywords) if top_keywords else top_app

        # Construct context title
        if primary_category == "Work / Coding":
            context_title = f"Development Session: {kw_str.title()} ({top_app})"
        elif primary_category == "Learning / Research":
            context_title = f"Research & Study: {kw_str.title()}"
        elif primary_category == "Communication":
            context_title = f"Collaboration & Messaging: {top_app}"
        elif primary_category == "Idle / Away":
            context_title = f"Away / Workstation Inactive"
        else:
            context_title = f"{primary_category}: {kw_str.title()}"

        # High-level summary string
        summary = (
            f"Focused on {primary_category} for {total_duration // 60}m {total_duration % 60}s. "
            f"Primary tool: {top_app}. Key topics: {kw_str}."
        )

        return {
            "start_time": start_time,
            "end_time": end_time,
            "primary_category": primary_category,
            "context_title": context_title,
            "duration_seconds": total_duration,
            "activity_count": activity_count,
            "summary": summary,
            "top_app": top_app,
        }
