'''
ENHANCEMENTS:

SQLite database instead of CSV for better data management.
Support for task categories.
Ability to add notes to tasks.
Reporting functionality to view activities within a date range.
Data visualization of time distribution across categories.

HOW TO USE:
# Clock in
python time_tracker.py clockin --activity "physics/study" --category "Study" --notes "Chapter 5 review"

# Clock out
python time_tracker.py clockout --activity "physics/study"

# Generate a report
python time_tracker.py report --start_date 2024-01-01 --end_date 2024-12-31

# Visualize time distribution
python time_tracker.py visualize --start_date 2024-01-01 --end_date 2024-12-31

'''


import argparse
import datetime
import sqlite3
import os
from tabulate import tabulate
import matplotlib.pyplot as plt

DB_FILE = '/Users/tommasoferracina/tommaso/timetrack/timelog.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
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
    conn.close()

def clockin(category, activity, task, notes):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    current_time = datetime.datetime.now()
    c.execute("INSERT INTO timelog (category, activity, task, start_time, notes) VALUES (?, ?, ?, ?, ?)",
              (category, activity, task, current_time, notes))
    conn.commit()
    conn.close()
    print(f"Clocked in for {activity} ({task}) at {current_time.strftime('%H:%M:%S')}")

def clockout(activity, notes=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    current_time = datetime.datetime.now()
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
    conn.close()

def generate_report(start_date, end_date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT id, category, activity, task, start_time, end_time, duration, notes 
                 FROM timelog 
                 WHERE date(start_time) BETWEEN ? AND ?
                 ORDER BY start_time""", (start_date, end_date))
    activities = c.fetchall()
    conn.close()

    if activities:
        headers = ["ID", "CATEGORY", "ACTIVITY", "TASK", "START_TIME", "END_TIME", "DURATION", "NOTES"]
        table = [[a[0], a[1], a[2], a[3], a[4], a[5] or "Ongoing", str(datetime.timedelta(seconds=a[6])) if a[6] else "N/A", a[7]] for a in activities]
        print(tabulate(table, headers=headers, tablefmt="grid"))
    else:
        print("No activities found in the specified date range.")

def visualize_time_distribution(start_date, end_date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT category, SUM(duration) 
                 FROM timelog 
                 WHERE date(start_time) BETWEEN ? AND ? AND duration IS NOT NULL
                 GROUP BY category""", (start_date, end_date))
    data = c.fetchall()
    conn.close()

    if data:
        categories, durations = zip(*data)
        plt.pie(durations, labels=categories, autopct='%1.1f%%')
        plt.title(f"Time Distribution ({start_date} to {end_date})")
        plt.axis('equal')
        plt.show()
    else:
        print("No data available for visualization in the specified date range.")

def main():
    parser = argparse.ArgumentParser(description='Enhanced Time tracking CLI tool')
    parser.add_argument('action', choices=['clockin', 'clockout', 'report', 'visualize'], help='Action to perform')
    
    # Add subparsers for each action
    subparsers = parser.add_subparsers(dest='action')

    # Clockin subparser
    clockin_parser = subparsers.add_parser('clockin')
    clockin_parser.add_argument('category', help='Activity category')
    clockin_parser.add_argument('activity', help='Activity name')
    clockin_parser.add_argument('task', help='Task name')
    clockin_parser.add_argument('--notes', help='Additional notes for the activity')

    # Clockout subparser
    clockout_parser = subparsers.add_parser('clockout')
    clockout_parser.add_argument('activity', help='Activity name')
    clockout_parser.add_argument('--notes', help='Additional notes for the activity')

    # Report and Visualize subparsers
    for action in ['report', 'visualize']:
        action_parser = subparsers.add_parser(action)
        action_parser.add_argument('start_date', help='Start date (YYYY-MM-DD)')
        action_parser.add_argument('end_date', help='End date (YYYY-MM-DD)')

    args = parser.parse_args()
    
    if args.action == 'clockin':
        clockin(args.category, args.activity, args.task, args.notes)
    elif args.action == 'clockout':
        clockout(args.activity, args.notes)
    elif args.action == 'report':
        generate_report(args.start_date, args.end_date)
    elif args.action == 'visualize':
        visualize_time_distribution(args.start_date, args.end_date)

if __name__ == '__main__':
    if not os.path.exists(DB_FILE):
        init_db()
    main()