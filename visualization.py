"""
Create all the visualizations
"""

import tkinter as tk
from tkinter import ttk
import pandas as pd
import sqlite3
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from clockwork import get_db_path

class ClockworkDashboard:
    """Data Visualization Dashboard"""
    def __init__(self, master):
        """Initialize main window"""
        self.master = master
        self.master.title("Data Dashboard")
        self.master.geometry("800x600")

        # Connect to DB
        self.conn = sqlite3.connect(get_db_path())

        # Create tabs
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(expand=True, fill='both')

        self.summary_tab = ttk.Frame(self.notebook)
        self.graph_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.summary_tab, text="Summaries")
        self.notebook.add(self.graph_tab, text="Graphs")

        self.create_summary_tab()
        self.create_graph_tab()

    def create_summary_tab(self):
        """Create the summary tab"""

        # Fetch summary data
        data = self.get_data()

        total_hours = data['duration'].sum() / 3600
        avg_daily_hours = total_hours / data['start_time'].dt.date.nunique()
        most_common_task = data['task'].mode().iloc[0]

        summary_text = f"""
        Total Hours Logged: {total_hours:.2f}
        Average Daily Hours: {avg_daily_hours:.2f}
        Most Common Task: {most_common_task}
        """

        summary_label = ttk.Label(self.summary_tab, text=summary_text, justify=tk.LEFT, padding=20)
        summary_label.pack()

    def create_graph_tab(self):
        """Create a bar plot based on dates"""

        data = self.get_data()

        fig = plt.figure(figsize=(12, 10))

        # Hours by Days
        ax1 = fig.add_subplot(221)
        daily_hours = data.groupby(data['start_time'].dt.date)['duration'].sum() / 3600
        daily_hours.plot(kind='bar', ax=ax1)
        ax1.set_title("Hours by Days")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Hours")
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        plt.tight_layout()

        # Task Distribution
        ax2 = fig.add_subplot(222)
        data['task'].value_counts().plot(kind='pie', ax=ax2, autopct='%1.1f%%')
        ax2.set_title("Task Distribution")
        plt.tight_layout()

        # Hours by Weekday
        ax3 = fig.add_subplot(223)
        weekday_hours = data.groupby(data['start_time'].dt.weekday)['duration'].sum() / 3600
        weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekday_hours.index = [weekday_names[i] for i in weekday_hours.index]
        weekday_hours.plot(kind='bar', ax=ax3)
        ax3.set_title("Hours by Weekday")
        ax3.set_xlabel("Weekday")
        ax3.set_ylabel("Total Hours")
        plt.tight_layout()

        # Hourly Distribution
        ax4 = fig.add_subplot(224)
        hourly_dist = data.groupby(data['start_time'].dt.hour)['duration'].sum() / 3600
        hourly_dist.plot(kind='line', ax=ax4)
        ax4.set_title("Hourly Distribution")
        ax4.set_xlabel("Hour of Day")
        ax4.set_ylabel("Total Hours")

        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.graph_tab)
        canvas.draw()
        canvas.get_tk_widget().pack()

    def get_data(self):
        """Query all the data from database"""
        query = """
        SELECT *
        FROM timelog
        ORDER BY start_time
        """
        df = pd.read_sql_query(query, self.conn)
        df['start_time'] = pd.to_datetime(df['start_time'])
        return df



if __name__ == '__main__':
    root = tk.Tk()
    dashboard = ClockworkDashboard(root)
    root.mainloop()