# from .estimator.simple_linear_estimator import SimpleLinearEstimator
# from .tick import Tick

from .token import SpecialToken
from .variable import Variable
from .expression import Constantized, Node, Addition, Subtraction, Multiplication, Division, PowerN, InplaceAddition, InplaceSubtraction, InplaceMultiplication, InplaceDivision
from .bq_converter import convert_with_bq
from .sympy_transform import flatten_with_sympy
from .evaluator import evaluate
import time

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
        v._tracked = True
        self.variables.append(v)
        return v

    def __exit__(self, *args):
        # run after the entire block 
        
        #self.variables[0].print()
        #self.variables[1].print()
        # TODO: topological sort
        # TODO: check for cycles
        # TODO: flatten additions and subtractions        
        # TODO: flatten multiplications
        # TODO: check if each expr can be projected by BQs



        # flatten each variable by using Sympy
        for var in self.variables:
            var.expr = flatten_with_sympy(var.expr)

        # print("=== After Flatten with Sympy ===")
        # for i, v in enumerate(self.variables, start=1):
        #     print(f"Variable {i}:")
        #     v.expr.print()
       
                
        # compile
        # 1) convert to BQ
        for var in self.variables:
            var.expr = convert_with_bq(var.expr, len(self.array))
        
        print("=== After BQ Conversion ===")
        for i, v in enumerate(self.variables, start=1):
            print(f"Variable {i}:")
            v.print()


        # 2) find max BQ
        max_bq = 0



        for var in self.variables:
            if hasattr(var.expr, "bq_max"):
                max_bq = max(var.expr.bq_max, max_bq)
        


        # run with time estimators

        # TODO: 1) compute BQs iteratively (complete)
        BQ_list = [0] * (max_bq)
        es_BQ = [0] * (max_bq)
        iter_accum_duration = 0
        for idx in range(0, len(self.array.data)):
            iter_start = time.perf_counter()

            for i in range(0, max_bq):
                BQ_list[i] = (BQ_list[i] * (idx) + self.array.data[idx] ** (i+1)) / (idx+1)
            #print("BQ list:", BQ_list)

            # 2) evaluate each variable

            for var in self.variables:
                result = evaluate(var, BQ_list)
                var.val = result
                #print("result:", result)
                time.sleep(0.1)


            iter_end = time.perf_counter()

            iter_accum_duration += iter_end - iter_start
            
            if iter_accum_duration > self.interval:
                self.emit("tick")
                iter_accum_duration -= self.interval
            





            
            # TODO: 3) time estimation
            
                
  
        #print(args)
        pass
    
    def __iter__(self):        
        if self.cursor_in_loop: 
            raise "Nested loops are not supported!"
        return self 

    def __next__(self):
        if not self.cursor_in_loop:
            self.cursor_in_loop = True
            for var in self.variables:
                if not isinstance(var.expr, Constantized) and isinstance(var.expr, Node) and getattr(var, "modified", False):
                    #print("Constantizing", var)
                    var.expr = Constantized(var.expr)
            
            
            return self.symbol         

        # run after each loop
        # constantize all variables if they are not -> 등록된 모든 노드를 constantize 하면 안되고,
        # 해당 루프에서 사용된 노드만 constantize 해야 함.
        for var in self.variables:
                if not isinstance(var.expr, Constantized) and isinstance(var.expr, Node) and getattr(var, "modified", False):
                    var.expr = Multiplication(var.expr, len(self.array.data))
            
            
        
        self.cursor_in_loop = False        

        
        raise StopIteration  # Stop iteration after yielding once


    def on(self, event):        
        def decorator(handler):                        
            self.handlers.append((event, handler))
            return handler
        
        return decorator
    
    def emit(self, event, *args):
        for event_name, handler in self.handlers:
            if event_name == event:
                handler(*args)
    

    def _get_children(self, node):
        """
        Returns a list of child nodes for the given node (Variable, Addition, etc.).

        Args:
            node (Node): The node for which to find children.

        Returns:
            list[Node]: A list of child nodes.
        """
        if isinstance(node, (Addition, Subtraction, Multiplication, Division, InplaceAddition, InplaceSubtraction, InplaceMultiplication, InplaceDivision)):
            return [node.left, node.right]
        elif isinstance(node, PowerN):
            return [node.base, node.exponent]
        elif isinstance(node, Variable):
            # Variable also inherits from Node, but keeps its main expression in 'self.expr'.
            if hasattr(node, "expr"):
                return [node.expr]
            else:
                return []
        else:
            # For constants, tokens, or other terminal objects, no children.
            return []

