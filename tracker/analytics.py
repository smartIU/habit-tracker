from tracker.db import DB
from tracker.enums import TaskStatus

from datetime import date, datetime
from itertools import accumulate, groupby, filterfalse, islice

#region database access

def _habits(db : DB, period_days : int = 0):
    return db.get_habits(period_days = period_days)

def _progress(db : DB, habit, start_date : date = None, end_date : date = None):
    return db.get_progress(habit, start_date, end_date)

def _periods(db : DB, period_days : int = None, habit = None):
    return db.get_periods(period_days = period_days, habit = habit)

def _periods_between(db : DB, start_date : date, end_date : date):
    return db.get_periods_between(start_date = start_date, end_date = end_date)

#endregion

#region habits mapping

def _habit_id(habit : []) -> int:
    return habit[0]

def _habit_created(habit : []) -> str:
    return habit[1][:10]

def _habit_name(habit : []) -> str:
    return habit[2]

def _habit_task(habit : []) -> str:
    return habit[3]

def _habit_period(habit : []) -> str:
    return {1: "day", 7: "week", 30 : "month"}.get(habit[4], "{0} days".format(habit[4]))  

def _habit_goal(habit : []) -> str:
    return "{goal} {unit}".format(goal=habit[5], unit=habit[6]).rstrip()

#endregion

#region progress mapping

def _prog_period(prog : []) -> int:
    return prog[0]

def _prog_start(prog : []) -> date:
    return date.fromisoformat(prog[1])

def _prog_end(prog : []) -> date:
    return date.fromisoformat(prog[2])

def _prog_date(prog : []) -> datetime:
    return datetime.fromisoformat(prog[3])

def _prog_amount(prog : []) -> int:
    return prog[4]

def _prog_goal(prog : []) -> int:
    return prog[5]

def _prog_sum(prog : []) -> int:
    return prog[6]

def _prog_status(prog : []) -> int:
    return prog[7]

#endregion

#region periods mapping

def _period_days(period : []) -> int:
    return period[0]

def _period_habit_id(period : []) -> int:
    return period[2]

def _period_habit_name(period : []) -> str:
    return period[3]

def _period_goal(period : []) -> int:
    return period[4]

def _period_start(period : []) -> date:
    return date.fromisoformat(period[5])

def _period_end(period : []) -> date:
    return date.fromisoformat(period[6])

def _period_progress(period : []) -> int:
    return period[7]

def _period_is_completed(period : []) -> bool:
    return _period_goal(period) > 0 and _period_progress(period) >= _period_goal(period)

#endregion

#region completion rate mapping

def _comp_habit_id(comp : []) -> int:
    return comp[0]

def _comp_habit_name(comp : []) -> str:
    return comp[1]

def _comp_success(comp : []) -> int:
    return comp[2]

def _comp_count(comp : []) -> int:
    return comp[3]

def _comp_rate(comp : []) -> str:
    return "{:.2f} %".format(comp[2] * 100 / comp[3])

#endregion

#region streaks and breaks mapping

def _sb_is_streak(sb : []) -> bool:
    return sb[0]

def _sb_type(sb : []) -> str:
    return "streak" if sb[0] else "break"

def _sb_habit_id(sb : []) -> int:
    return sb[1]

def _sb_habit_name(sb : []) -> str:
    return sb[2]

def _sb_length(sb : []) -> int:
    return sb[3]

def _sb_start(sb : []) -> date:
    return sb[4]

def _sb_end(sb : []) -> date:
    return sb[5]

#endregion


def habits(db : DB, period_days : int = 0) -> list:
    """ get habits incl. current progress & streak length
    Args:
        period_days: optionally filter by length of period
    """
    return list(map(lambda h: (_habit_id(h), _habit_created(h), _habit_name(h), _habit_task(h),  _habit_period(h), _habit_goal(h),
                           current_progress(db, _habit_id(h)), current_streak(db, _habit_id(h))),
               _habits(db, period_days)))


def current_progress(db : DB, habit) -> int:
    """ returns current progress for a habit 
    Args:
        habit: habit id (int) or name (str)
    """
    return _period_progress(next(_periods(db, habit = habit), (0,) * 8))


def _count_streak(periods, count):
    # recursive implementation to comply functional programming paradigm without loading all periods
    if _period_is_completed(next(periods, (0,) * 8)):
        return _count_streak(periods, count + 1)

    return count

def current_streak(db : DB, habit) -> int:
    """ returns current streak length for a habit
    Args:
        habit: habit id (int) or name (str)
    Raises:
        RecursionError: streak length exceeds max recursion depth
    """
    return _period_is_completed(next(_periods(db, habit=habit), (0,) * 8)) + _count_streak(islice(_periods(db, habit=habit), 1, None), 0)


def _acc_progress(p1, p2):
    # current period
    if _prog_period(p1) == _prog_period(p2):
        return (*p2, _prog_sum(p1) + _prog_amount(p2), 2 if _prog_status(p1) >= 1 else (1 if _prog_sum(p1) + _prog_amount(p2) >= _prog_goal(p2) else 0))

    # new period
    return (*p2, _prog_amount(p2), 1 if _prog_amount(p2) >= _prog_goal(p2) else 0)

def _format_progress_time(p):
    # progress with time only
    return (_prog_start(p), _prog_date(p).strftime("%H:%M:%S"), _prog_amount(p), TaskStatus(_prog_status(p)).name)

def _format_progress_dates(p):
    # progress with dates
    return ("{0} to {1}".format(_prog_start(p), _prog_end(p)), _prog_date(p).strftime("%Y-%m-%d %H:%M:%S"), _prog_amount(p), TaskStatus(_prog_status(p)).name)

def _accumulate_and_format(progress, trim_date : bool) -> list:
    # accumulate progress to compute status, and format    
    return list(map(_format_progress_time if trim_date else _format_progress_dates, islice(accumulate(progress, _acc_progress, initial=(0,) * 8), 1, None)))
    
def past_progress(db : DB, habit, trim_date : bool, start_date : date = None, end_date : date = None) -> list:
    """ get individual progress for a habit, incl. task completion status
    Args:
        habit: habit id (int) or name (str)
        trim_date: only return time of progress date (for daily tasks)
        start_date: start of timeframe to analyze (including)
        end_date: end of timeframe to analyze (including)
    """     
    return list(reversed(_accumulate_and_format(_progress(db, habit, start_date, end_date), trim_date)))


def _acc_periods_to_streaks_and_breaks(sb, period):
    # consecutive streak or break
    if _sb_habit_id(sb) == _period_habit_id(period) and _sb_is_streak(sb) == _period_is_completed(period):
        return (_period_is_completed(period), _sb_habit_id(sb), _sb_habit_name(sb), _sb_length(sb) + 1, _period_start(period), _sb_end(sb))

    # new streak or break
    return (_period_is_completed(period), _period_habit_id(period), _period_habit_name(period), 1, _period_start(period), _period_end(period))

def _streaks_and_breaks(periods) -> list:
    """ returns a list of streaks and breaks
    Args:
        periods: periods to accumulate
    """   
    return list(map(lambda g: max(g[1], key=_sb_length),
               groupby(accumulate(periods, _acc_periods_to_streaks_and_breaks, initial=(False, 0, "", 0, date.today(), date.today())), lambda p: (_sb_habit_id(p), _sb_end(p)))))

def _remove_last_break(periods : list):
    """ do not count time from habit creation until first completed task as 'break' """
    if len(periods) == 0:
        return periods

    if _sb_is_streak(periods[-1]):
        return periods[1:]

    return periods[1:-1]

def past_streaks(db : DB, habit) -> list:
    """ get streaks and breaks for a given habit, skipping the current period
    Args:
        habit: habit id (int) or name (str)
    """   
    return list(map(lambda sb: (_sb_type(sb), _sb_length(sb), _sb_start(sb), _sb_end(sb)), _remove_last_break(_streaks_and_breaks(islice(_periods(db, habit=habit), 1, None)))))


def max_streak(db : DB, period_days : int = None, habit = None):
    """ get the longest streak
    Args:
        period_days: optionally filter by length of period
        habit: optionally filter by habit
    """
    return [max(filter(_sb_is_streak, _streaks_and_breaks(_periods(db, period_days, habit))),default=(),key=_sb_length)[2:]]


def max_break(db : DB, period_days : int = None, habit = None):
    """ get the longest break, skipping the current period
    Args:
        period_days: optionally filter by length of period
        habit: optionally filter by habit
    """
    return [max(filterfalse(_sb_is_streak, _remove_last_break(_streaks_and_breaks(islice(_periods(db, period_days, habit), 1, None)))),default=(),key=_sb_length)[2:]]


def _acc_periods_to_completion_rate(comp, period):
    # current habit
    if _comp_habit_id(comp) == _period_habit_id(period):
        return (_comp_habit_id(comp), _comp_habit_name(comp), _comp_success(comp) + (1 if _period_is_completed(period) else 0), _comp_count(comp) + 1)

    # next habit
    return (_period_habit_id(period), _period_habit_name(period), (1 if _period_is_completed(period) else 0), 1)

def completion_rate(db : DB, start_date : date = None, end_date : date = None):
    """ returns completion rates for all periods in a given timeframe
    Args:
        start_date: start of timeframe to analyze (including)
        end_date: end of timeframe to analyze (including)
    """
    return list(map(lambda c: (*c[1:], _comp_rate(c)), map(lambda g: max(g[1], key=_comp_count),
             filter(lambda g: g[0] > 0, groupby(accumulate(_periods(db) if start_date is None else _periods_between(db, start_date, end_date)
                                                          ,_acc_periods_to_completion_rate, initial=(0, "", 0, 0)), _comp_habit_id)))))
