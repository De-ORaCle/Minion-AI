"""
Productivity Metrics, Visualization & Reporting Engine for ProductivityCheck.

This module processes raw database logs to generate:
1. Matplotlib charts (Category Donut Chart, Hourly Productivity Breakdown).
2. Time-filtered summary statistics (Active time, Idle time, Normalized Productivity Index).
3. Data exports (CSV and JSON) for external reporting and personal journaling.

Architectural Rationale:
- Matplotlib figures are configured with a sleek dark-theme palette (#1e1e2e / #2b2b3b)
  to blend seamlessly into the CustomTkinter desktop interface.
- Thread-safe figure generation: Figures are created using the non-interactive Agg canvas,
  preventing GUI freezing during chart rendering.
"""

from __future__ import annotations
import os
import csv
import json
import datetime
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
import customtkinter as ctk

if TYPE_CHECKING:
    from matplotlib.figure import Figure

from config import CATEGORY_CONFIG
from core.database import DatabaseManager

_FigureClass = None

def _get_figure_class():
    """Lazily load Matplotlib Figure class only when chart rendering is requested."""
    global _FigureClass
    if _FigureClass is None:
        import matplotlib
        matplotlib.use("Agg")  # Non-blocking headless backend for Tkinter
        from matplotlib.figure import Figure
        _FigureClass = Figure
    return _FigureClass


class ProductivityReporter:
    """Calculates metrics, renders charts, and exports productivity data."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize reporter with database manager reference.
        
        Args:
            db_manager: DatabaseManager instance.
        """
        self.db = db_manager

    def get_time_interval_bounds(self, interval_preset: str) -> Tuple[str, str]:
        """
        Convert user-friendly interval presets into ISO start and end timestamp strings.

        Presets:
        - 'Today': Midnight today to now.
        - 'Yesterday': Midnight yesterday to end of yesterday.
        - 'Past 7 Days': 7 days ago to now.
        - 'Past 30 Days': 30 days ago to now.
        - 'Past 1 Hour': 1 hour ago to now.
        - 'Past 4 Hours': 4 hours ago to now.
        """
        now = datetime.datetime.now()

        if interval_preset == "Today":
            start = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
            end = now
        elif interval_preset == "Yesterday":
            yesterday = now - datetime.timedelta(days=1)
            start = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
            end = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
        elif interval_preset == "Past 7 Days":
            start = now - datetime.timedelta(days=7)
            end = now
        elif interval_preset == "Past 30 Days":
            start = now - datetime.timedelta(days=30)
            end = now
        elif interval_preset == "Past 1 Hour":
            start = now - datetime.timedelta(hours=1)
            end = now
        elif interval_preset == "Past 4 Hours":
            start = now - datetime.timedelta(hours=4)
            end = now
        else:  # Default to Today
            start = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
            end = now

        return start.isoformat(), end.isoformat()

    def generate_category_chart(self, start_time: str, end_time: str) -> Figure:
        """
        Generate a modern Donut Chart representing the percentage breakdown of categories.

        Returns:
            Matplotlib Figure ready to embed into Tkinter canvas.
        """
        summary = self.db.get_category_summary(start_time, end_time)

        mode = ctk.get_appearance_mode()
        bg_color = "#ffffff"
        title_color = "#0f172a"
        label_color = "#334155"
        edge_color = "#ffffff"

        Figure = _get_figure_class()
        fig = Figure(figsize=(5.2, 4.0), dpi=100)
        fig.patch.set_facecolor(bg_color)
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg_color)

        if not summary or all(s["total_seconds"] == 0 for s in summary):
            ax.text(
                0.5, 0.5, "No Activity Data Recorded Yet\nStart the tracker to view live charts",
                horizontalalignment="center", verticalalignment="center",
                color="#64748b", fontsize=11, transform=ax.transAxes
            )
            ax.axis("off")
            return fig

        labels = [s["category"] for s in summary]
        sizes = [s["total_seconds"] for s in summary]
        colors = [
            CATEGORY_CONFIG.get(cat, {}).get("color", "#888888")
            for cat in labels
        ]

        # Draw donut chart (pie with center circle)
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,  # Suppress default outer labels for clean look
            colors=colors,
            autopct="%1.1f%%",
            pctdistance=0.75,
            startangle=140,
            wedgeprops=dict(width=0.45, edgecolor=edge_color, linewidth=1.5),
        )

        # Style percentage text
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontsize(9)
            autotext.set_weight("bold")

        # Compact legend below chart
        ax.legend(
            wedges, labels,
            title="Categories",
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            frameon=False,
            labelcolor=label_color,
            title_fontsize=10,
            fontsize=8.5,
        )
        ax.set_title("Time Distribution by Category", color=title_color, fontsize=12, pad=12, weight="bold")
        fig.tight_layout()

        return fig

    def generate_top_apps_chart(self, start_time: str, end_time: str, limit: int = 6) -> Figure:
        """
        Generate a horizontal bar chart displaying top active applications.
        """
        top_apps = self.db.get_top_apps(start_time, end_time, limit=limit)

        mode = ctk.get_appearance_mode()
        bg_color = "#ffffff"
        title_color = "#0f172a"
        text_color = "#334155"
        tick_color = "#475569"
        spine_color = "#e2e8f0"
        grid_color = "#f1f5f9"

        Figure = _get_figure_class()
        fig = Figure(figsize=(5.5, 3.8), dpi=100)
        fig.patch.set_facecolor(bg_color)
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg_color)

        if not top_apps:
            ax.text(
                0.5, 0.5, "No application data for this period",
                horizontalalignment="center", verticalalignment="center",
                color="#64748b", fontsize=11, transform=ax.transAxes
            )
            ax.axis("off")
            return fig

        # Invert so highest app is at the top
        top_apps = list(reversed(top_apps))
        app_names = [a["app_name"] for a in top_apps]
        # Convert seconds to minutes
        durations_m = [round(a["total_seconds"] / 60.0, 1) for a in top_apps]
        colors = [
            CATEGORY_CONFIG.get(a["category"], {}).get("color", "#3b82f6")
            for a in top_apps
        ]

        bars = ax.barh(app_names, durations_m, color=colors, height=0.55, edgecolor="#ffffff")
        ax.set_xlabel("Active Minutes", color=text_color, fontsize=9)
        ax.set_title("Top Applications by Active Time", color=title_color, fontsize=12, pad=12, weight="bold")

        # Dynamic theme axes styling
        ax.tick_params(colors=tick_color, labelsize=8.5)
        for spine in ax.spines.values():
            spine.set_color(spine_color)
        ax.grid(axis="x", color=grid_color, linestyle="--", alpha=0.6)

        # Annotate bar values
        for bar in bars:
            width = bar.get_width()
            ax.text(
                width + (max(durations_m) * 0.02),
                bar.get_y() + bar.get_height() / 2,
                f"{width}m",
                ha="left", va="center", color=title_color, fontsize=8.5, weight="bold"
            )

        fig.tight_layout()
        return fig

    def export_csv(self, start_time: str, end_time: str, export_filepath: str) -> int:
        """Export activity logs to CSV format."""
        activities = self.db.get_activities(start_time, end_time, limit=10000)
        if not activities:
            return 0

        fieldnames = [
            "id", "timestamp", "app_name", "window_title",
            "category", "productivity_score", "duration_seconds",
            "is_idle", "context_tag"
        ]

        with open(export_filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for act in activities:
                writer.writerow(act)

        return len(activities)

    def export_json(self, start_time: str, end_time: str, export_filepath: str) -> int:
        """Export activity logs to JSON format."""
        activities = self.db.get_activities(start_time, end_time, limit=10000)
        metrics = self.db.get_productivity_metrics(start_time, end_time)
        categories = self.db.get_category_summary(start_time, end_time)

        payload = {
            "period": {"start": start_time, "end": end_time},
            "metrics": metrics,
            "category_summary": categories,
            "activities": activities,
        }

        with open(export_filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return len(activities)
