from .loop import Loop


class Session:
    def __init__(self):
        self.variables = []
        self.handlers = []

    def add(self, *variables):
        self.variables.extend(variables)
        
    def on(self, event):        
        def decorator(handler):                        
            self.handlers.append((event, handler))
            return handler
        
        return decorator


    
    def loop(self, array, interval = 1):
        return Loop(self, array, interval)
    
        
        