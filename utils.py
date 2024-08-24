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
        "csv_export": {"delimiter": ",", "quotechar": "\"", "encoding": "utf-8"},
        "visualization": {"default_chart_type": "pie", "figure_size": [10, 7], "dpi": 100},
        "time_format": "%Y-%m-%d %H:%M:%S",
        "categories": [],
        "notification": {"enable": False, "reminder_interval": 30},
        "backup": {"enable": False, "interval_days": 7, "max_backups": 5}
    }
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding="utf8") as f:
            user_config = json.load(f)
        default_config.update(user_config)
    return default_config


def save_config(config):
    """Save configuration to JSON file."""
    with open(CONFIG_FILE, 'w', encoding="utf8") as f:
        json.dump(config, f, indent=2)


def ensure_table_exists():
    """Check if the timelog table exists, and initialize the database if it does not."""
    try:
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='timelog'")
            if not c.fetchone():
                init_db()
    except sqlite3.Error as e:
        print(f"An error occurred while checking the table existence: {e}")


def init_db():
    """Initialize the database by creating necessary tables if they do not exist."""
    try:
        Path(get_db_path()).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS timelog
                         (id INTEGER PRIMARY KEY,
                          category TEXT,
                          activity TEXT,
                          task TEXT,
                          start_time TIMESTAMP,
                          end_time TIMESTAMP,
                          duration INTEGER,
                          notes TEXT)''')
            conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred while initializing the database: {e}")
    except OSError as e:
        print(f"An error occurred while creating the directory: {e}")


def validate_input(input_string, max_length=100):
    """Validate and sanitize input."""
    if not input_string or not isinstance(input_string, str):
        raise ValueError("Input must be a non-empty string")
    if len(input_string) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length} characters")
    return re.sub(r'[^\w\s-]', '', input_string)


def get_date_range(date_range):
    """Get the start and end dates based on the date range."""
    today = datetime.now().date()
    if date_range == "d":
        start_date = today
        end_date = today
    elif date_range == "w":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif date_range == "m":
        start_date = today.replace(day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)
    elif date_range == "y":
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    return start_date, end_date


def open_file(filepath):
    """Open file depending on platform."""
    if sys.platform.startswith('darwin'):  # macOS
        subprocess.call(('open', filepath))
    elif sys.platform.startswith('win'):   # Windows
        os.startfile(filepath)
    else:  # linux variants
        subprocess.call(('xdg-open', filepath))


def generate_random_color():
    """Generate a random color code for the COLOR_DICT."""
    return f"#{random.randint(0, 0xFFFFFF):06x}"