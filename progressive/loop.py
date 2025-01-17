# from .estimator.simple_linear_estimator import SimpleLinearEstimator
# from .tick import Tick

from .token import SpecialToken
from .variable import Variable

class Loop:
    def __init__(self, session, array, interval=1):
        self.session = session
        self.array = array
        self.interval = interval

        self.interperter_loop_in = False
        self.variables = []
        self.handlers = []
        self.symbol = SpecialToken.LOOP_INDEX        
    
    def __enter__(self):    
        return self
        
    def add_variable(self, value):
        v = Variable(self, value)
        self.variables.append(v)
        return v
    
    def __exit__(self, *args):
        # compile
        # run
        
        print(args)
        pass
    
    def __iter__(self):        
        if self.interperter_loop_in:                
            raise "Nested loops are not supported!"
        return self

    def __next__(self):
        if not self.interperter_loop_in:
            self.interperter_loop_in = True
            
            return self.symbol 
        
                   
        self.interperter_loop_in = False        
        raise StopIteration  # Stop iteration after yielding once

    # def __iter__(self):
    #     self.emit("start")

    #     self.iter = None
    #     self.array.init_iter()
    #     self.estimator = SimpleLinearEstimator()

    #     return self
    
    # def __next__(self):
    #     if self.iter:
    #         self.array.update_iter(self.iter)
    #         self.estimator.end()
            
    #         self.emit("tick")

    #         self.iter = None

    #     if self.array.iter_done():
    #         self.emit("end")
    #         raise StopIteration
        
    #     iter_from = self.array.iter
    #     iter_to = self.array.iter + self.estimator.estimate_next(self.tick)
    #     iter_to = min(iter_to, self.array.length)

    #     self.iter = iter_to
    #     self.estimator.start()

    #     return Tick(self.array, iter_from, iter_to)

    def on(self, event):        
        def decorator(handler):                        
            self.handlers.append((event, handler))
            return handler
        
        return decorator
    
    def emit(self, event, *args):
        for event_name, handler in self.handlers:
            if event_name == event:
                handler(*args)
