from enum import Enum

class TaskStatus(Enum):
    """ uniform naming of task status  """
    incomplete = 0
    completed = 1
    exceeded = 2

class Action(Enum):
    """ description of available user actions """
    create = "create a new habit"
    insert_samples = "insert a set of predefined habits incl. random progress"
    update = "update a habit"
    progress = "check off or progress the task for a habit"
    reset = "reset all progress for a habit"
    delete = "delete a habit"
    list = "list existing habits"
    analyze = "analyze habits"
    exit = "exit the application"

class Analysis(Enum):
    """ description of available analyses """
    current_progress = "get the current progress info for a habit"
    current_streak = "get the current streak info for a habit"
    past_progress= "get a list of progress updates for a habit"
    past_streaks = "get a list of past streaks and breaks for a habit"
    max_streak = "get the longest streak"
    max_break = "get the longest break"
    completion_rate = "get completion rates for a given timeframe"

class Parameter(Enum):
    """ description of available parameters """
    habit = "id or name of the habit"
    habit_filter = "filter by id or name of a habit"
    name = "short name of the habit"
    new_name = "new name of the habit"
    task = "imperative task description"
    new_task = "new task description"
    period = "period length (accepts a number of days as well as 'day', 'week' or 'month')"
    period_filter = "filter by period length (accepts a number of days as well as 'day', 'week' or 'month')"
    new_period = "new period length"
    goal = "required amount of progress per period to complete task"
    unit = "unit of progress, e.g., minutes, meters, pages"
    amount = "amount of progress"
    past_date = "date of progress already achieved in the past"
    progress_amount = "progress the task"
    start_progress = "start measuring minutes whilst you are progressing the task"
    end_progress = "update the task by the elapsed minutes since calling 'start'"
    current_week = "analyze the current week"
    current_month = "analyze the current month"
    last_week = "analyze the last week"
    last_month = "analyze the last month"
    start_date = "start date of custom timeframe to analyze (including)"
    end_date = "end date of custom timeframe to analyze (including)"
    no_filter = "all"
