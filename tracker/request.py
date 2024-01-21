import tracker.analytics as analytics
from tracker.db import DB
from tracker.habit import Habit
from tracker.progress import Progress

import argparse
import json
from datetime import timedelta, date, datetime
from calendar import monthrange


def handle(db : DB, request : argparse.Namespace):
    """ uniformly handles user request from command line or interactive session
    Args:
        db: database
        request: namespace with action plus dynamic attributes        
    """

    columns = None
    response = None

    try:

        if request.action == "insert_samples":            
            db.insert_samples()
            response = "five predefined habits created"

        elif request.action == "create":                 
            habit = Habit(request.name, request.task, request.period, request.goal, request.unit)
            db.save_habit(habit)
            response = "habit created"

        elif request.action == "update":
            habit = db.get_habit(request.habit)
            if hasattr(request, "name"): habit.name = request.name
            if hasattr(request, "task"): habit.task = request.task
            if hasattr(request, "period"): habit.days = request.request.period
            if hasattr(request, "goal"): habit.goal = request.goal
            if hasattr(request, "unit"): habit.unit = request.unit
            db.save_habit(habit)
            response = "habit updated"

        elif request.action == "progress":
            if request.start or request.end:
                habit = db.get_habit(request.habit)
                if habit.unit != "minutes":
                    response = "action only valid for tasks measured in minutes"
                else:
                    if request.start:
                        db.start_progress(request.habit)
                        response = "progress started - counting the minutes for you..."
                    else:
                        minutes = db.end_progress(request.habit)
                        response = "progress updated by {0} minutes".format(minutes)
            else:
                progress = Progress(request.habit, request.amount, request.date)
                db.add_progress(progress)
                habit = db.get_habit(request.habit, True)
                response = "progress added - new status: {0}".format(habit.current_progress())

        elif request.action == "reset":
            db.reset_progress(request.habit)
            response = "progress reset"

        elif request.action == "delete":            
            db.delete_habit(request.habit)
            response = "habit deleted"

        elif request.action == "list":
            columns = ("ID", "created", "name", "task", "period", "goal", "progress", "streak")
            response = analytics.habits(db, request.period)

        elif request.action == "analyze":

            if request.analysis == "current_progress":
                columns = ("habit", "current period", "progress")
                habit = db.get_habit(request.habit, True)
                response = [(habit.name, habit.current_period(), habit.current_progress())]

            elif request.analysis == "current_streak":
                columns = ("habit", "current streak")
                habit = db.get_habit(request.habit, True)
                response = [(habit.name, habit.current_streak())]
                
            elif request.analysis == "past_progress":
                columns = ("period", "progress date", "amount", "task status")
                habit = db.get_habit(request.habit)
                trim_date = (habit.days == 1)
                start_date, end_date = _get_timeframe(request) 
                response = analytics.past_progress(db, request.habit, trim_date, start_date, end_date)

            elif request.analysis == "past_streaks":
                columns = ("", "length", "from", "to")                
                response = analytics.past_streaks(db, request.habit)

            elif request.analysis == "max_streak":
                columns = ("habit", "max streak", "from", "to")
                response = analytics.max_streak(db, request.period, request.habit)

            elif request.analysis == "max_break":
                columns = ("habit", "max break", "from", "to")
                response = analytics.max_break(db, request.period, request.habit)

            elif request.analysis == "completion_rate":
                columns = ("habit", "completed", "out of", "rate")
                start_date, end_date = _get_timeframe(request)                
                response = analytics.completion_rate(db, start_date, end_date)

    except Exception as ex:
        response = str(ex)

    if not response or len(response) == 0 or len(response[0]) == 0:
        response = "no results"

    if hasattr(request, "json") and request.json:
        #json response
        _output_json(columns, response)
    else:
        #human readable
        if isinstance(response, str):
            print(response)
        else:
            _output_table(_create_header(columns) + response)


def _get_timeframe(request : argparse.Namespace):
    """ returns start and end date from user request """

    if (hasattr(request, "current_week") and request.current_week) or (hasattr(request, "last_week") and request.last_week):
        start_date = date.today() if request.current_week else date.today() - timedelta(days=7)
        start_date = start_date - timedelta(days=start_date.weekday()) # monday
        end_date = start_date + timedelta(days=6) 
    elif (hasattr(request, "current_month") and request.current_month) or (hasattr(request, "last_month") and request.last_month):
        start_date = date.today().replace(day=1)
        if request.last_month: 
            start_date = (start_date - timedelta(days=1)).replace(day=1)
        end_date = start_date.replace(day=monthrange(start_date.year, start_date.month)[1])
    elif hasattr(request, "start_date"):
        start_date = request.start_date
        end_date = request.end_date or date.today()
    else:
        start_date = None
        end_date = None
   
    return start_date, end_date


def _create_header(columns):
    """ creates header in the form
        col1 column2 ...
        ---- ------- ---
    """
    return [columns, tuple(map(lambda c:'-'*len(c), columns))]

def _output_table(response):
    """ outputs response as a well formed table """

    widths = [max(map(lambda c: len(str(c)), col)) for col in zip(*response)]
    widths[-1]=0
    
    for row in response:
        print("  ".join((str(val).ljust(width) for val, width in zip(row, widths))))


def _output_json(columns, response):
    """ outputs response as json """

    if isinstance(response, str):
        print(json.dumps({"result":response}))
    else:
        result = []
        for row in response:
            key = iter(columns)
            value = iter(row)
            result.append(dict(zip(key, value)))

        print(json.dumps({"result":result}))