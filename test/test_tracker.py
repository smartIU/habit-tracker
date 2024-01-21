from tracker.db import DB
from tracker.habit import Habit
from tracker.progress import Progress
from tracker.enums import TaskStatus
import tracker.request as request
import tracker.analytics as analytics

from contextlib import nullcontext
import argparse
import pytest
import os
import datetime


@pytest.fixture()
def db(tmp_path):
    """ set temp database path """
    db_path = tmp_path / "test.db"
    return DB(db_path)

@pytest.fixture(autouse=True)
def setup_and_teardown(db):       
    """ create , test, and then delete database """
    db.assure_database()
    yield
    os.remove(db._connection)
    

#region requesthandler method

@pytest.mark.parametrize(
    ("with_samples", "args", "expected_output"),
    [
        (False, argparse.Namespace(action="insert_samples"), "five predefined habits created"),        
        (False, argparse.Namespace(action="create", name="habit", task="task", period=1, goal=1, unit=""), "habit created"),
        (True, argparse.Namespace(action="update", habit=1, task="new task"), "habit updated"),
        (True, argparse.Namespace(action="progress", habit=1, start=True, end=False, amount=None), "action only valid for tasks measured in minutes"),
        (True, argparse.Namespace(action="progress", habit="sports", start=True, end=False, amount=None), "progress started"),
        (True, argparse.Namespace(action="progress", habit=3, start=False, end=True, amount=None), "progress for this habit not started"),
        (True, argparse.Namespace(action="progress", habit="morning stretching", start=False, end=False, amount=1, date=None), "progress added"),
        (True, argparse.Namespace(action="reset", habit=4), "progress reset"),
        (True, argparse.Namespace(action="delete", habit=5), "habit deleted"),
        (True, argparse.Namespace(action="list", period=None), "ID created name task period goal progress streak"),
        (True, argparse.Namespace(action="list", period=7), "ID created name task period goal progress streak"),
        (True, argparse.Namespace(action="list", period=120), "no results"),
        (True, argparse.Namespace(action="analyze", analysis="current_progress", habit=1), "habit current period progress"),
        (True, argparse.Namespace(action="analyze", analysis="current_progress", habit=6), "no habit found with id"),
        (True, argparse.Namespace(action="analyze", analysis="current_streak", habit=1), "habit current streak"),
        (True, argparse.Namespace(action="analyze", analysis="current_streak", habit="nonexisting"), "no habit found with name"),
        (True, argparse.Namespace(action="analyze", analysis="past_progress", habit=1, current_week=False, last_week=True), "period progress date amount task status"),        
        (True, argparse.Namespace(action="analyze", analysis="past_streaks", habit=1), "length from to"),
        (True, argparse.Namespace(action="analyze", analysis="max_streak", period=None, habit=None), "habit max streak from to"),
        (True, argparse.Namespace(action="analyze", analysis="max_streak", period=7, habit=None), "habit max streak from to"),
        (True, argparse.Namespace(action="analyze", analysis="max_streak", period=None, habit=1), "habit max streak from to"),
        (True, argparse.Namespace(action="analyze", analysis="max_streak", period=28, habit=None), "no results"),
        (True, argparse.Namespace(action="analyze", analysis="max_break", period=None, habit=None), "habit max break from to"),
        (True, argparse.Namespace(action="analyze", analysis="max_break", period=1, habit=None), "habit max break from to"),
        (True, argparse.Namespace(action="analyze", analysis="max_break", period=None, habit=2), "habit max break from to"),
        (True, argparse.Namespace(action="analyze", analysis="max_break", period=120, habit=None), "no results"),
        (True, argparse.Namespace(action="analyze", analysis="completion_rate", current_week=True, last_week=False), "habit completed out of rate"),
        (True, argparse.Namespace(action="analyze", analysis="completion_rate", current_week=False, last_week=True), "habit completed out of rate"),
        (True, argparse.Namespace(action="analyze", analysis="completion_rate", current_month=True, last_month=False), "habit completed out of rate"),
        (True, argparse.Namespace(action="analyze", analysis="completion_rate", current_month=False, last_month=True), "habit completed out of rate"),
    ],
)
def test_request_handler(db:DB, with_samples, args, expected_output, capfd):
    """ test the response (format) for a user request only, functional tests for db & analytics below """
    if with_samples: db.insert_samples()

    request.handle(db, args) # <- tested method
    out, err = capfd.readouterr() 

    if expected_output is None:
        assert out == ""
    else:
        output = out.split()
        expected = expected_output.split()

        for i,o in enumerate(expected):
            assert output[i] == o     

#endregion

#region test db methods

@pytest.mark.parametrize(
    ("with_samples","name", "task", "days", "goal", "unit", "context"),
    [
        (False, "Habit 1", "Task 1", None, None, None, nullcontext()),
        (False, "Habit 2", "weekly taßk", 7, None, None, nullcontext()),        
        (False, "!Habit_4", "Task 4", 30, 1, "", nullcontext()),
        (True, "Habit 0815", "Täsk", None, 5, "tests", nullcontext()),
        (True, "Habit 6", "rather long description incl. some punctuation!", None, None, "more tests", nullcontext()),
        (True, "morning stretching", "this again...", 7, 1, None, pytest.raises(Exception, match="a habit with this name already exists")),
    ],
)
def test_create_habit(db:DB, with_samples, name, task, days, goal, unit, context):
    """ test creating new habits with various parameters """
    if with_samples: db.insert_samples()

    with context:

        habit = Habit(name, task, days, goal, unit)
        habit_id = int(db.save_habit(habit)) # <- tested method

        if with_samples: assert habit_id > 5
        else: assert habit_id == 1

        if days is None: days = 1
        if goal is None: goal = 1
        if unit is None: unit = ""

        loaded_habit = db.get_habit(habit_id)

        assert loaded_habit.name == name 
        assert loaded_habit.task == task
        assert loaded_habit.days == days
        assert loaded_habit.goal == goal
        assert loaded_habit.unit == unit
    
   
@pytest.mark.parametrize(
    ("id","field", "value", "context"),
    [
        (1, "name", "new habit name", nullcontext()),
        ("morning stretching", "task", "new habit task", nullcontext()),
        ("sports", "days", 120, nullcontext()),
        (4, "goal", 300, nullcontext()),
        (5, "unit", "units", nullcontext()),
        (3, "name", "morning stretching", pytest.raises(Exception, match="a habit with this name already exists")),
    ],
)
def test_update_habit(db:DB, id, field, value, context):
    """ test updating habit attributes """
    db.insert_samples()

    with context:

        habit = db.get_habit(id)

        if field == "name": habit.name = value
        if field == "task": habit.task = value
        if field == "days": habit.days = value
        if field == "goal": habit.goal = value
        if field == "unit": habit.unit = value

        db.save_habit(habit) # <- tested method

        loaded_habit = db.get_habit(id)

        assert loaded_habit.name == habit.name
        assert loaded_habit.task == habit.task
        assert loaded_habit.days == habit.days
        assert loaded_habit.goal == habit.goal
        assert loaded_habit.unit == habit.unit

    
@pytest.mark.parametrize(
    ("habit_1", "habit_2", "context"),
    [
        (1,2, nullcontext()),        
        (2,"sports", nullcontext()),        
        (3,"sports", pytest.raises(Exception, match="progress for this habit already started")),
    ],
)
def test_start_progress(db:DB, habit_1, habit_2, context):
    """ test starting a progress (nothing to assert until calling end_progress) """
    db.insert_samples()

    with context:

        db.start_progress(habit_1) # <- tested method
        db.start_progress(habit_2) # <- tested method


@pytest.mark.parametrize(
    ("habit_1", "habit_2", "habit_3", "habit_4", "context"),
    [
        (4,5,4,5, nullcontext()),        
        (4,"sports","sports",4, nullcontext()),
        (1,2,1,3, pytest.raises(Exception, match="progress for this habit not started")),
        (3,4,3,3, pytest.raises(Exception, match="progress for this habit not started")),
    ],
)
def test_end_progress(db:DB, monkeypatch, habit_1, habit_2, habit_3, habit_4, context):
    """ test updating a progress after faked 5 minutes past """
    db.insert_samples()

    with context:

        progress_1 = db.get_habit(habit_1, True).current_progress()
        progress_2 = db.get_habit(habit_2, True).current_progress()

        db.start_progress(habit_1)
        db.start_progress(habit_2)

        ### override datetime.now() in db.end_progress()

        end_time = datetime.datetime.now() + datetime.timedelta(minutes=5)

        class mydatetime(datetime.datetime):

            @classmethod
            def now(cls): return end_time

        monkeypatch.setattr(datetime, 'datetime', mydatetime)
    
        ###

        minutes = db.end_progress(habit_3) # <- tested method
        assert minutes == 5
        minutes = db.end_progress(habit_4) # <- tested method
        assert minutes == 5

        new_progress_1 = db.get_habit(habit_1, True).current_progress()
        new_progress_2 = db.get_habit(habit_2, True).current_progress()

        assert int(new_progress_1.split()[0]) > int(progress_1.split()[0])
        assert int(new_progress_2.split()[0]) > int(progress_2.split()[0])


@pytest.mark.parametrize(
    ("goal", "unit", "progress", "expected_before", "expected_after"),
    [        
        (1,None,1,TaskStatus(0).name, TaskStatus(1).name),
        (1,"unit",5,TaskStatus(0).name, TaskStatus(1).name),        
        (100,None,1,"0 of 100", "1 of 100"),
        (100,None,150,"0 of 100", "150 of 100"),        
        (5,"tests",5,"0 of 5 tests", "5 of 5 tests"),
    ],
)
def test_add_get_and_reset_progress(db:DB, goal, unit, progress, expected_before, expected_after):
    """ test adding and reseting progress, and assert the formatted output from habit class"""
    untouched = Habit("untouched", "task")
    db.save_habit(untouched)
    db.add_progress(Progress("untouched", 1))

    untouched_progress = db.get_habit(1, True).current_progress()

    assert untouched_progress == TaskStatus(1).name

    habit = Habit("habit", "task", 1, goal, unit)
    db.save_habit(habit)

    before = db.get_habit("habit", True).current_progress()
   
    assert before == expected_before

    db.add_progress(Progress("habit", progress)) # <- tested method

    after = db.get_habit("habit", True).current_progress() # <- tested method

    assert after == expected_after
    
    db.reset_progress("habit") # <- tested method

    before = db.get_habit("habit", True).current_progress() # <- tested method

    assert before == expected_before

    untouched_progress = db.get_habit(1, True).current_progress()

    assert untouched_progress == TaskStatus(1).name


def test_delete_habit(db:DB):
    """ test deleting habits """
    db.insert_samples()
    
    count = len(list(db.get_habits()))

    assert count == 5

    db.delete_habit(4) # <- tested method

    count = len(list(db.get_habits()))

    assert count == 4

    db.delete_habit("sports") # <- tested method

    count = len(list(db.get_habits()))
    
    assert count == 3

    existing = db.get_habit(1)
    existing = db.get_habit(2)
    existing = db.get_habit(5)

#endregion

#region test analytics methods

def _insert_progress(db : DB, habit_id : int, period : int, past_progress):
    """ helper method to insert progress from test parameter """
    if period == 30:
        start_date = datetime.date.today().replace(day=1) - datetime.timedelta(days=1) #end of last month
    elif period == 7:
        start_date = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday()) - datetime.timedelta(days=1) #last sunday
    else:
        start_date = datetime.date.today() - datetime.timedelta(days=period)

    for i,p in enumerate(past_progress):
        if p > 0:
            progress = Progress(habit_id, p, (start_date - datetime.timedelta(days=i*(32 if period == 30 else period))))
            db.add_progress(progress)


@pytest.mark.parametrize(
    ("period", "expected_count"),
    [
        (None, 5),
        (-7, 0),
        (1, 1),
        (5, 0),
        (7, 2),
        (14, 1),
        (30, 1),       
    ],
)
def test_list_habits(db:DB, period, expected_count):
    """ test getting the extended list of habits, with and without period filter """
    db.insert_samples()

    count = len(analytics.habits(db, period)) # <- tested method

    assert count == expected_count


@pytest.mark.parametrize(
    ("period", "past_progress", "current_progress", "count_before", "expected_before", "count_after", "expected_after"),
    [
        (1,(0,0,1,0),1,0,"not on a streak",1,"streak of 1"),
        (1,(1,0,1,0),1,1,"streak of 1",2,"streak of 2"),
        (1,(1,1,0,1),1,2,"streak of 2",3,"streak of 3"),
        (7,(0,0,0,0),1,0,"not on a streak",1,"streak of 1"),
        (7,(1,0,1,0),1,1,"streak of 1",2,"streak of 2"),
        (7,(1,1,0,1),1,2,"streak of 2",3,"streak of 3"),
        (14,(0,0,1,0),1,0,"not on a streak",1,"streak of 1"),
        (14,(1,0,5,0),1,1,"streak of 1",2,"streak of 2"),
        (14,(1,1,0,1),1,2,"streak of 2",3,"streak of 3"),
        (30,(0,0,1,0),1,0,"not on a streak",1,"streak of 1"),
        (30,(1,0,1,1),1,1,"streak of 1",2,"streak of 2"),
        (30,(1,5,0,1),1,2,"streak of 2",3,"streak of 3"),
    ],
)
def test_current_progress(db:DB, period, past_progress, current_progress, count_before, expected_before, count_after, expected_after):
    """ test current streak output from habit class & analytics """
    habit = Habit("habit", "task", period)
    db.save_habit(habit)
    
    _insert_progress(db, 1, period, past_progress)
    
    habit = db.get_habit(1, True)
    streak = habit.current_streak() # <- tested method
    count = analytics.current_streak(db,1) # <- tested method

    assert streak.startswith(expected_before)
    assert count_before == count

    progress = Progress(1, current_progress)
    db.add_progress(progress)

    habit = db.get_habit(1, True)
    streak = habit.current_streak() # <- tested method
    count = analytics.current_streak(db,1) # <- tested method

    assert streak.startswith(expected_after)
    assert count_after == count


@pytest.mark.parametrize(
    ("period", "goal", "amount", "status"),
    [
        (1, 1, 1,(TaskStatus(1).name, TaskStatus(2).name)),      
        (1, 2, 1,(TaskStatus(0).name, TaskStatus(1).name, TaskStatus(2).name)),
        (7, 2, 1,(TaskStatus(0).name, TaskStatus(1).name, TaskStatus(2).name, TaskStatus(2).name)),
        (14, 25, 10,(TaskStatus(0).name, TaskStatus(0).name, TaskStatus(1).name, TaskStatus(2).name)),
        (30, 28, 7,(TaskStatus(0).name, TaskStatus(0).name, TaskStatus(0).name, TaskStatus(1).name, TaskStatus(2).name)),
    ],
)
def test_past_progress(db:DB, period, goal, amount, status):
    """ test past progress output """
    habit = Habit("habit", "task", period, goal)
    db.save_habit(habit)
   
    trim_date = period == 1
    
    assert len(analytics.past_progress(db, 1, trim_date)) == 0  # <- tested method

    for i,stat in enumerate(status):       
        progress = Progress(1, amount, datetime.datetime.today() + datetime.timedelta(seconds=i))
        db.add_progress(progress)
        
        result = analytics.past_progress(db, 1, trim_date)  # <- tested method

        assert result[0][3] == stat
        assert len(result) == (i + 1)


@pytest.mark.parametrize(
    ("period", "past_progress", "expected_streak", "expected_break"),
    [
        (1,(0,0,0,0,0,1,0,0,0),1,1),
        (1,(0,0,0,0,0,1,3,1,1),1,1),        
        (1,(1,1,1,0,1,1,1,0,0),2,1),
        (1,(1,1,1,2,1,1,1,1,1),1,0),
        (5,(0,0,1,0,4,1,1,0,1),3,3),
        (7,(0,0,0,0,0,1,0,0,0),1,1),
        (7,(0,0,6,0,1,1,1,0,1),3,3),
        (7,(0,0,0,0,0,0,0,0,0),0,0),
        (14,(1,1,1,1,1,2,3,4,1),1,0), 
        (30,(0,1,0,1,0,2,0,4,1),4,4), 
    ],
)
def test_past_streaks(db:DB, period, past_progress, expected_streak, expected_break):
    """ test output for past streaks and breaks """
    habit = Habit("habit", "task", period)
    db.save_habit(habit)
    
    _insert_progress(db, 1, period, past_progress)

    result = analytics.past_streaks(db,1) # <- tested method

    count_streak = len(list(filter(lambda sb: sb[0] == "streak", result)))
    count_break = len(list(filter(lambda sb: sb[0] == "break", result)))

    assert count_streak == expected_streak
    assert count_break == expected_break

    
@pytest.mark.parametrize(
    ("period", "past_progress_1", "past_progress_2", "expected_streak_period", "expected_break_period", "expected_streak_1", "expected_break_1", "expected_streak_2", "expected_break_2"),
    [
        (1,(0,1,1,1),(1,0,0,1),3,2,3,1,1,2),       
        (5,(1,1,1,1,0,0,1,0,1,1),(1,1,0,1),4,2,4,2,2,1),
        (7,(1,0,0,0,5,0,1),(3,2,1),3,3,1,3,3,None),
        (30,(0,0,1,0,5),(1,2),2,2,1,2,2,None),
        (30,(1,1),(0,0),2,None,2,None,None,None),
        (14,(0,0),(0,0),None,None,None,None,None,None),
    ],
)
def test_max_streaks(db:DB, period, past_progress_1, past_progress_2, expected_streak_period, expected_break_period, expected_streak_1, expected_break_1, expected_streak_2, expected_break_2):
    """ test output for max streaks and breaks """
    habit_1 = Habit("habit 1", "task", period)
    db.save_habit(habit_1)
   
    _insert_progress(db, 1, period, past_progress_1)

    habit_2 = Habit("habit 2", "task", period)
    db.save_habit(habit_2)
   
    _insert_progress(db, 2, period, past_progress_2)

    streak_period = analytics.max_streak(db,period_days=period) # <- tested method
    streak_1 = analytics.max_streak(db,habit=1) # <- tested method
    streak_2 = analytics.max_streak(db,habit=2) # <- tested method

    if expected_streak_period is None: assert len(streak_period[0]) == 0
    else: assert streak_period[0][1] == expected_streak_period

    if expected_streak_1 is None: assert len(streak_1[0]) == 0
    else: assert streak_1[0][1] == expected_streak_1

    if expected_streak_2 is None: assert len(streak_2[0]) == 0
    else: assert streak_2[0][1] == expected_streak_2

    break_period = analytics.max_break(db,period_days=period) # <- tested method
    break_1 = analytics.max_break(db,habit=1) # <- tested method
    break_2 = analytics.max_break(db,habit=2) # <- tested method       

    if expected_break_period is None: assert len(break_period[0]) == 0
    else: assert break_period[0][1] == expected_break_period

    if expected_break_1 is None: assert len(break_1[0]) == 0
    else: assert break_1[0][1] == expected_break_1

    if expected_break_2 is None: assert len(break_2[0]) == 0
    else: assert break_2[0][1] == expected_break_2


@pytest.mark.parametrize(
    ("period", "past_progress", "expected_completed", "expected_total"),
    [
        (1,(0,0,0,0,0,1),1,7),
        (5,(0,1,0,2,0,4,0,3),4,9),
        (7,(0,1),1,3),
        (14,(3,2,1),3,4),
        (30,(1,0,0,0,10,1),3,7),
    ],
)
def test_completion_rate(db:DB, period, past_progress, expected_completed, expected_total):
    """ test output for past streaks and breaks """
    habit = Habit("habit", "task", period)
    db.save_habit(habit)
    
    _insert_progress(db, 1, period, past_progress)

    result = analytics.completion_rate(db)[0] # <- tested method
    
    assert result[1] == expected_completed
    assert result[2] == expected_total

#endregion