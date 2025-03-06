import progressive as pp

if __name__ == "__main__":  
    array0 = pp.Array([2, 4, 6, 8, 10, 12, 14, 16, 18, 20])
    array1 = pp.Array([100, -20, 10, 71, 900, 422, 161, 144, 434, 173])
    array2 = pp.Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])


    accum, each = pp.create_session([array0, array1, array2])
    xmean = accum(each(0)/each(2)) / len(array0)
    xvar = accum((xmean - each(0))**2) / len(array0)


    compiled = pp.progressify(xmean, xvar, array_list = [array0, array1, array2])
    compiled.run(interval=1, callback = lambda xmean, xvar: print(xmean.val, xvar.val))

