"""
Description: A simple CLI tool for tracking time spent on different activities.
Clockwork v1.1.0
"""

import datetime
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import click
from tabulate import tabulate
import csv
from time import perf_counter

from utils import (
    validate_input,
    get_date_range,
    open_file,
    load_config,
    save_config,
    load_data,
    make_pie_chart,
)

from db_manager import DatabaseError, execute_query, execute_write_query, init_db


# CONSTANTS
RANGE = {"d": "daily", "w": "weekly", "m": "monthly", "y": "yearly"}
temp_dir = Path(tempfile.gettempdir())
config = load_config()


@click.group()
def clockwork():
    """A simple CLI tool for tracking time spent on different activities."""


@click.command()
@click.argument("category")
@click.argument("activity")
@click.argument("task")
@click.option("--notes", help="Additional notes for the activity", default=None)
def clockin(category, activity, task, notes=None):
    """Clock in for the given activity."""
    try:
        category = validate_input(category)
        activity = validate_input(activity)
        task = validate_input(task)
        notes = validate_input(notes) if notes else None

        current_time = datetime.now()
        query = """
            INSERT INTO timelog (category, activity, task, start_time, notes)
            VALUES (?, ?, ?, ?, ?)
        """
        execute_write_query(query, (category, activity, task, current_time, notes))
        print(
            f"Clocked in for {activity} ({task}) at {current_time.strftime('%H:%M:%S')}"
        )
    except DatabaseError as e:
        print(f"Database error while clocking in: {e}")
    except ValueError as e:
        print(f"Invalid input: {e}")


@click.command()
@click.argument("activity")
@click.option("--notes", help="Additional notes for the activity", default=None)
def clockout(activity, notes=None):
    """Clock out from the given activity."""
    try:
        activity = validate_input(activity)
        notes = validate_input(notes) if notes else None
        current_time = datetime.now()

        # First check if there's an active session
        query = """
            SELECT id, start_time
            FROM timelog
            WHERE activity = ? AND end_time IS NULL
            ORDER BY start_time DESC LIMIT 1
        """
        result = execute_query(query, (activity,))

        if not result:
            print(f"No active clock-in found for {activity}")
            return

        activity_id, start_time = result[0]
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S.%f")
        duration = int((current_time - start_time).total_seconds())

        # Update the record
        update_query = """
            UPDATE timelog
            SET end_time = ?,
                duration = ?,
                notes = CASE
                    WHEN ? IS NOT NULL
                    THEN COALESCE(notes || ' ' || ?, ?)
                    ELSE notes
                END
            WHERE id = ?
        """
        execute_write_query(
            update_query, (current_time, duration, notes, notes, notes, activity_id)
        )

        print(
            f"Clocked out from {activity} at {current_time.strftime('%H:%M:%S')} | "
            f"Duration: {timedelta(seconds=duration)}"
        )
    except DatabaseError as e:
        print(f"Database error while clocking out: {e}")
    except ValueError as e:
        print(f"Invalid input: {e}")


@click.command()
@click.argument("date_range", type=click.Choice(RANGE.keys()), default="m")
def clocklog(date_range):
    """Generate a report for activities between the given dates."""
    try:
        start_date, end_date = get_date_range(date_range)

        query = """
            SELECT
                category,
                strftime('%W', start_time) AS week_of_year, -- Week of the year
                CASE CAST(strftime('%w', start_time) AS INTEGER)
                    WHEN 0 THEN 7  -- Sunday becomes 7
                    ELSE CAST(strftime('%w', start_time) AS INTEGER)
                END AS day_of_week,
                COALESCE(SUM(duration), 0) as total_duration
            FROM timelog
            WHERE date(start_time) BETWEEN ? AND ?
            GROUP BY category, week_of_year, day_of_week
            ORDER BY week_of_year, category, day_of_week
        """
        result = execute_query(query, (start_date, end_date))

        if result:
            week_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
            for category, week, day, duration in result:
                week_data[int(week)][int(day)][category] = int(duration)

            headers = [
                "MONDAY",
                "TUESDAY",
                "WEDNESDAY",
                "THURSDAY",
                "FRIDAY",
                "SATURDAY",
                "SUNDAY",
            ]

            # Prepare the report for each week
            for week in sorted(week_data.keys()):
                print(f"\nWeek {week+1}:")

                # Find all unique categories for this week
                all_categories = set(
                    category
                    for day_data in week_data[week].values()
                    for category in day_data.keys()
                )

                table = []
                for category in sorted(all_categories):
                    row = []
                    for day in range(1, 8):
                        duration = week_data[week][day].get(category, 0)
                        if duration > 0:
                            row.append(f"{category}:\n{str(timedelta(seconds=duration))}")
                        else:
                            row.append("")
                    table.append(row)

                print(tabulate(table, headers=headers, tablefmt="grid"))

            # Grand total for the entire month
            grand_total = sum(
                duration
                for week_data_week in week_data.values()
                for day_data in week_data_week.values()
                for duration in day_data.values()
            )
            if grand_total > 0:
                print(f"\nTotal time for {RANGE[date_range]} ({start_date} to {end_date}): {str(timedelta(seconds=grand_total))}")

        else:
            print("No activities found in the specified date range.")
    except DatabaseError as e:
        print(f"Database error while generating report: {e}")
    except ValueError as e:
        print(f"Invalid input: {e}")



@click.command()
@click.argument("date_range", type=click.Choice(RANGE.keys()), default="w")
def clocksum(date_range):
    """Generate a nested summary report of activities by category between the given dates"""
    start_timer = perf_counter()
    try:
        start_date, end_date = get_date_range(date_range)
        query = """SELECT category, activity, task, SUM(duration) as total_duration
                        FROM timelog
                        WHERE date(start_time) BETWEEN ? AND ?
                        AND duration IS NOT NULL
                        GROUP BY category, activity, task
                        ORDER BY category, activity, total_duration DESC"""

        result = execute_query(query, (start_date, end_date))

        if result:
            headers = ["CATEGORY", "ACTIVITY", "TASK", "DURATION"]
            table = []
            summary_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

            # Organize data into nested dictionary
            for category, activity, task, duration in result:
                summary_dict[category][activity][task] = duration

            # Build the table
            for category, activities in summary_dict.items():
                category_total = sum(
                    sum(tasks.values()) for tasks in activities.values()
                )
                table.append([category, "", "", str(timedelta(seconds=category_total))])

                for activity, tasks in activities.items():
                    activity_total = sum(tasks.values())
                    table.append(
                        ["", activity, "", str(timedelta(seconds=activity_total))]
                    )

                    for task, duration in tasks.items():
                        table.append(["", "", task, str(timedelta(seconds=duration))])

            total_duration = sum(
                sum(sum(tasks.values()) for tasks in activities.values())
                for activities in summary_dict.values()
            )

            print(
                f"\nNested summary report for {RANGE[date_range]} ({start_date} to {end_date}):"
            )
            print(tabulate(table, headers=headers, tablefmt="grid"))
            print(f"\nTotal duration: {str(timedelta(seconds=total_duration))}")
            print(f"\nReport generated in {perf_counter() - start_timer:.2f} seconds")
        else:
            print("No activities found in the specified date range.")
    except DatabaseError as e:
        print(f"An error occurred while fetching the summary: {e}")
    except ValueError as e:
        print(f"Invalid input: {e}")


COLOR_DICT = config.get("color_dict", {})


@click.command()
@click.argument("date_range", type=click.Choice(RANGE.keys()), default="w")
@click.argument("category", required=False)
def clockvis(date_range, category=None):
    """Visualize the time distribution for the activities between the given dates."""
    try:
        init_db()  # Ensure database exists
        data = load_data()

        if data.empty:
            print("No data available for visualization.")
            return

        if category is not None:
            category = validate_input(category)

        fig_path = make_pie_chart(data, date_range, category)

        if fig_path is not None:
            try:
                open_file(fig_path)
            except subprocess.SubprocessError as e:
                print(f"Error opening visualization: {e}")
                print(f"File saved at: {fig_path}")
        else:
            print(
                "No data available for visualization in the specified date range and/or category."
            )
    except DatabaseError as e:
        print(f"Database error while creating visualization: {e}")
    except ValueError as e:
        print(f"Invalid input: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise


config["color_dict"] = COLOR_DICT
save_config(config)


@click.command()
@click.argument("start_date", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.argument("end_date", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--category", help="Optional category filter")
def clockcsv(start_date, end_date, category=None):
    """Generate a CSV file for the activities between the given dates."""
    try:
        if end_date < start_date:
            raise ValueError("End date must be after start date")

        # Prepare query and parameters
        base_query = """
            SELECT
                id, category, activity, task,
                start_time, end_time, duration, notes
            FROM timelog
            WHERE date(start_time) BETWEEN ? AND ?
            AND duration IS NOT NULL
        """

        params = [start_date.date(), end_date.date()]

        if category:
            category = validate_input(category)
            query = base_query + " AND category = ? ORDER BY id"
            params.append(category)
        else:
            query = base_query + " ORDER BY id"

        # Execute query
        activities = execute_query(query, tuple(params))

        if not activities:
            print("No activities found in the specified date range.")
            return

        # Prepare CSV file
        headers = [
            "ID",
            "CATEGORY",
            "ACTIVITY",
            "TASK",
            "START_TIME",
            "END_TIME",
            "DURATION",
            "NOTES",
        ]

        csv_file = (
            temp_dir
            / f"timelog_{start_date.date()}_{end_date.date()}{'_' + category if category else ''}.csv"
        )

        # Write CSV file using proper CSV handling
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for activity in activities:
                # Convert activity from sqlite3.Row to list
                writer.writerow(
                    [
                        str(value) if value is not None else ""
                        for value in dict(activity).values()
                    ]
                )

        print(f"CSV file generated: {csv_file}")

        try:
            open_file(str(csv_file))
        except subprocess.SubprocessError as e:
            print(f"Error opening CSV file: {e}")
            print(f"File saved at: {csv_file}")

    except DatabaseError as e:
        print(f"Database error while generating CSV file: {e}")
    except ValueError as e:
        print(f"Invalid input: {e}")
    except IOError as e:
        print(f"Error writing CSV file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise


clockwork.add_command(clockin)
clockwork.add_command(clockout)
clockwork.add_command(clocklog)
clockwork.add_command(clocksum)
clockwork.add_command(clockvis)
clockwork.add_command(clockcsv)


if __name__ == "__main__":
    init_db()
    clockwork()
