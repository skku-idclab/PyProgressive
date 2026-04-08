from .token import SpecialToken
from .variable import Variable
from .expression import Node, Addition, Subtraction, Multiplication, Division, PowerN, InplaceAddition, InplaceSubtraction, InplaceMultiplication, InplaceDivision, BQ, GroupBy, BinaryOperationNode, InplaceOperationNode
from .token import DataItemToken, DataLengthToken, GToken, global_G_arridx
from .array import array, global_arraylist
from .bq_converter import convert_with_bq
from .group_bq_converter import group_convert_with_bq
from .sympy_transform import flatten_with_sympy
from .evaluator import evaluate
from .groupby import group_by_bq_update, group_evaluator, detect_group_bq
import time
from .elapsed import Elapsed
import inspect

G = GToken()
elapsed = Elapsed()


def find_array_id_in_expr(node):

    if node is None:
        return None

   
    if isinstance(node, DataItemToken):
        return node.id
    
    if isinstance(node, BQ):
        return node.arridx



    if isinstance(node, Variable):
        return find_array_id_in_expr(node.expr)

    if isinstance(node, GroupBy):
        expr_id = find_array_id_in_expr(node.expr)
        if expr_id is not None:
            return expr_id

        return None

    if isinstance(node, PowerN):
        base_id = find_array_id_in_expr(node.base)
        if base_id is not None:
            return base_id

        exp_id = find_array_id_in_expr(node.exponent)
        if exp_id is not None:
            return exp_id
        return None


    if isinstance(node, (BinaryOperationNode, InplaceOperationNode)):
        left_id = find_array_id_in_expr(node.left)
        if left_id is not None:
            return left_id
        right_id = find_array_id_in_expr(node.right)
        if right_id is not None:
            return right_id
        return None


    if not hasattr(node, 'left') and not hasattr(node, 'right') and \
       not hasattr(node, 'base') and not hasattr(node, 'exponent') and \
       not hasattr(node, 'expr'):
        return None

    return None

def accum(expr):

    bq_expr, _= convert_with_bq(expr, {})

    related_array_id = find_array_id_in_expr(bq_expr)


    if related_array_id == "GToken":
        return Multiplication(DataLengthToken(arrayid = "GToken", ingroup = True), Variable(None, bq_expr))


    if related_array_id is None:
        if not global_arraylist:
            raise ValueError("global_arraylist is empty")
        related_array_id = "constant"
        return Multiplication(DataLengthToken(arrayid = "constant"), Variable(None, bq_expr))

    
    length_val = len(global_arraylist[int(related_array_id)].data)
    found_array = global_arraylist[int(related_array_id)]
    

    return Multiplication(DataLengthToken(value = length_val, arrayid = related_array_id, array = found_array), Variable(None, bq_expr)) 



def each(*args):
    if len(args) == 1:
        i = args[0]
        if isinstance(i, array):
            return DataItemToken(i, i.id)
        else:
            raise ValueError("Only array is supported.")
        
    elif len(args) == 2:
        d, index = args
        if isinstance(d, array):
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
        if group_index_item.index == -1: # counting case
            using_arr = group_index_item.array
            if type(using_arr.data[0]) is tuple:
                raise ValueError("Index is not specified")

        group_index = group_index_item.index
        group_arrayid = group_index_item.id
        return GroupBy(group_index, group_arrayid, expr)
    else:
        raise ValueError("group_index must be DataItemToken")


class Program:
    def __init__(self, *args):
        self.args = args
    def _update_bqs_with_chunk(self, BQ_dict, idx, chunk_count):
        for keys in BQ_dict.keys():
            if keys.split("_")[1] == "group":
                pass
            if keys.split("_")[1] == "special":
                arr1id, pow1 = keys.split("_")[2], keys.split("_")[4]
                arr2id, pow2 = keys.split("_")[6], keys.split("_")[8]
                operator  = keys.split("_")[5]

        pass



    def run(self, interval=1, callback=None, tau = 0.99, chunk_count = 1):
        

        for array in global_arraylist:
            if len(array) != len(global_arraylist[0]):
                raise ValueError("Array's lengths must be same")
        variables = self.args
        for var in variables:
            if isinstance(var, GroupBy):
                var = flatten_with_sympy(var)
            else:
                var.expr = flatten_with_sympy(var)


       

        BQ_dict = {}
        BQ_group_dict = {}
                
        # compile
        # 1. convert to BQ & find BQ that need to calculate(update BQ_dict)
        for var in variables:

            if isinstance(var, GroupBy):
                var.expr, BQ_group_dict = group_convert_with_bq(var.expr, BQ_group_dict)
            else:  
                var, BQ_dict = convert_with_bq(var, BQ_dict)
        


        #evaluate
        elapsed.start()
        iter_accum_duration = 0
        support_normal_BQ_dict = {}
        for idx in range(0, len(global_arraylist[0])):
            # print("=== Iteration", idx, "===")
            iter_start = time.perf_counter()

            for var in self.args:
                if isinstance(var, GroupBy):
                    BQ_group_dict = detect_group_bq(var, BQ_group_dict, idx)
                #print("BQ_group_dict: ", BQ_group_dict)

            for keys in BQ_group_dict.keys():
                if keys.split("_")[0] == "BQ" and keys.split("_")[2] == "of":
                    support_normal_BQ_dict[keys] = 0
            
            #print("support_normal_BQ_dict: ", support_normal_BQ_dict)
            for keys in support_normal_BQ_dict.keys():
                if keys not in BQ_dict.keys():
                    BQ_dict[keys] = support_normal_BQ_dict[keys]
        


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

            
            #print("BQ_dict: ", BQ_dict)
            BQ_group_dict = group_by_bq_update(BQ_group_dict, idx)

            for var in self.args:
                if isinstance(var, GroupBy):
                    group_index = var.group_index
                    array_index = var.array_index
                    global_G_arridx = array_index
                
                    var.val = group_evaluator(var, BQ_group_dict, index = idx, gindex = array_index, normal_BQ_dict= BQ_dict)
                    results.append(var.val)
                else:
                    try:
                        result = evaluate(var, BQ_dict, length = len(global_arraylist[0]))
                    except Exception:
                        result = float('nan')
                    var.val = result
                    results.append(result)
            
            
            #time.sleep(0.001)
   

            iter_end = time.perf_counter()

            callback_start = time.perf_counter()


            iter_accum_duration += iter_end - iter_start
            if iter_accum_duration > interval * tau:
                elapsed.stop()
                elapsed.done = False
                if not inspect.isbuiltin(callback):
                    sig = inspect.signature(callback)
                    num_params = len(sig.parameters)
                    num_results = len(results)
                    if num_params == num_results:
                        callback(*results)
                        iter_accum_duration -= interval
                    elif num_params == num_results + 1:
                        callback(*results, elapsed)
                        iter_accum_duration -= interval
                    else:
                        raise ValueError(f"Callback function must have {num_results} or {num_results + 1}(when including elpased) parameters, but got {num_params}.")
                else:
                    callback(*results)
                    iter_accum_duration -= interval
                callback_start = time.perf_counter()
                iter_accum_duration += callback_start - iter_end



        elapsed.stop()
        elapsed.done = True

        if not inspect.isbuiltin(callback):
                sig = inspect.signature(callback)
                num_params = len(sig.parameters)
                num_results = len(results)
                if num_params == num_results:
                    callback(*results)
                elif num_params == num_results + 1:
                    callback(*results, elapsed)
                else:
                    raise ValueError(f"Callback function must have {num_results} or {num_results + 1}(when including elpased) parameters, but got {num_params}.")
        else:
            callback(*results)
            
        



def compile(*args):

    return Program(*args)