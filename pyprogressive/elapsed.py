class Elapsed:
    """
    A class to measure elapsed time.
    """

    def __init__(self):
        """
        Initialize the Elapsed class.
        """
        self.start_time = None
        self.end_time = None
        self.done = False

    def start(self):
        """
        Start the timer.
        """
        import time
        self.start_time = time.perf_counter()

    def stop(self):
        """
        Stop the timer.
        """
        import time
        self.end_time = time.perf_counter()

    def elapsed(self):
        """
        Get the elapsed time in seconds.
        """
        if self.start_time is None or self.end_time is None:
            raise ValueError("Timer has not been started and stopped properly.")
        return self.end_time - self.start_time
    
    def __str__(self):
        if self.done:
            return f"(time: {self.elapsed()}, complete)"
        else:
            return f"(time: {self.elapsed()})"