import tracker.analytics as analytics
import tracker.request as request
from tracker.db import DB
from tracker.habit import Habit
from tracker.progress import Progress
from tracker.enums import Action, Analysis, Parameter

import argparse
from datetime import date
from enum import Enum


#region parse user input

def _add_parser(parser, enum : Enum, parents=[]):
     """ add parser created from enum, where description equals help """
     return parser.add_parser(enum.name, description=enum.value, help=enum.value, parents=parents)

def _create_parser(db_is_empty : bool):
    """ parses single command line request """
    main_parser = argparse.ArgumentParser(description="Habit progress tracker - run without arguments to enter interactive mode")

    json_parser = argparse.ArgumentParser(add_help=False)
    output_group = json_parser.add_argument_group("output flag")
    output_group.add_argument("--json", help="return result as json", action='store_true')


    habit_parser = argparse.ArgumentParser(add_help=False)
    habit_parser.add_argument("habit", help=Parameter.habit.value)

    habit_filter_parser = argparse.ArgumentParser(add_help=False)
    habit_filter_parser.add_argument("-i", "--habit", help=Parameter.habit_filter.value)

    period_filter_parser = argparse.ArgumentParser(add_help=False)
    period_filter_parser.add_argument("-p", "--period", help=Parameter.period_filter.value, type=_parse_period)

    timeframe_parser = argparse.ArgumentParser(add_help=False)
    timeframe_parser.add_argument("-w", "--current_week", help=Parameter.current_week.value, action='store_true')
    timeframe_parser.add_argument("-m", "--current_month", help=Parameter.current_month.value, action='store_true')
    timeframe_parser.add_argument("-W", "--last_week", help=Parameter.last_week.value, action='store_true')
    timeframe_parser.add_argument("-M", "--last_month", help=Parameter.last_month.value, action='store_true')
    timeframe_parser.add_argument("-s", "--start_date", help=Parameter.start_date.value, type=_parse_date)
    timeframe_parser.add_argument("-e", "--end_date", help=Parameter.end_date.value, type=_parse_date)

    actions = main_parser.add_subparsers(title="action", dest="action")
    actions.required = False    

    create_parser = _add_parser(actions, Action.create, [json_parser])
    create_parser.add_argument("name", help=Parameter.name.value, type=_parse_name)
    create_parser.add_argument("task", help=Parameter.task.value, type=_parse_name)
    create_parser.add_argument("-p","--period", help=Parameter.period.value, type=_parse_period, default=1)
    create_parser.add_argument("-g","--goal", help=Parameter.goal.value, type=_parse_amount, default=1)
    create_parser.add_argument("-u","--unit", help=Parameter.unit.value, type=_parse_name, default="")

    if db_is_empty:
        # only allow samples to be inserted when empty
        _add_parser(actions, Action.insert_samples)
    else:
        # only allow rest of actions after creating at least one habit
        update_parser = _add_parser(actions, Action.update, [json_parser, habit_parser])
        update_parser.add_argument("-n", "--name", help=Parameter.new_name.value, type=_parse_name)
        update_parser.add_argument("-t", "--task", help=Parameter.new_task.value, type=_parse_name)
        update_parser.add_argument("-p","--period", help=Parameter.new_period.value, type=_parse_period)
        update_parser.add_argument("-g","--goal", help=Parameter.goal.value, type=_parse_amount)
        update_parser.add_argument("-u","--unit", help=Parameter.unit.value, type=_parse_name)
      
        progress_parser = _add_parser(actions, Action.progress, [json_parser, habit_parser])
        progress_parser.add_argument("-a", "--amount", help=Parameter.amount.value, type=_parse_amount, default=1)
        progress_parser.add_argument("-d", "--date", help=Parameter.past_date.value, type=_parse_date)
        progress_parser.add_argument("-s", "--start", help=Parameter.start_progress.value, action='store_true')
        progress_parser.add_argument("-e", "--end", help=Parameter.end_progress.value, action='store_true')       

        _add_parser(actions, Action.reset, [json_parser, habit_parser])
        _add_parser(actions, Action.delete, [json_parser, habit_parser])
        _add_parser(actions, Action.list, [json_parser, period_filter_parser])

        analyze_parser = _add_parser(actions, Action.analyze)

        analyses = analyze_parser.add_subparsers(title="analysis", dest="analysis")    
        _add_parser(analyses, Analysis.current_progress, [json_parser, habit_parser])
        _add_parser(analyses, Analysis.current_streak, [json_parser, habit_parser])
        _add_parser(analyses, Analysis.past_progress, [json_parser, habit_parser, timeframe_parser])
        _add_parser(analyses, Analysis.past_streaks, [json_parser, habit_parser])
        _add_parser(analyses, Analysis.max_streak, [json_parser, habit_filter_parser, period_filter_parser])
        _add_parser(analyses, Analysis.max_break, [json_parser, habit_filter_parser, period_filter_parser])
        _add_parser(analyses, Analysis.completion_rate, [timeframe_parser])

    return main_parser


def _parse_name(input):
    """ parses user input for valid string """
    
    if not input is None:
        if input == "" or input.isspace():
            raise argparse.ArgumentTypeError("invalid input")

        illegal_chars = "\"#$%&'*/;<=>\?@[\]^`{|}~"

        for c in input:
            if c in illegal_chars:
                raise argparse.ArgumentTypeError("invalid character: {0}".format(c))
        
    return input

def _parse_amount(input):
    """ parses user input for a positive amount """

    if not input is None:
        if not input.isdigit():
            raise argparse.ArgumentTypeError("invalid amount")
        if int(input) < 1:
            raise argparse.ArgumentTypeError("amount has to be positive")

    return input

def _parse_period(input):
    """ parses user input for valid period length """

    if not input is None:

        if input == "d" or input == "day": return 1
        if input == "w" or input == "week": return 7
        if input == "m" or input == "month": return 30

        if not input.isdigit():
            raise argparse.ArgumentTypeError("invalid period length")
        if int(input) < 1:
            raise argparse.ArgumentTypeError("period has to be positive")

    return input

def _parse_date(input):
    """ parses user input for valid date """   

    parsed_date = None
    try:
        parsed_date = date.fromisoformat(input)
    except:
        raise argparse.ArgumentTypeError("invalid date format")

    if not parsed_date is None:
        if parsed_date > date.today():
            raise argparse.ArgumentTypeError("date cannot be in the future")

        return parsed_date

    return input

#endregion
    

#region interactive session

def interactive_session(db : DB):
    """ interactive handling of user requests """

    print("Welcome to your habit progress tracker.")

    action = None
    while True:
        
        args = None

        if db.is_empty():
            # only allow samples to be inserted when empty
            actions = [Action.create, Action.insert_samples, Action.exit]
        else:
            # only allow rest of actions after creating at least one habit
            actions = [Action.create, Action.update, Action.progress, Action.reset, Action.delete, Action.list, Action.analyze, Action.exit]

        action = get_choice_from("What would you like to do{0}?".format("" if action is None else " next"), actions)
        if action == Action.create:
            name = get_input_for(Parameter.name, _parse_name)
            task = get_input_for(Parameter.task, _parse_name)
            period = get_input_for(Parameter.period, _parse_period, 1)
            goal = get_input_for(Parameter.goal, _parse_amount, 1)
            unit = get_input_for(Parameter.unit, _parse_name, "")

            args = argparse.Namespace(action=Action.create.name,name=name,task=task,period=period,goal=goal,unit=unit)
        elif action == Action.insert_samples:
            args = argparse.Namespace(action=Action.insert_samples.name)
        elif action == Action.update:
            habit_id = get_habit_selection(db, "Which habit do you want to update?")
            
            args = argparse.Namespace(action=Action.update.name, habit=habit_id)
            
            prop = get_choice_from("What would you like to update?", [Parameter.new_name, Parameter.new_task, Parameter.new_period, Parameter.goal, Parameter.unit])

            if prop == Parameter.new_name:
                args.name = get_input_for(Parameter.name, _parse_name)
            elif prop == Parameter.new_task:
                args.task = get_input_for(Parameter.task, _parse_name)
            elif prop == Parameter.new_period:
                args.period = get_input_for(Parameter.period, _parse_period)
            elif prop == Parameter.goal:
                args.goal = get_input_for(Parameter.goal, _parse_amount)
            elif prop == Parameter.unit:
                args.unit = get_input_for(Parameter.unit, _parse_name, "")

        elif action == Action.progress:
            habit_id = get_habit_selection(db, "Which habit do you want to progress or check off?")
            
            args = argparse.Namespace(action=Action.progress.name, habit=habit_id, amount=1, start=False, end=False, date=None)

            habit = db.get_habit(habit_id)

            if habit.unit == "minutes":                
                action = get_choice_from("What would you like to do?", [Parameter.progress_amount, Parameter.start_progress, Parameter.end_progress])

                if action == Parameter.progress_amount:
                    args.amount = get_input_for(Parameter.amount, _parse_amount)
                elif action == Parameter.start_progress:
                    args.start = True
                else:
                    args.end = True
            elif habit.goal > 1:
                args.amount = get_input_for(Parameter.amount, _parse_amount)

        elif action == Action.reset:
            habit_id = get_habit_selection(db, "Which habit do you want to reset?")
            
            if get_confirmation():
                args = argparse.Namespace(action=Action.reset.name, habit=habit_id)

        elif action == Action.delete:
            habit_id = get_habit_selection(db, "Which habit do you want to delete?")
            
            if get_confirmation():
                args = argparse.Namespace(action=Action.delete.name, habit=habit_id)

        elif action == Action.list:           
            args = argparse.Namespace(action=Action.list.name, period=None)

            choice = get_choice_from("Which habits do you want to see?",[Parameter.no_filter, Parameter.period_filter])

            if choice == Parameter.period_filter:
                args.period = get_input_for(Parameter.period, _parse_period)

        elif action == Action.analyze:            
            analysis = get_choice_from("Which analysis do you want to conduct?", [Analysis.current_progress, Analysis.current_streak
                                     , Analysis.past_progress, Analysis.past_streaks, Analysis.max_streak, Analysis.max_break, Analysis.completion_rate])

            args = argparse.Namespace(action=Action.analyze.name, analysis=analysis.name)

            if analysis == Analysis.current_progress or analysis == Analysis.current_streak or analysis == Analysis.past_streaks or analysis == Analysis.past_progress:
                args.habit = get_habit_selection(db, "Which habit do you want to analyze?")

            if analysis == Analysis.past_progress or analysis == Analysis.completion_rate:                
                timeframe = get_choice_from("Which period do you want to analyze"
                                          , [Parameter.no_filter, Parameter.current_week, Parameter.last_week, Parameter.current_month, Parameter.last_month])

                if timeframe == Parameter.current_week:
                    args.current_week = True
                    args.last_week = False
                elif timeframe == Parameter.last_week:
                    args.current_week = False
                    args.last_week = True
                elif timeframe == Parameter.current_month:
                    args.current_month = True
                    args.last_month = False
                elif timeframe == Parameter.last_month:
                    args.current_month = False
                    args.last_month = True

            elif analysis == Analysis.max_streak or analysis == Analysis.max_break:
                args.habit = None
                args.period = None                

                choice = get_choice_from("Which habits do you want to analyze?",[Parameter.no_filter, Parameter.period_filter, Parameter.habit_filter])

                if choice == Parameter.period_filter:
                    args.period = get_input_for(Parameter.period, _parse_period)
                elif choice == Parameter.habit_filter:
                    args.habit = get_habit_selection(db, "Please select the habit:")
        else:
            break

        if not args is None:
            print("")
            request.handle(db, args)

def get_choice_from(prompt : str, choices : []) -> Enum:
    """ presents a numbered list of choices and loops until a valid selection was made """
    print("\n" + prompt)

    for i,c in enumerate(choices):
        print("{0}) {1}".format(i+1,c.value))

    while True:
        i = input()
        if not i.isdigit() or int(i) < 1 or int(i) > len(choices):
            print("invalid selection, please try again: ", end="")
        else:
            return choices[int(i)-1]

def get_input_for(param : Enum, parse_func, default = None):
    """ prompts for a user input and loops until it conforms with parse function """
    print("\nPlease enter the {0}{1}: ".format(param.value, "" if default is None else " (optional)"), end="")

    while True:
        try:
            i = input()            
            i = parse_func(None if i == "" else i)
            if not i is None:
                return i
            if not default is None:
                return default

            print("invalid input, please try again: ", end="")
             
        except argparse.ArgumentTypeError as e:
            print(str(e) + ", please try again: ", end="")

def get_habit_selection(db : DB, prompt) -> int:
    """ prompts for habit selection and returns selected id """
    print("\n" + prompt)

    db_habits = db.get_habits()

    habits = []
    for i,h in enumerate(db_habits):
        habit = Habit.from_db(*h)
        habits.append(habit)
        print("{0}) {1}".format(i+1,habit))

    while True:
        i = input()
        if not i.isdigit() or int(i) < 1 or int(i) > len(habits):
            print("invalid selection, please try again: ", end="")
        else:
            return habits[int(i)-1]._id

def get_confirmation() -> bool:
    """ get a confirmation for critical actions """
    print("\nAre you sure?")
    i = input()

    if i.lower() == "yes" or i.lower() == "y":
        return True

    return False

#endregion


if __name__ == "__main__":

    db = DB("habits.db")
    db.assure_database()

    args = _create_parser(db.is_empty()).parse_args()

    if args.action is None:        
        interactive_session(db)
    else:
        # single request
        request.handle(db, args)