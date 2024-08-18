import argparse
import datetime
import csv
import os

LOG_FILE = '/Users/tommasoferracina/tommaso/timetrack/time_log.csv'

def clockin(activity):
    current_time = datetime.datetime.now()
    with open(LOG_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([activity, current_time.strftime('%Y-%m-%d %H:%M:%S'), '', ''])
    print(f"Clocked in for {activity} at {current_time.strftime('%H:%M:%S')}")

def clockout():
    current_time = datetime.datetime.now()
    with open(LOG_FILE, 'r') as file:
        lines = list(csv.reader(file))
    
    if lines and lines[-1][2] == '':
        activity = lines[-1][0]
        start_time = datetime.datetime.strptime(lines[-1][1], '%Y-%m-%d %H:%M:%S')
        duration = current_time - start_time
        
        lines[-1][2] = current_time.strftime('%Y-%m-%d %H:%M:%S')
        lines[-1][3] = str(duration)
        
        with open(LOG_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(lines)
        
        print(f"Clocked out from {activity} at {current_time.strftime('%H:%M:%S')}")
        print(f"Duration: {duration}")
    else:
        print("No active clock-in found.")

def clocklog():
    if os.path.exists(LOG_FILE):
        os.system(f'code "{LOG_FILE}"')
    else:
        print("No log file found.")

def main():
    parser = argparse.ArgumentParser(description='Time tracking CLI tool')
    parser.add_argument('action', choices=['clockin', 'clockout', 'clocklog'], help='Action to perform')
    parser.add_argument('activity', nargs='?', help='Activity to clock in (required for clockin)')
    
    args = parser.parse_args()
    
    if args.action == 'clockin':
        if not args.activity:
            print("Error: Activity is required for clockin")
            return
        clockin(args.activity)
    elif args.action == 'clockout':
        clockout()
    elif args.action == 'clocklog':
        clocklog()

if __name__ == '__main__':
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['ACTIVITY', 'IN', 'OUT', 'DURATION'])
    main()