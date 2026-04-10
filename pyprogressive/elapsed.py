
import time

class Elapsed:

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.done = False
        self.current = 0   # number of items processed so far
        self.total = 0     # total number of items

    def start(self):
        self.start_time = time.perf_counter()

    def stop(self):
        self.end_time = time.perf_counter()

    def elapsed(self):
        if self.start_time is None or self.end_time is None:
            raise ValueError("Timer has not been started and stopped properly.")
        return self.end_time - self.start_time
    
    def __str__(self):
        if self.done:
            return f"(time: {self.elapsed()}, complete)"
        else:
            return f"(time: {self.elapsed()})"