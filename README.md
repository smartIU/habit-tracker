# Habit Progress Tracker

A habit progress tracker for a university assignment.
Code complete.
Documentation still to be finished.

## Features

- sqlite3 database
- simple cli
- analytics

## Installation

### Windows

Install Python version 3.10 or newer from [Python Download](https://www.python.org/downloads/windows/), checking "Add Python to PATH"

or use the precompiled [release](https://github.com/smartIU/habit-tracker/releases/tag/v1.0) of the app for Windows x64

### Linux

Install Python manually from [Python Download](https://www.python.org/downloads/source/)

or use git:

```bash
# Debian-based:
sudo apt install wget git python3 python3-venv
# Red Hat-based:
sudo dnf install wget git python3
# Arch-based:
sudo pacman -S wget git python3
```

### macOS

Install Python from [Python Download](https://www.python.org/downloads/macos/) and follow the instructions on [How to run a python script](https://docs.python.org/3/using/mac.html):

To run the habit tracker from the Terminal window you must make sure that /usr/local/bin is in your shell search path.

To run the habit tracker from the Finder you have two options:

  Drag it to PythonLauncher

  Select PythonLauncher as the default application to open tracker.py (or any .py script) through the finder Info window and double-click it.

## Usage

```commandline
tracker.py
```

## Test

```commandline
python -m pytest -v
```
