"""
Reports & Analytics View for ProductivityCheck.

This view renders visual productivity charts, key performance indicators (KPIs),
and comprehensive interval filtering (Today, Yesterday, Past 7 Days, etc.).

Architectural Rationale:
- Embedded Matplotlib Canvas: Uses FigureCanvasTkAgg to render smooth, dark-themed
  charts natively inside Tkinter without webview overhead.
- Dynamic Data Fetching: When the user toggles the interval dropdown, statistics
  and charts recalculate and redraw seamlessly.
"""

from typing import Dict, Any, Optional
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.database import DatabaseManager
from core.reporter import ProductivityReporter
from config import THEME, CATEGORY_CONFIG, get_font


class ReportsView(ctk.CTkFrame):
    """View displaying productivity metrics, visual donut charts, and application bar graphs."""

    INTERVAL_OPTIONS = [
        "Today",
        "Yesterday",
        "Past 1 Hour",
        "Past 4 Hours",
        "Past 7 Days",
        "Past 30 Days",
    ]

    def __init__(self, master, db_manager: DatabaseManager, reporter: ProductivityReporter, **kwargs):
        """
        Initialize the Reports View.

        Args:
            master: Parent container.
            db_manager: Database access manager.
            reporter: Productivity reporting and chart generator.
        """
        super().__init__(master, fg_color="transparent", **kwargs)

        self.db = db_manager
        self.reporter = reporter

        self.current_interval = "Today"
        self._canvas_cat = None
        self._canvas_apps = None

        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        """Construct the visual hierarchy."""
        # Header and Controls Row
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(20, 10))

        # Title
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")

        title_label = ctk.CTkLabel(
            title_box,
            text="Focus Analytics & Charts",
            font=get_font(size=24, weight="bold"),
            text_color=THEME["yellow_title"],
        )
        title_label.pack(anchor="w")

        sub_label = ctk.CTkLabel(
            title_box,
            text="Bello! Visual breakdown of your focus time and applications across custom intervals",
            font=get_font(size=13),
            text_color=THEME["text_secondary"],
        )
        sub_label.pack(anchor="w", pady=(2, 0))

        # Interval filter and actions
        actions_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        actions_box.pack(side="right")

        self.combo_interval = ctk.CTkComboBox(
            actions_box,
            values=self.INTERVAL_OPTIONS,
            command=self._on_interval_changed,
            width=140,
            height=36,
            corner_radius=8,
            border_width=1,
            border_color=THEME["input_border"],
            fg_color=THEME["card_bg"],
            button_color=THEME["card_inner"],
            button_hover_color=THEME["border"],
            dropdown_fg_color=THEME["card_bg"],
            dropdown_hover_color=THEME["yellow_tint"],
            dropdown_text_color=THEME["text_primary"],
            text_color=THEME["text_primary"],
            font=get_font(size=13),
        )
        self.combo_interval.set(self.current_interval)
        self.combo_interval.pack(side="left", padx=(0, 10))

        btn_refresh = ctk.CTkButton(
            actions_box,
            text="⟳ Refresh",
            command=self.refresh_data,
            fg_color=THEME["card_bg"],
            hover_color=THEME["card_hover"],
            text_color=THEME["text_primary"],
            border_width=1,
            border_color=THEME["border"],
            width=90,
            height=36,
            corner_radius=8,
            font=get_font(size=12, weight="bold"),
            cursor="hand2",
        )
        btn_refresh.pack(side="left", padx=(0, 8))

        btn_csv = ctk.CTkButton(
            actions_box,
            text="Export CSV",
            command=self._export_csv,
            fg_color=THEME["denim_blue"],
            hover_color=THEME["denim_hover"],
            text_color="#ffffff",
            width=95,
            height=36,
            corner_radius=8,
            font=get_font(size=12, weight="bold"),
            cursor="hand2",
        )
        btn_csv.pack(side="left")

        # Scrollable Content Area
        self.content_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
        )
        self.content_scroll.pack(fill="both", expand=True, padx=20, pady=(5, 15))

        # KPI Metrics Cards Row
        self.kpi_frame = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        self.kpi_frame.pack(fill="x", pady=(0, 15))

        self.kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="kpi")

        # Card 1: Score
        self.card_score = self._create_kpi_card(self.kpi_frame, 0, "PRODUCTIVITY SCORE", "-- %", "#b45309")
        # Card 2: Active Time
        self.card_active = self._create_kpi_card(self.kpi_frame, 1, "ACTIVE FOCUS TIME", "-- hrs", "#0284c7")
        # Card 3: Idle Time
        self.card_idle = self._create_kpi_card(self.kpi_frame, 2, "IDLE / AWAY TIME", "-- hrs", "#64748b")
        # Card 4: Top Category
        self.card_top_cat = self._create_kpi_card(self.kpi_frame, 3, "TOP CATEGORY", "None", "#ea580c")

        # Visual Charts Container (2 columns)
        self.charts_frame = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        self.charts_frame.pack(fill="both", expand=True, pady=(0, 15))
        self.charts_frame.grid_columnconfigure((0, 1), weight=1, uniform="chart_col")

        # Left Chart Container: Donut chart
        self.cat_chart_card = ctk.CTkFrame(
            self.charts_frame,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        self.cat_chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)

        # Right Chart Container: Top Apps
        self.apps_chart_card = ctk.CTkFrame(
            self.charts_frame,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        self.apps_chart_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)

        # Breakdown Table Card
        self.table_card = ctk.CTkFrame(
            self.content_scroll,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        self.table_card.pack(fill="x", pady=5)

        table_header = ctk.CTkFrame(self.table_card, fg_color="transparent")
        table_header.pack(fill="x", padx=20, pady=(15, 10))

        lbl_table = ctk.CTkLabel(
            table_header,
            text="Detailed Category Breakdown",
            font=get_font(size=16, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl_table.pack(side="left")

        self.table_body = ctk.CTkFrame(self.table_card, fg_color="transparent")
        self.table_body.pack(fill="x", padx=20, pady=(0, 15))

    def _create_kpi_card(self, parent, col: int, label: str, default_val: str, accent_color: str):
        """Build an individual stat card widget."""
        card = ctk.CTkFrame(
            parent,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
            height=90,
        )
        card.grid(row=0, column=col, padx=5, pady=0, sticky="nsew")

        lbl_desc = ctk.CTkLabel(
            card,
            text=label,
            font=get_font(size=11, weight="bold"),
            text_color=THEME["text_secondary"],
        )
        lbl_desc.pack(anchor="w", padx=16, pady=(12, 2))

        lbl_val = ctk.CTkLabel(
            card,
            text=default_val,
            font=get_font(size=22, weight="bold"),
            text_color=accent_color,
        )
        lbl_val.pack(anchor="w", padx=16, pady=(0, 12))

        return {"card": card, "val_label": lbl_val, "color": accent_color}

    def _on_interval_changed(self, choice: str) -> None:
        """Handle interval dropdown change."""
        self.current_interval = choice
        self.refresh_data()

    def refresh_data(self) -> None:
        """Recalculate metrics and re-render visual charts."""
        start_iso, end_iso = self.reporter.get_time_interval_bounds(self.current_interval)

        # 1. Update Metrics
        metrics = self.db.get_productivity_metrics(start_iso, end_iso)
        score = metrics.get("productivity_score", 0.0)
        active_sec = metrics.get("active_seconds", 0)
        idle_sec = metrics.get("idle_seconds", 0)

        active_str = self._format_duration(active_sec)
        idle_str = self._format_duration(idle_sec)

        self.card_score["val_label"].configure(text=f"{score}%")
        self.card_active["val_label"].configure(text=active_str)
        self.card_idle["val_label"].configure(text=idle_str)

        # 2. Update Top Category
        summary = self.db.get_category_summary(start_iso, end_iso)
        if summary:
            top_cat = summary[0]["category"]
            self.card_top_cat["val_label"].configure(text=top_cat)
        else:
            self.card_top_cat["val_label"].configure(text="No Data")

        # 3. Render Matplotlib Category Donut Chart
        fig_cat = self.reporter.generate_category_chart(start_iso, end_iso)
        if self._canvas_cat:
            self._canvas_cat.get_tk_widget().destroy()
        self._canvas_cat = FigureCanvasTkAgg(fig_cat, master=self.cat_chart_card)
        self._canvas_cat.draw()
        self._canvas_cat.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # 4. Render Matplotlib Top Apps Bar Chart
        fig_apps = self.reporter.generate_top_apps_chart(start_iso, end_iso)
        if self._canvas_apps:
            self._canvas_apps.get_tk_widget().destroy()
        self._canvas_apps = FigureCanvasTkAgg(fig_apps, master=self.apps_chart_card)
        self._canvas_apps.draw()
        self._canvas_apps.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # 5. Populate Detailed Table
        self._render_table(summary)

    def _render_table(self, summary: list) -> None:
        """Render category rows in table body."""
        for child in self.table_body.winfo_children():
            child.destroy()

        if not summary:
            lbl_empty = ctk.CTkLabel(
                self.table_body,
                text="No logged activities during this interval.",
                text_color=THEME["text_muted"],
                font=get_font(size=12),
            )
            lbl_empty.pack(pady=10)
            return

        for row in summary:
            cat = row["category"]
            color = CATEGORY_CONFIG.get(cat, {}).get("color", "#64748b")
            dur_str = self._format_duration(row["total_seconds"])
            pct = row["percent"]

            item_frame = ctk.CTkFrame(self.table_body, fg_color=THEME["card_inner"], corner_radius=6, height=36, border_width=1, border_color=THEME["border"])
            item_frame.pack(fill="x", pady=3)

            pill = ctk.CTkLabel(
                item_frame,
                text=cat,
                font=get_font(size=11, weight="bold"),
                text_color="#ffffff",
                fg_color=color,
                corner_radius=4,
                padx=8,
                pady=2,
            )
            pill.pack(side="left", padx=10)

            lbl_dur = ctk.CTkLabel(
                item_frame,
                text=f"{dur_str} ({pct}%)",
                font=get_font(size=12, weight="bold"),
                text_color=THEME["text_primary"],
            )
            lbl_dur.pack(side="right", padx=15)

    def _format_duration(self, seconds: int) -> str:
        """Format raw seconds into readable 'Xh Ym' or 'Ys' string."""
        if seconds < 60:
            return f"{seconds}s"
        mins = seconds // 60
        if mins < 60:
            return f"{mins}m"
        hrs = mins // 60
        rem_m = mins % 60
        return f"{hrs}h {rem_m}m"

    def _export_csv(self) -> None:
        """Export current interval logs to CSV."""
        start_iso, end_iso = self.reporter.get_time_interval_bounds(self.current_interval)
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Export Productivity Logs to CSV",
            initialfile=f"productivity_export_{self.current_interval.lower().replace(' ', '_')}.csv",
        )
        if path:
            count = self.reporter.export_csv(start_iso, end_iso, path)
            messagebox.showinfo("Export Complete", f"Successfully exported {count} records to CSV.")
