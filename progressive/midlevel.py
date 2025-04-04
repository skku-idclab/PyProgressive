from .token import SpecialToken
from .variable import Variable
from .expression import Node, Addition, Subtraction, Multiplication, Division, PowerN, InplaceAddition, InplaceSubtraction, InplaceMultiplication, InplaceDivision
from .token import DataItemToken
from .array import Array, global_arraylist
from .bq_converter import convert_with_bq
from .sympy_transform import flatten_with_sympy
from .evaluator import evaluate
import time

global_BQ_dict = {}
def accum(expr):
    bq_expr, _ = convert_with_bq(expr, global_BQ_dict)
    return Multiplication(len(global_arraylist[0]), Variable(None, bq_expr))

def each(i):
    if type(i) is Array:
        return DataItemToken(i, i.id)
    else:
        raise ValueError("Only array is supported.")

class Program:
    def __init__(self, *args):
        self.args = args
    def run(self, interval=1, callback=None):

        for array in global_arraylist:
            if len(array) != len(global_arraylist[0]):
                raise ValueError("Array's lengths must be same")
        variables = self.args
        for var in variables:
            # var.print()
            var.expr = flatten_with_sympy(var)

        # print("=== After Flatten with Sympy ===")
        # for i, v in enumerate(variables, start=1):
        #     print(f"Variable {i}:")
        #     #v.print()
       

        BQ_dict = {}
                
        # compile
        # 1. convert to BQ & find BQ that need to calculate(update BQ_dict)
        for var in variables:
            var, BQ_dict = convert_with_bq(var, BQ_dict)
        
        # print("=== After BQ Conversion ===")
        # for i, v in enumerate(variables, start=1):
        #     print(f"Variable {i}:")
        #     v.print()

        
        iter_accum_duration = 0
        for idx in range(0, len(global_arraylist[0])):
            iter_start = time.perf_counter()
            for keys in BQ_dict.keys():
                if keys.split("_")[1] == "special":
                    arr1id, pow1 = keys.split("_")[2], keys.split("_")[4]
                    arr2id, pow2 = keys.split("_")[6], keys.split("_")[8]
                    operator  = keys.split("_")[5]

                    for array in global_arraylist:
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
                    for array in global_arraylist:
                        if array.id == int(compute_arr):
                            target_arr = array
                    if(target_arr == None):
                        raise ValueError("Array not found")
                    BQ_dict[keys] = (BQ_dict[keys] * (idx) + target_arr.data[idx] ** (int(degree))) / (idx+1)


            eval_BQ_dict = {}
            for BQs in BQ_dict.keys():
                eval_BQ_dict[BQs] = BQ_dict[BQs] * len(global_arraylist[0])


            for var in self.args:
                result = evaluate(var, eval_BQ_dict, length = len(global_arraylist[0]))
                var.val = result
                
            time.sleep(0.0001)
   

            iter_end = time.perf_counter()

            iter_accum_duration += iter_end - iter_start
            
            if iter_accum_duration > interval:
                args_val = [arg.val for arg in self.args]
                callback(*args_val)
                iter_accum_duration -= interval



def progressify(*args):

    return Program(*args)