import progressive as pp
from progressive.midlevel import each, accum

if __name__ == "__main__":  
    array0 = pp.Array([2, 4, 6, 8, 10, 12, 14, 16, 18])
    array1 = pp.Array([100, -20, 10, 71, 900, 422, 161, 144, 434])
    array2 = pp.Array([1, 2, 3, 4, 5, 6, 7, 8, 9])


    mean1 = accum(each(array1)) / len(array1)
    mean2 = accum(each(array2)) / len(array2)
    cov = accum((each(array1) - mean1) * (each(array2) - mean2)) / len(array1)
    var = accum((each(array1) - mean1) ** 2) / len(array1)
    slope = cov / (var + 1e-6)
    intercept = mean2 - slope * mean1



    compiled = pp.progressify(slope, intercept)
    compiled.run(interval=1, callback = lambda slope, intercept: print(slope, intercept))

