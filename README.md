
# Clocker: simple CLI time tracker

An easy way to track your time spent doing different tasks.




## Usage

The command `clockin` is how you start tracking the time. You must provide a category, activity, and a task. In addition, there is also a section for notes to be provided.
```
clockin category activity task notes:(optional)
```
Some examples:
```
clockin study exercise physics
clockin work research image-preprocessing-tools
```

When you're done, stop the clock by using the `clockout` command, which also has an optional section for notes.
```
clockout notes:(optional)
```

To see the log of your hours, you can use the `clocklog` command.
```
clocklog
```

To be implemented:
```
clocklog daily
clocklog weekly
clocklog monthly
```
