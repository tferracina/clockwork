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

from utils import (get_db_path, ensure_table_exists, validate_input,
                   get_date_range, open_file, load_config, save_config,
                   load_data, make_pie_chart)


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
def clocklog(date_range):
    """Generate a weekly report for the activities between the given dates"""
    ensure_table_exists()

    start_date, end_date = get_date_range(date_range)

    try:
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            c.execute("""SELECT category,
                                strftime('%w', start_time) AS day_of_week,
                                COALESCE(SUM(duration), 0) as total_duration
                         FROM timelog
                         WHERE date(start_time) BETWEEN ? AND ?
                         GROUP BY category, day_of_week
                         ORDER BY day_of_week, category""", (start_date, end_date))
            activities = c.fetchall()

        if activities:
            # Create a nested dictionary to store the data
            week_data = defaultdict(lambda: defaultdict(int))
            for category, day, duration in activities:
                week_data[int(day)][category] = int(duration)  # Ensure duration is an integer

            # Prepare the table data
            headers = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
            table = []

            # Find all unique categories
            all_categories = set(category for day_data in week_data.values() for category in day_data.keys())

            for category in sorted(all_categories):
                row = []
                for day in range(7):  # 0 (Sunday) to 6 (Saturday)
                    duration = week_data[day].get(category, 0)
                    if duration > 0:
                        row.append(f"{category}:\n{str(timedelta(seconds=duration))}")
                    else:
                        row.append("")
                table.append(row)

            # Reorder the columns to start with Monday
            table = [row[1:] + [row[0]] for row in table]

            print(f"\nWeekly report for {RANGE[date_range]} ({start_date} to {end_date}):")
            print(tabulate(table, headers=headers, tablefmt="grid"))
        else:
            print("No activities found in the specified date range.")
    except sqlite3.Error as e:
        print(f"An error occurred while fetching the report: {e}")


@click.command()
@click.argument('date_range', type=click.Choice(RANGE.keys()), default="w")
def clocksum(date_range):
    """Generate a nested summary report of activities by category between the given dates"""
    ensure_table_exists()

    start_date, end_date = get_date_range(date_range)

    try:
        with sqlite3.connect(get_db_path()) as conn:
            c = conn.cursor()
            c.execute("""SELECT category, activity, task, SUM(duration) as total_duration
                        FROM timelog
                        WHERE date(start_time) BETWEEN ? AND ?
                        AND duration IS NOT NULL
                        GROUP BY category, activity, task
                        ORDER BY category, activity, total_duration DESC""", (start_date, end_date))
            summary = c.fetchall()

        if summary:
            headers = ["CATEGORY", "ACTIVITY", "TASK", "DURATION"]
            table = []
            summary_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

            # Organize data into nested dictionary
            for category, activity, task, duration in summary:
                summary_dict[category][activity][task] = duration

            # Build the table
            for category, activities in summary_dict.items():
                category_total = sum(sum(tasks.values()) for tasks in activities.values())
                table.append([category, "", "", str(timedelta(seconds=category_total))])

                for activity, tasks in activities.items():
                    activity_total = sum(tasks.values())
                    table.append(["", activity, "", str(timedelta(seconds=activity_total))])

                    for task, duration in tasks.items():
                        table.append(["", "", task, str(timedelta(seconds=duration))])

            total_duration = sum(sum(sum(tasks.values()) for tasks in activities.values()) for activities in summary_dict.values())

            print(f"\nNested summary report for {RANGE[date_range]} ({start_date} to {end_date}):")
            print(tabulate(table, headers=headers, tablefmt="grid"))
            print(f"\nTotal duration: {str(timedelta(seconds=total_duration))}")
        else:
            print("No activities found in the specified date range.")
    except sqlite3.Error as e:
        print(f"An error occurred while fetching the summary: {e}")


COLOR_DICT = config.get('color_dict', {})


@click.command()
@click.argument('date_range', type=click.Choice(RANGE.keys()), default="w")
@click.argument('category', required=False)
def clockvis(date_range, category=None):
    """Visualize the time distribution for the activities between the given dates."""
    try:
        ensure_table_exists()
        data = load_data()

        if data.empty:
            print("No data available for visualization.")
            return

        if category is not None:
            category = validate_input(category)

        fig_path = make_pie_chart(data, date_range, category)

        if fig_path is not None:
            open_file(fig_path)
        else:
            print("No data available for visualization in the specified date range and/or category.")
    except sqlite3.Error as e:
        print(f"An error occurred while fetching data for visualization: {e}")
    except subprocess.SubprocessError as e:
        print(f"An error occurred while opening the image: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


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
