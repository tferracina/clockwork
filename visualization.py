import plotly.express as px
import panel as pn

from utils import load_data, df_by_range, minute_to_string

class Dashboard():
    """A class to create and update the dashboard."""
    def __init__(self):
        self.df = self.prepare_data()
        self.dashboard = self.create_dashboard()

    def prepare_data(self):
        """Prepare the data for visualization."""
        df = load_data()
        df['day'] =df['start_time'].dt.date
        df['month'] =df['start_time'].dt.to_period('M')
        df['year'] =df['start_time'].dt.to_period('Y')
        df['weekday'] = df['start_time'].dt.day_name()
        df['hour'] =df['start_time'].dt.hour
        return df

    def create_dashboard(self):
        """Create the dashboard layout."""
        return pn.Tabs(
            ('Pie', pn.Column(pn.pane.Plotly())),
            ('Bar', pn.Column(pn.pane.Plotly())),
            ('Gantt', pn.Column(pn.pane.Plotly()))
        )

    def make_pie_chart(self, date_range=None, category=None):
        """Create a pie chart based on the given date range and category."""
        # Filter the DataFrame by the given date range
        date_subdf = df_by_range(self.df, date_range[0], date_range[1]) if date_range else self.df
        start_date = date_subdf['start_time'].min().date()
        end_date = date_subdf['end_time'].max().date()

        # Filter the DataFrame by the given category
        cat_subdf = date_subdf[date_subdf['category'] == category] if category else date_subdf

        names = 'activity' if category else 'category'
        title = f"{'Category' if category is None else category} breakdown from {start_date} to {end_date}"

        fig = px.pie(
            cat_subdf,
            names=names,
            values='duration',
            color=names,
            color_discrete_sequence=px.colors.qualitative.Plotly
        )

        fig.update_traces(
            textposition='inside',
            direction='clockwise',
            hole=0.3,
            textinfo='percent+label'
        )

        total_time = cat_subdf['duration'].sum()
        formatted_tt = minute_to_string(int(total_time))

        fig.update_layout(
            uniformtext_minsize=12,
            uniformtext_mode='hide',
            title=dict(text=title, x=0.5),
            annotations=[dict(text=formatted_tt, x=0.5, y=0.5, font_size=12, showarrow=False)]
        )

        return fig

    def make_bar_chart(self, date_range=None, category=None):
        """Create a bar chart based on the given date range and category."""
        # Filter the DataFrame by the given date range
        date_subdf = df_by_range(self.df, date_range[0], date_range[1]) if date_range else self.df
        start_date = date_subdf['start_time'].min().date()
        end_date = date_subdf['end_time'].max().date()

        # Filter the DataFrame by the given category
        cat_subdf = date_subdf[date_subdf['category'] == category] if category else date_subdf

        names = 'activity' if category else 'category'
        title = f"{'Category' if category is None else category} breakdown from {start_date} to {end_date}"

        fig = px.bar(
            cat_subdf,
            x='day',
            y='duration',
            color=names,
            color_discrete_sequence=px.colors.qualitative.Plotly
        )

        fig.update_layout(
            title=dict(text=title, x=0.5),
            xaxis_title='Day',
            yaxis_title='Duration (minutes)'
        )

        return fig

    def make_gantt_chart(self, date_range=None):
        """Create a Gantt chart based on the given date range."""
        date_subdf = df_by_range(self.df, date_range[0], date_range[1]) if date_range else self.df

        fig = px.timeline(
            date_subdf,
            x_start="start_time",
            x_end="end_time",
            y="category",
            color="activity",
            hover_name="activity",
            title="Activity Timeline",
            labels={"category": "Category", "activity": "Activity"},
            color_discrete_sequence=px.colors.qualitative.Plotly
        )

        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Category",
            height=600,
            title_x=0.5,
            legend_title="Activity"
        )

        return fig

    def update_dashboard(self, start_date, end_date, category=None):
        date_range = (start_date, end_date)
        pie_chart = self.make_pie_chart(date_range, category)
        bar_chart = self.make_bar_chart(date_range, category)
        gantt_chart = self.make_gantt_chart(date_range)

        self.dashboard[0][0].object = pie_chart
        self.dashboard[1][0].object = bar_chart
        self.dashboard[2][0].object = gantt_chart

        return self.dashboard


# Create dashboard instance
dashboard = Dashboard()

# Create widgets
date_range_picker = pn.widgets.DateRangeSlider(
    name='Date Range',
    start=dashboard.df['start_time'].min().date(),
    end=dashboard.df['start_time'].max().date(),
    value=(dashboard.df['start_time'].min().date(), dashboard.df['start_time'].max().date())
)
category_select = pn.widgets.Select(name='Category', options=[''] + list(dashboard.df['category'].unique()))

# Create a function to update the dashboard
def update_dashboard_wrapper(event):
    """Update the dashboard based on the selected date range and category."""
    start_date, end_date = date_range_picker.value
    category = category_select.value
    dashboard.update_dashboard(start_date, end_date, category)

# Add callbacks to the widgets
date_range_picker.param.watch(update_dashboard_wrapper, 'value')
category_select.param.watch(update_dashboard_wrapper, 'value')

# Create the layout
layout = pn.Column(
    pn.Row(date_range_picker, category_select),
    dashboard.dashboard
)

# Initial update
update_dashboard_wrapper(None)

# Serve the Panel layout
layout.servable()
