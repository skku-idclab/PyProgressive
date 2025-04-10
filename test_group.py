import progressive as pp
from progressive.midlevel import each, accum, group

if __name__ == "__main__":  
    #array0 = pp.Array([('A', 2), ('B', 100), ('A', 4), ('B', 3), ('A', 6000), ('B', 5), ('A', 8), ('B', 7), ('A', 10), ('A', 0)])
    array0 = pp.Array([('A', 2), ('B', 1), ('B', 4), ('B', 3), ('A', -3), ('A', 10), ('A', 8), ('B', 7), ('A', 10), ('A', 0)])
    array1 = pp.Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    wholesum = accum(each(array0, 1))
    var = group(each(array0, 0), accum(each(array0, 1)))

    compiled = pp.compile(wholesum)
    compiled.run(interval = 0, callback = lambda var: print(var))

#TODO: array index handling in datalength
#TODO: each index handling for category and data
    


