from datetime import date

class Period:
    """ struct to hold progress in a given period """

    def __init__(self, start_date : date, end_date : date, progress : int = 0):
        """ instanciate a period
        Args:
            start_date: start of period
            end_date: end of period
            progress: amount of progress made in this period            
        """

        self.start_date = start_date
        self.end_date = end_date
        self.progress = progress