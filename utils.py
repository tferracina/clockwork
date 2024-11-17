"""Utility functions for the clockwork package."""

import re
from pathlib import Path
from datetime import datetime, timedelta
import os
import subprocess
import sys
import random
import json
import tempfile
import pandas as pd
import plotly.express as px
from db_manager import get_db_connection, DatabaseError
from typing import Tuple, Optional

# Define the paths
home_dir = Path.home()
clockwork_dir = home_dir / ".clockwork"

DB_FILE = clockwork_dir / "timelog.db"
CONFIG_FILE = clockwork_dir / "config.json"

# Define the date range mappings
RANGE = {"d": "daily", "w": "weekly", "m": "monthly", "y": "yearly"}


def get_db_path():
    """Get the path to the database file."""
    return str(DB_FILE)


def load_config():
    """Load configuration from JSON file with default values."""
    default_config = {
        "color_dict": {},
        "database": {"path": str(DB_FILE)},
        "default_date_range": "w",
        "csv_export": {"delimiter": ",", "quotechar": '"', "encoding": "utf-8"},
        "visualization": {
            "default_chart_type": "pie",
            "figure_size": [10, 7],
            "dpi": 100,
        },
        "time_format": "%Y-%m-%d %H:%M:%S",
        "categories": [],
        "notification": {"enable": False, "reminder_interval": 30},
        "backup": {"enable": False, "interval_days": 7, "max_backups": 5},
    }
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf8") as f:
            user_config = json.load(f)
        default_config.update(user_config)
    return default_config


def save_config(config):
    """Save configuration to JSON file."""
    with open(CONFIG_FILE, "w", encoding="utf8") as f:
        json.dump(config, f, indent=2)


def load_data() -> pd.DataFrame:
    """Query all the data from database and return as DataFrame."""
    try:
        query = "SELECT * FROM timelog ORDER BY start_time"
        with get_db_connection() as conn:
            return pd.read_sql_query(
                query, conn, parse_dates=["start_time", "end_time"]
            )
    except DatabaseError as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()


def validate_input(input_string: Optional[str], max_length: int = 100) -> Optional[str]:
    """Validate and sanitize input."""
    if input_string is None:
        return None
    if not isinstance(input_string, str):
        raise ValueError("Input must be a string")
    if len(input_string) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length} characters")
    sanitized = re.sub(r"[^\w\s-]", "", input_string)
    if not sanitized:
        raise ValueError("Input must contain valid characters")
    return sanitized


def get_date_range(date_range: str) -> Tuple[datetime.date, datetime.date]:
    """Get the start and end dates based on the date range."""
    today = datetime.now().date()
    if date_range == "d":
        return today, today
    elif date_range == "w":
        start_date = today - timedelta(days=today.weekday())
        return start_date, start_date + timedelta(days=6)
    elif date_range == "m":
        start_date = today.replace(day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)
        return start_date, end_date
    elif date_range == "y":
        return today.replace(month=1, day=1), today
    raise ValueError(f"Invalid date range: {date_range}")


def df_by_range(df: pd.DataFrame, date_range: str) -> pd.DataFrame:
    """Filter the DataFrame by the given date range."""
    start_date, end_date = get_date_range(date_range)
    return df[
        (pd.to_datetime(df["start_time"]).dt.date >= start_date)
        & (pd.to_datetime(df["start_time"]).dt.date <= end_date)
    ]


def minute_to_string(seconds: int) -> str:
    """
    Convert seconds to a human-readable string format.
    """
    minutes = seconds // 60
    hours = minutes // 60
    remaining_minutes = minutes % 60
    return f"{hours:02d}h {remaining_minutes:02d}m"


def open_file(filepath: str) -> None:
    """Open file depending on platform."""
    try:
        if sys.platform.startswith("darwin"):  # macOS
            subprocess.call(("open", filepath))
        elif sys.platform.startswith("win"):  # Windows
            os.startfile(filepath)
        else:  # linux variants
            subprocess.call(("xdg-open", filepath))
    except Exception as e:
        print(f"Error opening file: {e}")
        print(f"File saved at: {filepath}")


def generate_random_color() -> str:
    """Generate a random color code for the COLOR_DICT."""
    return f"#{random.randint(0, 0xFFFFFF):06x}"


def make_pie_chart(
    df: pd.DataFrame, date_range: Optional[str] = None, category: Optional[str] = None
) -> Optional[str]:
    """
    Create a pie chart visualization based on the DataFrame.
    """
    if df.empty:
        raise ValueError("No data available for visualization")

    # Ensure datetime columns are properly formatted
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])

    # Remove rows with NaT values
    df = df.dropna(subset=["start_time", "end_time"])

    # Filter by date range if specified
    if date_range is not None:
        df = df_by_range(df, date_range)
        if df.empty:
            raise ValueError(
                f"No data available for the specified {RANGE[date_range]} range"
            )

    # Filter by category if specified
    if category is not None:
        df = df[df["category"] == category]
        if df.empty:
            raise ValueError(
                f"No data available for category '{category}' in the specified {RANGE[date_range]} range"
            )

    # Calculate total duration
    total_duration = df["duration"].sum()
    if total_duration == 0:
        raise ValueError("No duration data available for visualization")

    # Set title text based on date range
    if date_range:
        title_text = (
            f"{'Activity' if category else 'Category'} Breakdown ({RANGE[date_range]})"
        )
    else:
        # Get date range for title, handling potential NaT values
        valid_start_times = df["start_time"].dropna()
        valid_end_times = df["end_time"].dropna()

        if not valid_start_times.empty and not valid_end_times.empty:
            start_date = valid_start_times.min().strftime("%Y-%m-%d")
            end_date = valid_end_times.max().strftime("%Y-%m-%d")
            title_text = f"{'Activity' if category else 'Category'} Breakdown ({start_date} to {end_date})"
        else:
            title_text = f"{'Activity' if category else 'Category'} Breakdown"

    # Create pie chart
    pie_fig = px.pie(
        df,
        names="activity" if category else "category",
        values="duration",
        color="activity" if category else "category",
        color_discrete_sequence=px.colors.qualitative.Plotly,
    )

    # Update chart appearance
    pie_fig.update_traces(
        textposition="inside",
        direction="clockwise",
        hole=0.3,
        textinfo="percent+label",
        texttemplate="%{percent:.1f}%<br>%{label}",
        hovertemplate=(
            "%{label}<br>"
            "Duration: %{value:,.0f} seconds<br>"
            "Percentage: %{percent:.1f}%<br>"
            "<extra></extra>"
        ),
    )

    # Update layout
    pie_fig.update_layout(
        title=dict(text=title_text, x=0.5, font=dict(size=16)),
        uniformtext_minsize=12,
        uniformtext_mode="hide",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        annotations=[
            dict(
                text=f"Total Time:<br>{minute_to_string(total_duration)}",
                x=0.5,
                y=0.5,
                font=dict(size=14),
                showarrow=False,
                align="center",
            )
        ],
        margin=dict(t=50, b=100),
    )

    # Save visualization
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".html", mode="w", encoding="utf-8"
        ) as tmpfile:
            pie_fig.write_html(
                tmpfile.name,
                include_plotlyjs=True,
                full_html=True,
                config={"displayModeBar": False},
            )
            return tmpfile.name
    except Exception as e:
        print(f"Error saving visualization: {e}")
        return None
