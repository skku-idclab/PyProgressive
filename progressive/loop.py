# from .estimator.simple_linear_estimator import SimpleLinearEstimator
# from .tick import Tick

from .token import SpecialToken
from .variable import Variable

class Loop:
    def __init__(self, session, array, interval=1):
        self.session = session
        self.array = array
        self.interval = interval

        self.cursor_in_loop = False
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
        self.variables[0].print()
        # TODO: topological sort
        # TODO: check for cycles
        # TODO: flatten additions and subtractions        
        # TODO: flatten multiplications
        # TODO: check if each expr can be projected by BQs
        
                
        # compile
        
        
        # run with time estimators
        
        print(args)
        pass
    
    def __iter__(self):        
        if self.cursor_in_loop: 
            raise "Nested loops are not supported!"
        return self

    def __next__(self):
        if not self.cursor_in_loop:
            self.cursor_in_loop = True
            
            return self.symbol         
                   
        self.cursor_in_loop = False        
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
