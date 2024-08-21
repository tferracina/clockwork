# clockwork: simple CLI time tracker (v1.0.1)

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

clockwork stores its data in a SQLite database located in a .clockwork directory in your home folder. The file timelog.db will be created to keep track of your logs.


## Usage

If you're using the executable, replace `python clockwork.py` with the path to the executable in the following commands.

### clockin

The command `clockin` is how you start tracking the time. You must provide a category, activity, and a task. Optionally, add notes with `--notes`.
```
clockin category activity task --notes "optional notes"
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
clockout activity --notes "optional notes"
```
Example:
```
clockout physics --notes "finished exercise set 3"
```

### clocklog

Displays the log of your tracked hours. A date range can be provided, if not, your full log will be returned. Format in YYYY-MM-DD
```
clocklog start-date end-date
clocklog 2024-01-01 2024-12-31
```

### clockvis

Saves a visualization of your hours for a specified date range. Format in YYYY-MM-DD
In addition, a category can be specified with --category

In a config.py file, it is possible to create a COLOR_DICT to specify what colors you prefer for different categories.
```
clockvis stard-date end-date
clockvis 2024-01-01 2024-12-31 --category coding

COLOR_DICT = {"school": "green", "personal": "yellow"}
```

### clockcsv

Download your logs in csv format with a specified date range. Format in YYYY-MM-DD
In addition, a category can be specified with --category
```
clockcsv stard-date end-date
clockcsv 2024-01-01 2024-12-31 --category coding
```


### Future Features:
```
clocklog daily
clocklog weekly
clocklog monthly
```


## Creating Aliases

To make the commands shorter, you can create aliases. This step is optional, especially if you're using the executable.

On macos using zsh:
```
open ~/.zshrc
```
Then add an alias as:
```
alias clockin='path/to/python path/to/clockwork.py clockin'
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
