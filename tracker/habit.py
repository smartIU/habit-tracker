from tracker.period import Period
from tracker.enums import TaskStatus

from datetime import datetime, date

class Habit:
    """ defines a periodic habit """

    def __init__(self, name : str, task : str, days : int = 1, goal : int = 1, unit : str = ""):
        """ instanciate a habit
        Args:
            name: distinct name of the habit
            task: description of periodic task
            days: number of days in a period; 7 = weekly starting on monday, 30 = monthly starting on the first
            goal: required amount of progress per period to complete task
            unit: unit of progress, e.g., minutes, meters, pages
        """

        self._id = 0
        self._creation_date = datetime.now()        
        
        self.name = name
        self.task = task 
        self.days = days or 1
        self.goal = goal or 1
        self.unit = unit or ""      

        # only holds periods until first break to compute current_progress and current_streak
        # use analytics module for everything else
        self._current_periods: list[Period] = []


    @classmethod
    def from_db(cls, id : int, creation_date : str, name : str, task : str, days : int, goal : int, unit : str):
        """ constructor with id & date """
        
        habit = cls(name, task, days, goal, unit)
        habit._id = id
        habit._creation_date = datetime.fromisoformat(creation_date)

        return habit

    def __str__(self):
        """ human readable representation """
        return "{0} - {1}".format(self.name, self.task)


    def add_period(self, period : Period):
        """ assigns a progress to a new period 
             (should be called from DB only)
        """
        self._current_periods.append(period)


    def current_period(self):
        """ returns the formatted current period for this habit """

        if len(self._current_periods) == 0:
            return "no periods defined"

        return "{0} to {1}".format(self._current_periods[0].start_date, self._current_periods[0].end_date)


    def current_progress(self) -> str:
        """ returns the formatted progress of the current period """

        progress = 0
        if len(self._current_periods) > 0:
            progress = self._current_periods[0].progress

        if self.goal == 1:
            #check-off task
            return TaskStatus(0).name if progress == 0 else TaskStatus(1).name
        
        return "{0} of {1} {2}".format(progress, self.goal, self.unit).rstrip()


    def current_streak(self) -> str:
        """ returns formatted information about consecutive completed tasks up to the last period """
        
        start = -1
        end = 1

        for s,p in enumerate(self._current_periods):            
            if s == 0:
                if p.progress >= self.goal: end = 0
                else: continue
            elif p.progress < self.goal:
                break

            start = s

        if start == -1:
            return "not on a streak"

        return "streak of {0} from {1} to {2}".format(1 + start - end, self._current_periods[start].start_date, self._current_periods[end].end_date)