import progressive as pp
from progressive.midlevel import each, accum, group

if __name__ == "__main__":  
    array0 = pp.Array([('A', 2), ('B', 100), ('A', 4), ('B', 3), ('A', 6000), ('B', 5), ('A', 8), ('B', 7), ('A', 10)])
    var = group(each(array0, 0), accum(each(array0, 1)*2)/accum(1))

    compiled = pp.compile(var)
    compiled.run(interval = 0, callback = lambda var: print(var))

#TODO: array index handling in datalength
#TODO: each index handling for catehgory and data
    


