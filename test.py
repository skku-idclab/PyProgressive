import progressive as pp

if __name__ == "__main__":  
    array0 = pp.Array([2, 4, 6, 8, 10, 12, 14, 16, 18, 20])
    array1 = pp.Array([100, -20, 10, 71, 900, 422, 161, 144, 434, 173])
    array2 = pp.Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])


    accum, each = pp.create_session([array0, array1, array2])
    xmean = accum(each(0)) / len(array0)
    xvar = accum((xmean - each(0))**2) / len(array0)
    ymean = accum(each(1)) / len(array1)
    yvar = accum((ymean - each(1))**2) / len(array1)

    xycov = accum((each(0) - xmean) * (each(1) - ymean)) / len(array0)


    compiled = pp.progressify(xvar, yvar, xycov, array_list = [array0, array1, array2])
    compiled.run(interval=1, callback = lambda xvar, yvar, xycov: print(xvar.val, yvar.val, xycov.val))

