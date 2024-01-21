from datetime import datetime

class Progress:
    """ struct to hold datetime and amount of progress """

    def __init__(self, habit, amount : int = 1, progress_date : datetime = None):
        """ instanciate a progress
        Args:  
            habit: habit id (int) or name (str) 
            amount: amount of progress made
            progress_date: datetime            
        """

        self.habit = habit
        self.amount = amount
        self.progress_date = progress_date or datetime.now()
             