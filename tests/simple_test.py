import pyprogressive as pp
from pyprogressive.midlevel import each, accum, group, G

if __name__ == "__main__":  
    array0 = pp.array([1, 2, 3, 4, 5, 6])
    wholesum = accum(each(array0))


    compiled = pp.compile(wholesum)
    compiled.run(interval = 0, callback = lambda wholesum: print(wholesum))