# clockwork: simple CLI time tracker (v1.1.0)

clockwork is a simple command-line interface (CLI) tool designed to help you track your time spent on different tasks. Whether you’re working on personal projects, studying, or managing work tasks, clockwork makes it simple to log and visualize your time.

## Installation

### Running from Source

You'll need Python installed on your system for this.

1. Clone this repository or download the source code.
    `git clone https://github.com/tferracina/clockwork.git`
2. Navigate to the cloned directory.
3. Install the required dependencies.
    `pip install -r requirements.txt`


## File Storage

clockwork stores its data in a SQLite database located in a .clockwork directory in your home folder. The file `timelog.db` will be created to keep track of your logs. Configuration settings are stored in `config.json` in the same directory.


## Usage

### clockin

The command `clockin` is how you start tracking the time.
You must provide a category, activity, and a task. Optionally, add notes with `--notes`.
```
python clockwork.py clockin <category> <activity> <task> [--notes "optional notes"]
```
Examples:
```
clockin study exercise physics
clockin coding timetrack testing --notes "test"
clockin work research image-preprocessing-tools
```

### clockout

The clock is stopped with `clockout` command. Provide the activity, and again, optionally add notes.
```
python clockwork.py clockout <activity> [--notes "optional notes"]
```
Example:
```
clockout physics --notes "finished exercise set 3"
```

### clocklog

Displays the log of your tracked hours. A date range can be specified using a single-letter code.
```
python clockwork.py clocklog [date_range]
```
Date range options:

`d`: daily (today)
`w`: weekly (current week)
`m`: monthly (current month)
`y`: yearly (current year)

If no date range is specified, it defaults to weekly.


### clocksum

Displays the total duration for each category. A date range can be specified using a single-letter code.
```
python clockwork.py clocksum [date_range]
```
Same date range options as clocklog. If no date range is specified, it defaults to weekly.


### clockvis

Saves a visualization of your hours for a specified date range. You must provide start and end dates in YYYY-MM-DD format.
In addition, a category can be specified with `--category`.

In a `config.json` file, it is possible to create a COLOR_DICT to specify what colors you prefer for different categories.
```
python clockwork.py clockvis --start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD> [--category <category>]
```

### clockcsv

Download your logs in CSV format with a specified date range. You must provide start and end dates in YYYY-MM-DD format.
In addition, a category can be specified with `--category`.
```
python clockwork.py clockcsv <start-date> <end-date> [--category <category>]
```


## Configuration

The `config.json` file in the `.clockwork` directory allows you to customize various aspects of the application:

- `color_dict`: Specify colors for different categories in visualizations
- `database`: Set the path for the SQLite database
- `default_date_range`: Set the default date range for reports
- `csv_export`: Configure CSV export settings
- `visualization`: Set default chart type and figure size
- `time_format`: Specify the time format used in logs
- `categories`: List of predefined categories
- `notification`: Enable and configure reminders
- `backup`: Configure automatic backups of your data

Please keep in mind some of these features still need to be implemented.


## Creating Aliases

To make the commands shorter, you can create aliases.

On macos using zsh:
```
open ~/.zshrc
```
Then add an alias as:
```
alias clockin='path/to/clockwork.py clockin'
```
And finally restart your terminal with:
```
source ~/.zshrc
```

This step is optional but can make the commands shorter and easier to use.

## Contact and Support

For issues or support, please open an issue on the [Github Issues](https://github.com/tferracina/clockwork/issues) page.

## License

This project is licensed under the MIT License.
