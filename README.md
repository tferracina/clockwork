# Clocker: simple CLI time tracker

An easy way to track your time spent on different tasks.

## Installation

### Option 1: Using the Executable (Recommended for non-technical users)

1. Go to the [Releases](https://github.com/tferracina/timetrack/releases) page of this repository.
2. Download the latest version of the `clocker` executable for your operating system.
3. Place the executable in a convenient location on your computer.

### Option 2: Running from Source

If you prefer to run the script directly, you'll need Python installed on your system.

1. Clone this repository or download the source code.
2. Install the required dependencies: `pip install -r requirements.txt`


## Usage

If you're using the executable, replace `python clocker.py` with the path to the executable in the following commands.

The command `clockin` is how you start tracking the time. You must provide a category, activity, and a task. In addition, there is also a section for notes to be provided.
```
clockin category activity task --notes:(optional)
```
Some examples:
```
clockin study exercise physics
clockin coding timetrack testing --notes "test"
clockin work research image-preprocessing-tools
```

When you're done, stop the clock by using the `clockout` command, which also has an optional section for notes.
```
clockout --notes:(optional)
```

To see the log of your hours, you can use the `clocklog` command.
```
clocklog start-date end-date
clocklog 2024-01-01 2024-12-31
```

To see a visualization of your hours, use the `clockvis` command.
```
clockvis stard-date end-date
clockvis 2024-01-01 2024-12-31
```


To be implemented:
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
alias clockin='path/to/python path/to/clocker.py clocklog'
```
And finally restart your terminal with:
```
source ~/.zshrc
```

This step is optional but can make the commands shorter and easier to use.