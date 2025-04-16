from .token import SpecialToken
from .variable import Variable
from .expression import Node, Addition, Subtraction, Multiplication, Division, PowerN, InplaceAddition, InplaceSubtraction, InplaceMultiplication, InplaceDivision, BQ, GroupBy
from .token import DataItemToken, DataLengthToken, GToken
from .array import Array, global_arraylist
from .bq_converter import convert_with_bq
from .group_bq_converter import group_convert_with_bq
from .sympy_transform import flatten_with_sympy
from .evaluator import evaluate
from .groupby import group_by_bq_update, group_evaluator, detect_group_bq
import time

G = GToken()

def accum(expr):
    print("=== Before Flatten with bq converter ===")
    if hasattr(expr, 'print'):
        expr.print()
    bq_expr, _= convert_with_bq(expr, {})
    
    # print("=== After Flatten with bq converter ===")
    # bq_expr.print()
    return Multiplication(DataLengthToken(value = len(global_arraylist[0])), Variable(None, bq_expr)) 

def each(*args):
    if len(args) == 1:
        i = args[0]
        if isinstance(i, Array):
            return DataItemToken(i, i.id)
        else:
            raise ValueError("Only array is supported.")
        
    elif len(args) == 2:
        d, index = args
        if isinstance(d, Array):
            types_in_list = set(type(x) for x in d.data)
            if len(types_in_list) != 1:
                raise ValueError("Array must be homogeneous")
            if types_in_list == {tuple}:
                return DataItemToken(d, d.id, index)
            else:
                raise ValueError("Array must consist of tuples if there is an index")
        elif isinstance(d, GToken):
            if isinstance(index, int):
                return DataItemToken(d, "GToken", index)
            else:
                raise ValueError("Index must be int")
        else:
            raise ValueError("Only array is supported.")
    else:
        raise TypeError("Invalid number of arguments to 'each'")
    

def group(group_index_item, expr):
    if isinstance(group_index_item, DataItemToken):
        if group_index_item.index == -1:
            raise ValueError("Index is not specified")
        group_index = group_index_item.index
        group_arrayid = group_index_item.id
        return GroupBy(group_index, group_arrayid, expr)
    else:
        raise ValueError("group_index must be DataItemToken")


class Program:
    def __init__(self, *args):
        self.args = args
    def run(self, interval=1, callback=None):

        for array in global_arraylist:
            if len(array) != len(global_arraylist[0]):
                raise ValueError("Array's lengths must be same")
        variables = self.args
        for var in variables:
            if isinstance(var, GroupBy):
                var = flatten_with_sympy(var)
            else:
                # print("=== Before Flatten with Sympy ===")
                # var.print()
                var.expr = flatten_with_sympy(var)

        # print("=== After Flatten with Sympy ===")
        # for i, v in enumerate(variables, start=1):
        #     print(f"Variable {i}:")
        #     v.print()
       

        BQ_dict = {}
        BQ_group_dict = {}
                
        # compile
        # 1. convert to BQ & find BQ that need to calculate(update BQ_dict)
        for var in variables:
            print("=== Before BQ Conversion ===")
            var.print()
            if isinstance(var, GroupBy):
                var.expr, BQ_group_dict = group_convert_with_bq(var.expr, BQ_group_dict)
            else:  
                var, BQ_dict = convert_with_bq(var, BQ_dict)
        
        print("=== After BQ Conversion ===")
        for i, v in enumerate(variables, start=1):
            print(f"Variable {i}:")
            v.print()

        #groupby handling
        # for var in variables:
        #     if isinstance(var, GroupBy):
        #         var, BQ_dict = group_by_converter(var.expr, BQ_dict)


        #evaluate
        iter_accum_duration = 0
        support_normal_BQ_dict = {}
        for idx in range(0, len(global_arraylist[0])):
            # print("=== Iteration", idx, "===")
            iter_start = time.perf_counter()

            # for var in variables:
            #     if isinstance(var, GroupBy):
            #         group_index = var.group_index
            #         array_index = var.array_index
            #         var, BQ_group_dict = group_by_evaluator(var, BQ_group_dict, idx)
            for var in self.args:
                if isinstance(var, GroupBy):
                    BQ_group_dict = detect_group_bq(var, BQ_group_dict, idx)
                #print("BQ_group_dict: ", BQ_group_dict)

            for keys in BQ_group_dict.keys():
                if keys.split("_")[0] == "BQ" and keys.split("_")[2] == "of":
                    support_normal_BQ_dict[keys] = 0
            
            print("support_normal_BQ_dict: ", support_normal_BQ_dict)


            for keys in support_normal_BQ_dict.keys():
                if keys.split("_")[1] == "group":
                    pass
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
                        support_normal_BQ_dict[keys] = (support_normal_BQ_dict[keys] * (idx) + (arr1.data[idx] ** (int(pow1))) * (arr2.data[idx] ** (int(pow2)))) / (idx+1)
                    elif operator == "div":
                        support_normal_BQ_dict[keys] = (support_normal_BQ_dict[keys] * (idx) + (arr1.data[idx] ** (int(pow1))) / (arr2.data[idx] ** (int(pow2)))) / (idx+1)
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
                    if type(target_arr.data[idx]) == tuple:
                        support_normal_BQ_dict[keys] = (support_normal_BQ_dict[keys] * (idx) + target_arr.data[idx][1] ** (int(degree))) / (idx+1)
                    else:
                        support_normal_BQ_dict[keys] = (support_normal_BQ_dict[keys] * (idx) + target_arr.data[idx] ** (int(degree))) / (idx+1)



            for keys in BQ_dict.keys():
                if keys.split("_")[1] == "group":
                    pass
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
                    if type(target_arr.data[idx]) == tuple:
                        BQ_dict[keys] = (BQ_dict[keys] * (idx) + target_arr.data[idx][1] ** (int(degree))) / (idx+1)
                    else:
                        BQ_dict[keys] = (BQ_dict[keys] * (idx) + target_arr.data[idx] ** (int(degree))) / (idx+1)


            results = []

            for keys in support_normal_BQ_dict.keys():
                if keys not in BQ_dict.keys():
                    BQ_dict[keys] = support_normal_BQ_dict[keys]
        
            print("BQ_dict: ", BQ_dict)
            BQ_group_dict = group_by_bq_update(BQ_group_dict, idx)

            for var in self.args:
                if isinstance(var, GroupBy):
                    group_index = var.group_index
                    array_index = var.array_index
                    

                    var.val = group_evaluator(var, BQ_group_dict, index = idx, gindex = array_index, normal_BQ_dict= BQ_dict)
                    results.append(var.val)
                else:
                    result = evaluate(var, BQ_dict, length = len(global_arraylist[0]))
                    var.val = result
                    results.append(result)
            
            time.sleep(0.001)
   

            iter_end = time.perf_counter()


            iter_accum_duration += iter_end - iter_start
            if iter_accum_duration > interval:
                #args_val = [arg.val for arg in self.args]
                callback(*results)
                iter_accum_duration -= interval



def compile(*args):

    return Program(*args)