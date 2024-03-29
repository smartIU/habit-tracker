# Habit Progress Tracker

A simple console application to define your personal habits and track their completion status.


## Features

- Create habits that can be checked off instantly or that need to accumulate progress over time
  - When creating your habits this is reflected by the "amount of progress required to complete the task",
    choose "1" or leave this property empty for a check-off task
- Supports daily, weekly and monthly tasks as well as freely defined periods spanning any number of days
  - Note that weekly periods always start on Mondays and monthly periods on the 1st of the month,
    whereas freely defined periods start on the day you create the respective habit
- A Lightweight SQLite database file to store your habits is created automatically upon start


## Installation

The app only requires python version 3.10 or newer to be installed on your machine.
There are no further dependecies and therefore no additional setup steps.

### Windows

Install Python from [Python Download](https://www.python.org/downloads/windows/), checking "Add Python to PATH"

or use the precompiled [release](https://github.com/smartIU/habit-tracker/releases/tag/v1.0) of the app for Windows x64.

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

Install Python from [Python Download](https://www.python.org/downloads/macos/) and follow the instructions on [How to run a python script](https://docs.python.org/3/using/mac.html)

To run the habit tracker from the Terminal window you must make sure that /usr/local/bin is in your shell search path.

To run the habit tracker from the Finder you have two options:

- Drag it to PythonLauncher

- Select PythonLauncher as the default application to open tracker.py (or any .py script) through the finder Info window and double-click it.


## Usage

Simply run the tracker.py script from the root directory

```commandline
tracker.py
```

or the tracker.exe, if you're using the precompiled release for Windows x64.

```commandline
tracker.exe
```

### First start

![start_empty](https://github.com/smartIU/habit-tracker/assets/156700437/7e917867-74bc-466e-accc-25a680da3936)

When you start the application for the first time, you have the option to either create your own habit or insert a set of predefined habits.

### Interactive mode

As soon as there is at least one habit defined, all actions of the app open up.

![list](https://github.com/smartIU/habit-tracker/assets/156700437/443a8d79-d2b0-44f4-beee-c477abf315e6)

To select an action from the menu, type the according number and press the "Enter" key.

![update](https://github.com/smartIU/habit-tracker/assets/156700437/be1a1fd1-5868-4313-8a0a-70b95a9e8cb2)

For some actions like creating or updating a habit, you have to manually enter a value. Simply follow the prompt on the screen.

You can conduct a variety of analyses with different filter options.

![completion rate](https://github.com/smartIU/habit-tracker/assets/156700437/314b9496-2dd8-4d51-bf59-8269aa8e5985)

When conducting an analysis for a specific timeframe, note that habits with a period greater than the timeframe will not be included.
For example, when analysing the last week, monthly habits will not be featured in the result.

### Command line requests

Every action from the interactive mode is also available directly via command line. Start the script or .exe with "-h" as an argument to get help for each individual command.

```commandline
tracker.py -h
```

![help](https://github.com/smartIU/habit-tracker/assets/156700437/b9c53f20-22dc-423b-8da3-f7467f4d7f87)

You can get the results in the same format as in interactive mode, for example, when querying the longest streak of all weekly habits:

![max_streak](https://github.com/smartIU/habit-tracker/assets/156700437/ba30933e-5268-4452-a3f0-93c5bea62550)

Or you can append "--json" to get results as a json object suitable for further processing, for example, if you intend to use the app as a backend for your own GUI:

![json](https://github.com/smartIU/habit-tracker/assets/156700437/8cd11983-72f2-4f2e-9bd3-db093b95732a)

For a full list of all available command line requests as well as examples on how to answer common questions like "With which habits did I struggle most last month?", please refer to the [Wiki](https://github.com/smartIU/habit-tracker/wiki).


## Test

There are 100 unit tests defined to validate every action you can perform with the app. Only parsing of the user input / creating and navigating through the interactive menu is not covered.

To run the tests by yourself, you have to first install pytest. You can use pip to achieve this:

```commandline
pip install pytest
```

Then navigate to the root of the app directory (i.e., where "tracker.py" is located) and run the following command:

```commandline
python -m pytest -v
```

Note that simply running "pytest ." without "python -m" will not work, because the test_tracker.py file is located in a subdirectory.

The output of the test should then look like this:

![pytest](https://github.com/smartIU/habit-tracker/assets/156700437/483fe94b-4f26-4e25-944e-e92b75d8cab2)


### Disclaimer

**No** part of the app or its documentation was created by or with the help of artificial intelligence.
