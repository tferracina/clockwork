"""Utility functions for the clockwork package."""

import re
import sqlite3
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
from db_manager import get_db_connection, DatabaseError, execute_query
from typing import Tuple, Optional


# Define the paths
home_dir = Path.home()
clockwork_dir = home_dir / ".clockwork"

DB_FILE = clockwork_dir / "timelog.db"
CONFIG_FILE = clockwork_dir / "config.json"


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
            df = pd.read_sql_query(query, conn)
            df["start_time"] = pd.to_datetime(df["start_time"])
            df["end_time"] = pd.to_datetime(df["end_time"])
            return df
    except DatabaseError as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error


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


def get_date_range(date_range: str) -> Tuple[datetime, datetime]:
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


def df_by_range(df, date_range):
    """Filter the DataFrame by the given date range."""
    start_date, end_date = get_date_range(date_range)

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])

    return df[
        (df["start_time"].dt.date >= start_date)
        & (df["start_time"].dt.date <= end_date)
    ]


def minute_to_string(x):
    """Converts the minute to a string in the format HH:MM."""
    return f"{int((x%(24*60))/60):02d}h {int(x%60):02d}m"


def open_file(filepath):
    """Open file depending on platform."""
    if sys.platform.startswith("darwin"):  # macOS
        subprocess.call(("open", filepath))
    elif sys.platform.startswith("win"):  # Windows
        os.startfile(filepath)
    else:  # linux variants
        subprocess.call(("xdg-open", filepath))


def generate_random_color():
    """Generate a random color code for the COLOR_DICT."""
    return f"#{random.randint(0, 0xFFFFFF):06x}"


def make_pie_chart(df, date_range=None, category=None):
    """Create a pie chart based on the DataFrame."""

    if date_range is not None:
        date_subdf = df_by_range(df, date_range)
    else:
        date_subdf = df

    start_date = date_subdf["start_time"].min().date()
    end_date = date_subdf["end_time"].max().date()

    if category is not None:
        cat_subdf = date_subdf[date_subdf["category"] == category]
    else:
        cat_subdf = date_subdf

    color_scale = px.colors.qualitative.Plotly

    if category is None:
        pie_fig = px.pie(
            cat_subdf,
            names="category",
            values="duration",
            color="category",
            color_discrete_sequence=color_scale,
        )
    else:
        pie_fig = px.pie(
            cat_subdf,
            names="activity",
            values="duration",
            color="activity",
            color_discrete_sequence=color_scale,
        )

    pie_fig.update_traces(
        textposition="inside", direction="clockwise", hole=0.3, textinfo="percent+label"
    )

    total_time = cat_subdf["duration"].sum()
    formatted_tt = minute_to_string(int(total_time))

    pie_fig.update_layout(
        uniformtext_minsize=12,
        uniformtext_mode="hide",
        title=dict(
            text=f'{"breakdown" if category is None else f"{category} Breakdown"} from {start_date} to {end_date}',
            x=0.5,
        ),
        annotations=[
            dict(text=formatted_tt, x=0.5, y=0.5, font_size=12, showarrow=False)
        ],
    )
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".html", mode="w", encoding="utf-8"
    ) as tmpfile:
        pie_fig.write_html(tmpfile.name)
        return tmpfile.name
