import pyprogressive as pp
from pyprogressive.midlevel import each, accum

if __name__ == "__main__":  
    # array0 = pp.Array([2, 4, 6, 8, 10, 12, 14, 16, 18])
    # array1 = pp.Array([100, -20, 10, 71, 900, 422, 161, 144, 434])
    # array2 = pp.Array([1, 2, 3, 4, 5, 6, 7, 8, 9])

    # # mean1 = accum(each(array1)) / len(array1)
    # # mean2 = accum(each(array2)) / len(array2)
    # # cov = accum((4*each(array1) - mean1) * (each(array2) - mean2)) / len(array1)
    # # var = accum((each(array1) - mean1) ** 2) / len(array1)
    # # slope = cov / (var + 1e-6)
    # # intercept = mean2 - slope * mean1

    def my_callback(slope, intercept):
        print(f"Slope: {slope}, Intercept: {intercept}")


    # # compiled = pp.compile(slope, intercept)
    # # compiled.run(interval=0.0001, callback = my_callback)

    # a = accum(each(array1)*each(array2))/len(array1)
    # b = accum((each(array1)-a)**3/ len(array1))

    # compiled = pp.compile(a, b)
    # compiled.run(interval=0, callback = lambda a, b: print(f"a: {a}, b: {b}"))

    D = pp.Array([100, -20, 10, 71, 90, -42, 61, 44, 34, -8])

    mean = accum(each(D)) / len(D)
    var = accum((mean - each(D))**2) / len(D)
    compiled = pp.compile(var)
    compiled.run(interval = 0, callback = print)

