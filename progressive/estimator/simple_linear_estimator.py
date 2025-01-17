import time

def linear_regression(history):
    x_values = [x for x, y in history]
    y_values = [y for x, y in history]
    
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in history)
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    m = numerator / denominator

    c = y_mean - m * x_mean

    return m, c

class SimpleLinearEstimator:
    def __init__(self, init_iter_count = 1, min_iter_count = 1):
        self.init_iter_count = init_iter_count
        self.min_iter_count = min_iter_count
        
        self.history = [] # (iter, time) tuples
        self.iter = None
        
    def estimate_next(self, tick):
        """ returns the number of iterations to run in ``tick`` seconds"""
        iter = self.init_iter_count

        if len(self.history) > 2:
            history = self.history[-10:]
            m, c = linear_regression(history)

            iter = (tick - c) / m

        iter = max(self.min_iter_count, int(iter))
        self.iter = iter    
            
        return iter
        
    def start(self):
        self.start_time = time.time()

    def end(self):
        self.history.append((self.iter, time.time() - self.start_time))
        self.iter = None

            
    
        

        

        

    


    


