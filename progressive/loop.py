from .estimators.simple_linear_estimator import SimpleLinearEstimator
from .tick import Tick

class Loop:
    def __init__(self, array, tick=1):
        self.array = array
        self.tick = tick

        self.handlers = []
        

    def __iter__(self):
        self.emit("start")

        self.iter = None
        self.array.init_iter()
        self.estimator = SimpleLinearEstimator()

        return self
    
    def __next__(self):
        if self.iter:
            self.array.update_iter(self.iter)
            self.estimator.end()
            
            self.emit("tick")

            self.iter = None

        if self.array.iter_done():
            self.emit("end")
            raise StopIteration
        
        iter_from = self.array.iter
        iter_to = self.array.iter + self.estimator.estimate_next(self.tick)
        iter_to = min(iter_to, self.array.length)

        self.iter = iter_to
        self.estimator.start()

        return Tick(self.array, iter_from, iter_to)

    def on(self, event):        
        def decorator(handler):                        
            self.handlers.append((event, handler))
            return handler
        
        return decorator
    
    def emit(self, event, *args):
        for event_name, handler in self.handlers:
            if event_name == event:
                handler(*args)
