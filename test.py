import progressive as pp

if __name__ == "__main__":
    # do we actually need to create a session?

    
    array0 = pp.Array([10, 20, 3, 21, 5, 42, 11, 14, 34, 13])
    array1 = pp.Array([100, -20, 10, 71, 900, 422, 161, 144, 434, 173])
    array2 = pp.Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])


    accum, each = pp.create_session([array0, array1, array2])
    xmean = accum(each(0)/each(1))
    ymean = accum(each(1)) / len(each(1))
    diff = xmean - ymean


    compiled = pp.progressify(xmean, ymean, diff, array_list = [array0, array1, array2])
    compiled.run(interval=1, callback = lambda xmean, ymean, diff: print(xmean.val, ymean.val, diff.val))

    


