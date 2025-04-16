import progressive as pp
from progressive.midlevel import each, accum, group, G

if __name__ == "__main__":  
    array0 = pp.Array([('A', 2), ('B', 1), ('B', 4), ('C', 3), ('A', -3), ('A', 10), ('A', 8), ('B', 7), ('A', 10), ('A', 0)])
    #array0 = pp.Array([(2, 'A'), (100, 'B'), (4, 'A'), (3, 'B'), (6000, 'A'), (5, 'B'), (8, 'A'), (7, 'B'), (10, 'A'), (0, 'A')])
    array1 = pp.Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    wholesum = accum(each(array0, 1))
    var = group(each(array0, 0), accum(each(G, 1))/wholesum)
    var2 = group(each(array0, 0), accum(1))

    compiled = pp.compile(var, var2)
    compiled.run(interval = 0, callback = lambda var, var2: print(var, var2))

#TODO: array index handling in datalength
#TODO: each index handling for category and data
    


