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
        


        # flatten each variable by using Sympy
        for var in self.variables:
            var.expr = flatten_with_sympy(var.expr)

        # print("=== After Flatten with Sympy ===")
        # for i, v in enumerate(self.variables, start=1):
        #     print(f"Variable {i}:")
        #     v.print()
       

        BQ_dict = {}
                
        # compile
        # 1) convert to BQ & find BQ that need to calculate(update BQ_dict)
        for var in self.variables:
            var.expr, BQ_dict = convert_with_bq(var.expr, len(self.array[0]), BQ_dict)
        
        # print("=== After BQ Conversion ===")
        # for i, v in enumerate(self.variables, start=1):
        #     print(f"Variable {i}:")
        #     v.print()

        # 2) find max BQ
        max_bq = 0
        for var in self.variables:
            if hasattr(var.expr, "bq_max"):
                max_bq = max(var.expr.bq_max, max_bq)

        
        iter_accum_duration = 0
        for idx in range(0, len(self.array[0].data)):
            iter_start = time.perf_counter()
            for keys in BQ_dict.keys():
                if keys.split("_")[1] == "special":
                    arr1id, pow1 = keys.split("_")[2], keys.split("_")[4]
                    arr2id, pow2 = keys.split("_")[6], keys.split("_")[8]
                    operator  = keys.split("_")[5]

                    for array in self.array:
                        if array.id == int(arr1id):
                            arr1 = array
                        if array.id == int(arr2id):
                            arr2 = array
                    if arr1 == None or arr2 == None:
                        raise ValueError("Array not found")

                    if operator == "mul":
                        BQ_dict[keys] = (BQ_dict[keys] * (idx) + (arr1.data[idx] ** (int(pow1))) * (arr2.data[idx] ** (int(pow2)))) / (idx+1)
                    elif operator == "div":
                        BQ_dict[keys] = (BQ_dict[keys] * (idx) + (arr1.data[idx] ** (int(pow1))) / (arr2.data[idx] ** (int(pow2)))) / (idx+1)
                    else:
                        raise ValueError("Operator not found")

                else:
                    degree, compute_arr = keys.split("_")[1], keys.split("_")[3]
                    target_arr = None
                    for array in self.array:
                        if array.id == int(compute_arr):
                            target_arr = array
                    if(target_arr == None):
                        raise ValueError("Array not found")
                    BQ_dict[keys] = (BQ_dict[keys] * (idx) + target_arr.data[idx] ** (int(degree))) / (idx+1)

            # print("BQ dict:", BQ_dict)

            for var in self.variables:
                result = evaluate(var, BQ_dict)
                var.val = result
                

            iter_end = time.perf_counter()

            iter_accum_duration += iter_end - iter_start
            
            if iter_accum_duration > self.interval:
                self.emit("tick")
                iter_accum_duration -= self.interval
            


        # run with time estimators

        # 1) compute BQs iteratively
        # BQ_list = [0] * (max_bq)
        # iter_accum_duration = 0
        # for idx in range(0, len(self.array[0].data)):
        #     iter_start = time.perf_counter()

        #     for i in range(0, max_bq):
        #         BQ_list[i] = (BQ_list[i] * (idx) + self.array[0].data[idx] ** (i+1)) / (idx+1)
        #     #print("BQ list:", BQ_list)

        #     # 2) evaluate each variable

        #     for var in self.variables:
        #         result = evaluate(var, BQ_list)
        #         var.val = result
        #         #print("result:", result)
        #         time.sleep(0.2)


        #     # 3) time estimation
        #     iter_end = time.perf_counter()

        #     iter_accum_duration += iter_end - iter_start
            
        #     if iter_accum_duration > self.interval:
        #         self.emit("tick")
        #         iter_accum_duration -= self.interval


        self.emit("end")
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
        # constantize all variables if they are not 
        for var in self.variables:
                if not isinstance(var.expr, Constantized) and isinstance(var.expr, Node) and getattr(var, "modified", False):
                    var.expr = Multiplication(var.expr, len(self.array[0].data))
            
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

