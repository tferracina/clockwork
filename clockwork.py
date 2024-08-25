"""
Description: A simple CLI tool for tracking time spent on different activities.
Clockwork v1.1.0
"""
import datetime
import sqlite3
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import click
from tabulate import tabulate
import matplotlib.pyplot as plt

from utils import (get_db_path, ensure_table_exists, validate_input,
                   get_date_range, generate_random_color, open_file,
                   load_config, save_config)


# Define temp paths
temp_dir = Path(tempfile.gettempdir())
config = load_config()

@click.group()
def clockwork():
    """A simple CLI tool for tracking time spent on different activities."""


@click.command()
@click.argument('category')
@click.argument('activity')
@click.argument('task')
@click.option('--notes', help='Additional notes for the activity', default=None)
def clockin(category, activity, task, notes=None):
    """Clock in for the given activity, provide category, activity, and task + (optionally notes)"""
    ensure_table_exists()

    try:
        category = validate_input(category)
        activity = validate_input(activity)
        task = validate_input(task)
        notes = validate_input(notes) if notes else None
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            current_time = datetime.now()
            c.execute("INSERT INTO timelog (category, activity, task, start_time, notes) VALUES (?, ?, ?, ?, ?)",
                      (category, activity, task, current_time, notes))
            conn.commit()
        print(f"Clocked in for {activity} ({task}) at {current_time.strftime('%H:%M:%S')}")
    except (sqlite3.Error, ValueError) as e:
        print(f"An error occurred while clocking in: {e}")


@click.command()
@click.argument('activity')
@click.option('--notes', help='Additional notes for the activity', default=None)
def clockout(activity, notes=None):
    """Clock out for the given activity, provide activity name + (optionally notes)."""
    ensure_table_exists()

    try:
        activity = validate_input(activity)
        notes = validate_input(notes) if notes else None

        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            current_time = datetime.now()

            c.execute("SELECT COUNT(*) FROM timelog WHERE activity = ? AND end_time IS NULL",
                       (activity,))
            if c.fetchone()[0] == 0:
                print(f"No active clock-in found for {activity}")
                return
            c.execute("SELECT id, start_time FROM timelog WHERE activity = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1", (activity,))
            result = c.fetchone()

            if result:
                activity_id, start_time = result
                start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S.%f')
                duration = int((current_time - start_time).total_seconds())

                if notes:
                    c.execute("UPDATE timelog SET end_time = ?, duration = ?, notes = COALESCE(notes || ' ' || ?, notes, ?) WHERE id = ?",
                              (current_time, duration, notes, notes, activity_id))
                else:
                    c.execute("UPDATE timelog SET end_time = ?, duration = ? WHERE id = ?",
                              (current_time, duration, activity_id))
                conn.commit()
                print(f"Clocked out from {activity} at {current_time.strftime('%H:%M:%S')} | Duration: {timedelta(seconds=duration)}")
            else:
                print(f"No active clock-in found for {activity}")
    except sqlite3.Error as e:
        print(f"An error occurred while clocking out: {e}")


RANGE = {
    "d": "daily",
    "w": "weekly",
    "m": "monthly",
    "y": "yearly"
}

@click.command()
@click.argument('date_range', type=click.Choice(RANGE.keys()), default="w")
#@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]))
#@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]))
def clocklog(date_range):
    """Generate a report for the activities between the given dates"""
    ensure_table_exists()

    start_date, end_date = get_date_range(date_range)

    try:
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            c.execute("""SELECT id, category, activity, task,
                                strftime('%Y-%m-%d %H:%M:%S', start_time) AS start_time,
                                strftime('%Y-%m-%d %H:%M:%S', end_time) AS end_time,
                                duration, notes
                         FROM timelog
                         WHERE date(start_time) BETWEEN ? AND ?
                         ORDER BY start_time""", (start_date, end_date))
            activities = c.fetchall()

        if activities:
            headers = ["ID", "CATEGORY", "ACTIVITY", "TASK", "START_TIME", "END_TIME", "DURATION", "NOTES"]
            table = [[a[0], a[1], a[2], a[3], a[4], a[5] or "Ongoing", str(timedelta(seconds=a[6])) if a[6] else "N/A", a[7]] for a in activities]
            print(f"\nReport for {RANGE[date_range]} activities ({start_date} to {end_date}):")
            print(tabulate(table, headers=headers, tablefmt="grid"))
        else:
            print("No activities found in the specified date range.")
    except sqlite3.Error as e:
        print(f"An error occurred while fetching the report: {e}")


@click.command()
@click.argument('date_range', type=click.Choice(RANGE.keys()), default="w")
def clocksum(date_range):
    """Generate a summary report of activities by category between the given dates"""
    ensure_table_exists()

    start_date, end_date = get_date_range(date_range)

    try:
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            c.execute("""SELECT category, SUM(duration) as total_duration
                         FROM timelog
                         WHERE date(start_time) BETWEEN ? AND ?
                         GROUP BY category
                         ORDER BY total_duration DESC""", (start_date, end_date))
            summary = c.fetchall()

        if summary:
            headers = ["CATEGORY", "TOTAL DURATION"]
            summary_dict = defaultdict(int)
            for category, duration in summary:
                summary_dict[category] = duration

            table = [[category, str(timedelta(seconds=duration))] for category, duration in summary_dict.items()]
            total_duration = sum(summary_dict.values())

            print(f"\nSummary report for {RANGE[date_range]} ({start_date} to {end_date}):")
            print(tabulate(table, headers=headers, tablefmt="grid"))
            print(f"\nTotal duration: {str(timedelta(seconds=total_duration))}")
        else:
            print("No activities found in the specified date range.")
    except sqlite3.Error as e:
        print(f"An error occurred while fetching the summary: {e}")


COLOR_DICT = config.get('color_dict', {})


@click.command()
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option('--category', help='Optional category filter')
def clockvis(start_date, end_date, category=None):
    """Visualize the time distribution for the activities between the given dates."""
    ensure_table_exists()

    try:
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            if category:
                category = validate_input(category)
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
            open_file(str(fig_path))
        else:
            print("No data available for visualization in the specified date range and/or category.")
    except sqlite3.Error as e:
        print(f"An error occurred while fetching data for visualization: {e}")
    except subprocess.SubprocessError as e:
        print(f"An error occurred while opening the image: {e}")


config['color_dict'] = COLOR_DICT
save_config(config)


@click.command()
@click.argument('start_date', required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.argument('end_date', required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option('--category', help='Optional category filter')
def clockcsv(start_date, end_date, category=None):
    """Generate a CSV file for the activities between the given dates."""
    ensure_table_exists()

    try:
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            if category:
                category = validate_input(category)
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
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                f.write(csv_data)
            print(f"CSV file generated: {csv_file}")
            open_file(str(csv_file))
        else:
            print("No activities found in the specified date range.")
    except sqlite3.Error as e:
        print(f"An error occurred while generating the CSV file: {e}")


clockwork.add_command(clockin)
clockwork.add_command(clockout)
clockwork.add_command(clocklog)
clockwork.add_command(clocksum)
clockwork.add_command(clockvis)
clockwork.add_command(clockcsv)


if __name__ == '__main__':
    ensure_table_exists()
    clockwork()
