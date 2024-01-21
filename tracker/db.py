from tracker.habit import Habit
from tracker.period import Period
from tracker.progress import Progress

import random
import sqlite3
import datetime # do not change or pytest monkeypatch will break
from contextlib import closing

class DB:
    """ encapsulates all database requests """

    def __init__(self, connection : str):
        """ instanciate database encapsulation
        Args:
            connection: path to sqlite3 database file
        """

        self._connection = connection

    
    def _create_connection(self):
        """ returns a database connection """       
        return sqlite3.connect(self._connection)
        
    
    def assure_database(self):
        """ creates schema objects if neccessary 
        Tables:
            habit(id, name, task, creation_date, period, goal, unit)
            progress(id, habit_id, progress_date, amount)
        Index: 
            progress(habit_id, progress_date)
        View:
            period(period, nr, habit_id, goal, start_date, end_date, progress)
        """

        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                cmd.execute('''CREATE TABLE IF NOT EXISTS habit(
                               id INTEGER PRIMARY KEY
                              ,creation_date TEXT NOT NULL DEFAULT(datetime('now', 'localtime'))
                              ,name TEXT UNIQUE NOT NULL
                              ,task TEXT NOT NULL -- task description                              
                              ,period INTEGER NOT NULL DEFAULT(1)
                              ,goal INTEGER NOT NULL DEFAULT(1)
                              ,unit TEXT NOT NULL DEFAULT('')
                              )''')
            
                cmd.execute('''CREATE TABLE IF NOT EXISTS progress(
                               id INTEGER PRIMARY KEY
                              ,habit_id INTEGER NOT NULL
                              ,progress_date TEXT NOT NULL DEFAULT(datetime('now', 'localtime'))
                              ,amount INTEGER NOT NULL DEFAULT(1)
                              ,FOREIGN KEY(habit_id) REFERENCES habit(id) ON DELETE CASCADE
                              )''')

                cmd.execute('''CREATE INDEX IF NOT EXISTS INDEX_progress_habit_date ON progress(habit_id, progress_date)''')


                cmd.execute('''CREATE VIEW IF NOT EXISTS period AS                        
                                WITH RECURSIVE StartDates AS
                                (
                                   -- compute start dates for special 'weekly' and 'monthly' periods
	                               SELECT [period]
	                                    , MIN(CASE WHEN [period] = 7 THEN date(ifnull([progress_date],[creation_date]), '-6 days', 'weekday 1') --monday
			                                       WHEN [period] = 30 THEN date(ifnull([progress_date],[creation_date]), 'start of month')
			                                       ELSE date(ifnull([progress_date],[creation_date])) END) AS start_date
                                   FROM [habit]	H        
                                   LEFT OUTER JOIN [progress]  P
                                    ON P.[habit_id] = H.[id]
                                   GROUP BY [period]
                                )
                                , AlignedPeriods AS 
                                (
                                    -- generate list of all necessary periods
	                                SELECT    [period]
			                                , 1 AS nr
			                                , [start_date]
			                                , CASE WHEN [period] = 30 THEN date([start_date], '+1 month')
							                       ELSE date([start_date], ([period] || ' day')) END AS end_date					                  
	                                FROM StartDates
	                                UNION ALL
	                                SELECT    [period]		
			                                , [nr] + 1
                                            , [end_date]
			                                , CASE WHEN [period] = 30 THEN date([end_date], '+1 month')
					                               ELSE date([end_date], ([period] || ' day')) END			                         
	                                FROM     AlignedPeriods
	                                WHERE    [end_date] <= date('now', 'localtime')
                                )
                                SELECT A.[period], A.[nr], H.[id] AS habit_id, H.[name] AS habit_name, H.[goal],
                                       A.[start_date], date(A.[end_date], '-1 day') AS end_date, ifnull(SUM(P.amount), 0) AS progress
                                FROM habit H
                                INNER JOIN AlignedPeriods A
                                 ON A.[period] = H.[period]
                                LEFT OUTER JOIN [progress] P
                                 ON P.[habit_id] = H.[id]
                                AND P.[progress_date] >= A.[start_date] AND P.[progress_date] < A.[end_date]
                                GROUP BY A.[period], A.[nr], H.[id], H.[name], H.[goal], A.[start_date], date(A.[end_date], '-1 day')''')


#region mangement

    def is_empty(self) -> bool:
        """ check if database is empty """
        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:
                res = cmd.execute('''SELECT id FROM habit LIMIT 1''').fetchone()
                if res is None:
                    return True

        return False

    def _get_habit_id(self, habit) -> int:
        """ returns id of habit
        Args:
            habit: id (int) or name (str) of habit
        """
        
        if isinstance(habit, int) or (isinstance(habit, str) and habit.isdigit()):
            with closing(self._create_connection()) as conn:
                with closing(conn.cursor()) as cmd:
                    res = cmd.execute('''SELECT id FROM habit WHERE id = ?''', [habit]).fetchone()
                    if res is None:
                        raise Exception("no habit found with id {0}".format(habit))
                    return res[0]

        if isinstance(habit, str):
            with closing(self._create_connection()) as conn:
                with closing(conn.cursor()) as cmd:
                    res = cmd.execute('''SELECT id FROM habit WHERE name = ?''', [habit]).fetchone()
                    if res is None:
                        raise Exception("no habit found with name '{0}'".format(habit))
                    return res[0]

        raise TypeError("unexpected type for parameter 'habit'")


    def get_habit(self, identifier, include_current_periods : bool = False) -> Habit:
        """ returns habit from database
        Args:
            identifier: id (int) or name (str)
            include_current_periods: optionally include current periods
        """

        id = self._get_habit_id(identifier)

        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                res = cmd.execute('''SELECT * FROM habit WHERE id = ?''', [id]).fetchone()

                habit = Habit.from_db(*res)

                if include_current_periods:

                    first_period = True

                    cur = cmd.execute('''SELECT start_date, end_date, progress FROM period WHERE habit_id = ? ORDER BY start_date DESC''', [id])

                    while True:
                        res = cur.fetchmany(100)
                        if not res:
                            break

                        for row in res:
                            period = Period(*row)
                            habit.add_period(period)

                            # stop after first break of the current streak
                            if period.progress < habit.goal and not first_period:
                                break

                            first_period = False
                        else:
                            continue

                        break

                return habit


    def delete_habit(self, habit):
        """ deletes a habit incl. progress
        Args:
            habit: habit id (int) or name (str)
        """

        id = self._get_habit_id(habit)

        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                cmd.execute('''DELETE FROM habit WHERE id = ?''', [id])
                
                conn.commit()


    def save_habit(self, habit : Habit) -> int:
        """ saves a habit to the db """

        try:
            with closing(self._create_connection()) as conn:
                with closing(conn.cursor()) as cmd:

                    if habit._id == 0:

                         cmd.execute('''INSERT INTO habit (name, task, creation_date, period, goal, unit) VALUES (?, ?, ?, ?, ?, ?)''', 
                                     (habit.name, habit.task, habit._creation_date, habit.days, habit.goal, habit.unit))

                         conn.commit()

                         return cmd.lastrowid
                    else:

                         cmd.execute('''UPDATE habit SET name = ?, task = ?, period = ?, goal = ?, unit = ? WHERE id = ?''', 
                                     (habit.name, habit.task, habit.days, habit.goal, habit.unit, habit._id))

                         conn.commit()

                         return cmd.lastrowid

        except Exception as ex:
            if str(ex).startswith("UNIQUE constraint failed"):
                raise Exception("a habit with this name already exists")

            raise ex

    def add_progress(self, progress : Progress):
        """ adds progress for a habit """

        id = self._get_habit_id(progress.habit)

        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                cmd.execute('''INSERT INTO progress (habit_id, progress_date, amount) VALUES (?, ?, ?)''', (id, progress.progress_date, progress.amount))

                conn.commit()


    def start_progress(self, habit):
        """ start progress for a habit with unit 'minutes'
        Args:
            habit: habit id (int) or name (str)       
        """

        id = self._get_habit_id(habit)

        start_date = datetime.datetime.now()

        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                res = cmd.execute('''SELECT * FROM progress WHERE habit_id = ? AND amount = 0''', [id]).fetchone()

                if res != None:
                    raise Exception("progress for this habit already started")

                cmd.execute('''INSERT INTO progress (habit_id, progress_date, amount) VALUES (?, ?, ?)''', (id, start_date, 0))
                conn.commit()
                    

    def end_progress(self, habit) -> int:
        """ end progress for a habit with unit 'minutes'
        Args:
            habit: habit id (int) or name (str)
        Returns:
            progressed minutes
        """

        id = self._get_habit_id(habit)
        
        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                res = cmd.execute('''SELECT progress_date FROM progress WHERE habit_id = ? AND amount = 0''', [id]).fetchone()

                if res == None:
                    raise Exception("progress for this habit not started")

                start_date = datetime.datetime.fromisoformat(res[0])

                end_date = datetime.datetime.now()
                
                minutes = int((end_date - start_date).total_seconds()/60)

                cmd.execute('''UPDATE progress
                               SET progress_date = ?, amount = ?
                               WHERE habit_id = ? AND amount = 0''', (end_date, minutes, id))

                conn.commit()

                return minutes


    def reset_progress(self, habit):
        """ delete all progress for a habit
        Args:
            habit: habit id (int) or name (str)
        """
        
        id = self._get_habit_id(habit)
        
        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                cmd.execute('''DELETE FROM progress WHERE habit_id = ?''', [id])
                
                conn.commit()

#endregion

#region analytics
                
    def get_habits(self, period_days : int = 0):
        """ habits generator
        Args:
            period_days: only return habits with this period length
        """

        select = 'SELECT * FROM habit'

        if period_days:
            select = select + ' WHERE period = {0}'.format(period_days)
       
        select = select + ' ORDER BY name'

        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                cur = cmd.execute(select)
             
                while True:
                    res = cur.fetchmany(10)
                    if not res:
                        break

                    for row in res:
                       yield row


    def get_progress(self, habit, start_date : datetime.date = None, end_date : datetime.date = None):
        """ progress generator
        Args:
            habit: habit id (int) or name (str)
            start_date: start of timeframe (including)
            end_date: end of timeframe (including)
        """

        id = self._get_habit_id(habit)

        select = '''SELECT P.nr, P.start_date, P.end_date, A.progress_date, A.amount, P.goal
                                     FROM progress A
                                     INNER JOIN period P
                                        ON A.habit_id = P.habit_id
                                       AND A.progress_date >= P.start_date
                                       AND A.progress_date < date(P.end_date, '+1 day')
                                     WHERE A.habit_id = ?'''

        if not start_date is None:            
            select = select + ' AND P.start_date >= ? AND P.end_date <= ?'

        select = select + ' ORDER BY A.progress_date ASC'

        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                cur = cmd.execute(select, [id] if start_date is None else (id, start_date, end_date))
             
                while True:
                    res = cur.fetchmany(10)
                    if not res:
                        break

                    for row in res:
                       yield row


    def get_periods(self, period_days : int = None, habit = None):
        """ periods generator
        Args:
            period_days: only return periods with this length
            habit: only return periods for this habit
        """      

        select = 'SELECT * FROM period'

        if habit:
            id = self._get_habit_id(habit)
            select = select + ' WHERE habit_id = {0}'.format(id)
        elif period_days:
            select = select + ' WHERE period = {0}'.format(period_days)
       
        select = select + ' ORDER BY habit_id, start_date DESC'

        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                cur = cmd.execute(select)

                while True:
                    res = cur.fetchmany(10)
                    if not res:
                        break

                    for row in res:
                       yield row


    def get_periods_between(self, start_date : datetime.date, end_date : datetime.date):
        """ periods generator for given timeframe
        Args:
            start_date: start of timeframe (including)
            end_date: end of timeframe (including)
        """

        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                cur = cmd.execute('''SELECT * FROM period 
                                     WHERE start_date >= ? AND end_date <= ?
                                     ORDER BY habit_id, start_date DESC''', (start_date, end_date))

                while True:
                    res = cur.fetchmany(10)
                    if not res:
                        break

                    for row in res:
                       yield row

#endregion

#region sample data

    def _insert_random_progress(self, habit, min_progress : int, max_progress : int, success_rate : int, start_date : datetime.date, days : int):
        """ inserts random progress for a given habit
        Args:
            habit: habit id (int) or name (str)
            max_progress: maximum amount of progress to insert per day
            succes_rate: percentage of days where any progress is made (0-100)
            start_date: first date to potentially insert progress
            days: number of days after start_date to potentially insert progress
        """

        id = self._get_habit_id(habit)

        with closing(self._create_connection()) as conn:
            with closing(conn.cursor()) as cmd:

                progress = []

                for i in range(days):
                    if random.randrange(100) < success_rate:                        
                        progress.append((id, (start_date + datetime.timedelta(days=i, hours=random.randrange(1, 22), minutes=random.randrange(1, 58))), random.randrange(min_progress, max_progress + 1)))

                cmd.executemany('''INSERT INTO progress (habit_id, progress_date, amount) VALUES (?, ?, ?)''', progress)

                conn.commit()
    
    def _insert_sample_habit(self, habit : Habit, days : int, min_progress : int, max_progress : int, success_rate : int):
        """ helper method to create habit with random progress in the past """

        today = datetime.datetime.today()
        start_date = datetime.datetime(today.year,today.month,today.day) - datetime.timedelta(days=days)

        habit_id = self.save_habit(habit)
        self._insert_random_progress(habit_id, min_progress, max_progress, success_rate, start_date, days)

    def insert_samples(self):
        """ inserts 5 predefined habits """

        habit = Habit('morning stretching', 'stretch before breakfast', 1, 1, '')
        self._insert_sample_habit(habit, 100, 1, 1, 75)

        self.add_progress(Progress(1))

        habit = Habit('veggy day', 'survive a whole day without meat', 7, 1, '')
        self._insert_sample_habit(habit, 100, 1, 1, 8)

        habit = Habit('sports', '90 minutes of sports per week', 7, 90, 'minutes')
        self._insert_sample_habit(habit, 100, 15, 90, 30)

        habit = Habit('study', 'read a minimum of pages every other week', 14, 100, 'pages')
        self._insert_sample_habit(habit, 100, 10, 50, 15)

        habit = Habit('side hustle', 'earn some extra money', 30, 250, '€')
        self._insert_sample_habit(habit, 100, 25, 250, 12)

#endregion