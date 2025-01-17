from functools import wraps

class Session:
    def __init__(self):
        self.handlers = []

    def on(self, event):        
        def decorator(handler):                        
            self.handlers.append((event, handler))
            return handler
        
        return decorator


    