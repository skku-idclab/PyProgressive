import pyprogressive as pp
from pyprogressive.midlevel import each, accum, group, G

# A: 2 -3 10 8 10 0
# B: 1 4 7 -5
# C: 2 3
array0 = pp.array([('A', 2), ('C', 2), ('B', 1), ('B', 4), ('C', 3), ('A', -3),
                   ('A', 10), ('A', 8), ('B', 7), ('A', 10), ('B', -5), ('A', 0)])


mean = accum(each(array0, 1))/accum(1)
variance = accum((each(array0, 1) - mean)**2) / accum(1)
# #group_count = accum(each(G,1)*0 + 1)
# group_mean = group(each(array0, 0), each(G, 1)/group_count)
# group_var = group(each(array0, 0),(each(G, 1) - group_mean)**2)
group_var = group(each(array0, 0),(each(G, 1) - mean)**2)

compiled = pp.compile(mean, variance, group_var)
compiled.run(interval = 0, callback = lambda mean, variance, group_var: print(mean, variance, group_var))

#   File "C:\Python\Python3_8\lib\site-packages\pyprogressive\evaluator.py", line 53, in evaluate
#     return evaluate(node.base, bq_values, length) ** evaluate(node.exponent, bq_values, length)
# TypeError: unsupported operand type(s) for ** or pow(): 'NoneType' and 'int'

#   File "C:\Python\Python3_8\lib\site-packages\pyprogressive\sympy_transform.py", line 88, in node_to_string
#     raise TypeError(f"Unsupported node type in node_to_string: {type(node)}")
# TypeError: Unsupported node type in node_to_string: <class 'str'>