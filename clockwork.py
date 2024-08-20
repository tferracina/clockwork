# Description: A simple CLI tool for tracking time spent on different activities.
# Clockwork v1.0.1

import argparse
import datetime
import sqlite3
import tempfile
import sys
import os
import re
import subprocess
from tabulate import tabulate
import matplotlib.pyplot as plt
from pathlib import Path
import random

# Define the paths
home_dir = Path.home()
clockwork_dir = home_dir / ".clockwork"
temp_dir = Path(tempfile.gettempdir())

DB_FILE = clockwork_dir / "timelog.db"

def get_db_path():
    return str(DB_FILE)

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

def sanitize_input(input_string):
    """Sanitize input to prevent SQL injection."""
    return re.sub(r'[^\w\s-]', '', input_string)

def clockin(category, activity, task, notes=None):
    """Clock in for the given activity, provide category, activity, and task + (optionally notes)."""
    try: 
        category = sanitize_input(category)
        activity = sanitize_input(activity)
        task = sanitize_input(task)
        notes = sanitize_input(notes) if notes else None
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            current_time = datetime.datetime.now()
            c.execute("INSERT INTO timelog (category, activity, task, start_time, notes) VALUES (?, ?, ?, ?, ?)",
                      (category, activity, task, current_time, notes))
            conn.commit()
        print(f"Clocked in for {activity} ({task}) at {current_time.strftime('%H:%M:%S')}")
    except sqlite3.Error as e:
        print(f"An error occurred while clocking in: {e}")

def clockout(activity, notes=None):
    """Clock out for the given activity, provide activity name + (optionally notes)."""
    try:
        activity = sanitize_input(activity)
        notes = sanitize_input(notes) if notes else None

        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            current_time = datetime.datetime.now()

            c.execute("SELECT COUNT(*) FROM timelog WHERE activity = ? AND end_time IS NULL", (activity,))
            if c.fetchone()[0] == 0:
                print(f"No active clock-in found for {activity}")
                return
            
            c.execute("SELECT id, start_time FROM timelog WHERE activity = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1", (activity,))
            result = c.fetchone()

            if result:
                activity_id, start_time = result
                start_time = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S.%f')
                duration = int((current_time - start_time).total_seconds())

                if notes:
                    c.execute("UPDATE timelog SET end_time = ?, duration = ?, notes = COALESCE(notes || ' ' || ?, notes, ?) WHERE id = ?",
                              (current_time, duration, notes, notes, activity_id))
                else:
                    c.execute("UPDATE timelog SET end_time = ?, duration = ? WHERE id = ?",
                              (current_time, duration, activity_id))
                conn.commit()
                print(f"Clocked out from {activity} at {current_time.strftime('%H:%M:%S')}")
                print(f"Duration: {datetime.timedelta(seconds=duration)}")
            else:
                print(f"No active clock-in found for {activity}")
    except sqlite3.Error as e:
        print(f"An error occurred while clocking out: {e}")

def validate_date(date_text):
    """Validate date format as YYYY-MM-DD."""
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def generate_report(start_date=None, end_date=None):
    """Generate a report for the activities between the given dates"""

    # If no dates are provided, fetch the earliest and latest dates in the database
    if start_date is None and end_date is None:
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            c.execute("SELECT MIN(date(start_time)), MAX(date(end_time)) FROM timelog")
            result = c.fetchone()
            start_date, end_date = result
            if not (start_date and end_date):
                print("No records found in the database.")
                return
    else:
        result = None

    if not (validate_date(start_date) and validate_date(end_date)):
        print("Error: Invalid date format. Please use YYYY-MM-DD.")
        return

    try: 
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            if result:
                c.execute("""SELECT id, category, activity, task, start_time, end_time, duration, notes 
                            FROM timelog 
                            WHERE date(start_time) BETWEEN ? AND ?
                            ORDER BY start_time""", result)
            else:
                c.execute("""SELECT id, category, activity, task, start_time, end_time, duration, notes 
                            FROM timelog 
                            WHERE date(start_time) BETWEEN ? AND ?
                            ORDER BY start_time""", (start_date, end_date))
            activities = c.fetchall()

        if activities:
            headers = ["ID", "CATEGORY", "ACTIVITY", "TASK", "START_TIME", "END_TIME", "DURATION", "NOTES"]
            table = [[a[0], a[1], a[2], a[3], a[4], a[5] or "Ongoing", str(datetime.timedelta(seconds=a[6])) if a[6] else "N/A", a[7]] for a in activities]
            print(tabulate(table, headers=headers, tablefmt="grid"))
        else:
            print("No activities found in the specified date range.")
    except sqlite3.Error as e:
        print(f"An error occurred while fetching the report: {e}")

def open_file(filepath):
    if sys.platform.startswith('darwin'):  # macOS
        subprocess.call(('open', filepath))
    elif sys.platform.startswith('win'):   # Windows
        os.startfile(filepath)
    else:  # linux variants
        subprocess.call(('xdg-open', filepath))

try:
    from config import COLOR_DICT
except ImportError:
    COLOR_DICT = {}

def generate_random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def visualize_time_distribution(start_date, end_date, category=None, open_image=True):
    """Visualize the time distribution for the activities between the given dates."""
    if not (validate_date(start_date) and validate_date(end_date)):
        print("Error: Invalid date format. Please use YYYY-MM-DD.")
        return
    
    try:
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            if category:
                category = sanitize_input(category)
                c.execute("""SELECT activity, SUM(duration) 
                            FROM timelog 
                            WHERE date(start_time) BETWEEN ? AND ? 
                            AND duration IS NOT NULL
                            AND category = ?
                            GROUP BY activity""", (start_date, end_date, category))
            else:
                c.execute("""SELECT category, SUM(duration) 
                            FROM timelog 
                            WHERE date(start_time) BETWEEN ? AND ? 
                            AND duration IS NOT NULL
                            GROUP BY category""", (start_date, end_date))
            data = c.fetchall()

        fig_path = temp_dir / f"time_dist_{start_date}_{end_date}{'_' + category if category else ''}.png"

        if data:
            labels, durations = zip(*data)
            if not durations:
                print("No data available for visualization in the specified date range and/or category.")
                return
            plt.figure(figsize=(10, 7))
            colors = []
            for label in labels:
                if label not in COLOR_DICT:
                    COLOR_DICT[label] = generate_random_color()
                colors.append(COLOR_DICT[label])
            plt.pie(durations, labels=labels, autopct='%1.1f%%', shadow=True, colors=colors)
            title = f"Time Distribution ({start_date} to {end_date})"
            if category:
                title += f" for category: {category}"
            plt.title(title)
            plt.legend(loc="best")
            plt.axis('equal')
            plt.savefig(fig_path)
            plt.close()
            print(f"Time distribution saved to {fig_path}")

            if open_image:
                open_file(str(fig_path))
        else:
            print("No data available for visualization in the specified date range and/or category.")
    except sqlite3.Error as e:
        print(f"An error occurred while fetching data for visualization: {e}")
    except subprocess.SubprocessError as e:
        print(f"An error occurred while opening the image: {e}")

def generate_csv(start_date, end_date, category=None):
    """Generate a CSV file for the activities between the given dates."""
    if not (validate_date(start_date) and validate_date(end_date)):
        print("Error: Invalid date format. Please use YYYY-MM-DD.")
        return

    try:
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            if category:
                category = sanitize_input(category)
                c.execute("""SELECT id, category, activity, task, start_time, end_time, duration, notes 
                            FROM timelog 
                            WHERE date(start_time) BETWEEN ? AND ? 
                            AND duration IS NOT NULL
                            AND category = ?
                            ORDER BY id""", (start_date, end_date, category))
            else:
                c.execute("""SELECT id, category, activity, task, start_time, end_time, duration, notes 
                            FROM timelog 
                            WHERE date(start_time) BETWEEN ? AND ? 
                            AND duration IS NOT NULL
                            ORDER BY id""", (start_date, end_date))
            activities = c.fetchall()

        if activities:
            headers = ["ID", "CATEGORY", "ACTIVITY", "TASK", "START_TIME", "END_TIME", "DURATION", "NOTES"]
            csv_data = [",".join(headers)]
            for a in activities:
                csv_data.append(",".join([str(i) for i in a]))
            csv_data = "\n".join(csv_data)
            csv_file = temp_dir / f"timelog_{start_date}_{end_date}{'_' + category if category else ''}.csv"
            with open(csv_file, "w") as f:
                f.write(csv_data)
            print(f"CSV file generated: {csv_file}")
            open_file(str(csv_file))
        else:
            print("No activities found in the specified date range.")
    except sqlite3.Error as e:
        print(f"An error occurred while generating the CSV file: {e}")


def main():
    ensure_table_exists()

    parser = argparse.ArgumentParser(description='Enhanced Time tracking CLI tool')
    subparsers = parser.add_subparsers(dest='action', required=True)

    # Clockin parser
    clockin_parser = subparsers.add_parser('clockin')
    clockin_parser.add_argument('category', nargs='?', help='Activity category, examples: work, study, personal, etc.')
    clockin_parser.add_argument('activity', nargs='?', help='Activity name, examples: coding, physics, reading etc.')
    clockin_parser.add_argument('task', nargs='?', help='Task name: project-task, exercise-set-3, etc.')
    clockin_parser.add_argument('--notes', help='Additional notes for the activity')

    # Clockout parser
    clockout_parser = subparsers.add_parser('clockout')
    clockout_parser.add_argument('activity', help='Activity name')
    clockout_parser.add_argument('--notes', help='Additional notes for the activity')

    # Report parser
    report_parser = subparsers.add_parser('clocklog')
    report_parser.add_argument('start_date', nargs='?', help='Start date (YYYY-MM-DD)')
    report_parser.add_argument('end_date', nargs='?', help='End date (YYYY-MM-DD)')

    # Visualize parser
    vis_parser = subparsers.add_parser('clockvis')
    vis_parser.add_argument('start_date', help='Start date (YYYY-MM-DD)')
    vis_parser.add_argument('end_date', help='End date (YYYY-MM-DD)')
    vis_parser.add_argument('--category', help='Optional category filter')
    vis_parser.add_argument('--closed', action='store_false', dest='open', help='Do not open the generated figure')

    # Csv parser
    csv_parser = subparsers.add_parser('clockcsv')
    csv_parser.add_argument('start_date', help='Start date (YYYY-MM-DD)')
    csv_parser.add_argument('end_date', help='End date (YYYY-MM-DD)')
    csv_parser.add_argument('--category', help='Optional category filter')

    args = parser.parse_args()

    if args.action == 'clockin':
        clockin(args.category, args.activity, args.task, args.notes)
    elif args.action == 'clockout':
        clockout(args.activity, args.notes)
    elif args.action == 'clocklog':
        generate_report(args.start_date, args.end_date)
    elif args.action == 'clockvis':
        visualize_time_distribution(args.start_date, args.end_date, args.category, args.open)
    elif args.action == 'clockcsv':
        generate_csv(args.start_date, args.end_date, args.category)

if __name__ == '__main__':
    main()