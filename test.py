import progressive as pp

if __name__ == "__main__":
    # do we actually need to create a session?

    ps = pp.Session()
    array0 = pp.Array([10, 20, 3, 21, 5, 42, 11, 14, 34, 13])
    array1 = pp.Array([100, -20, 10, 71, 900, 422, 161, 144, 434, 173])
    array2 = pp.Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])


    with ps.loop([array0, array1, array2], interval=1) as loop:
        xmean = loop.add_variable(0)
        xstd = loop.add_variable(0)
        ymean = loop.add_variable(0)
        ystd = loop.add_variable(0)
        cov = loop.add_variable(0)
        cor = loop.add_variable(0)
        a = loop.add_variable(0)


        @loop.on("tick")
        def tick_handler():
            print(xstd.value(), ystd.value(), cov.value(), abs(cor.value())**0.5)

        @loop.on("end")
        def end_handler():
            print("Computation end")
            print(xstd.value(), ystd.value(), cov.value())

        for i in loop:
            xmean += array0[i]
        xmean /= len(array0)

        for i in loop:
            xstd += (array0[i] - xmean) ** 2
        xstd /= len(array0)-1

        for i in loop:
            ymean += array1[i]
        ymean /= len(array0)

        for i in loop:
            ystd += (array1[i] - ymean) ** 2
        ystd /= len(array0)-1

        for i in loop:
            cov += (array0[i] - xmean) * (array1[i] - ymean)
        cov /= len(array0)-1

        for i in loop:
            cor += 0

    
        cor += cov**2
        cor /= xstd +1e-9
        cor /= ystd +1e-9




        


    # loop = pp.Loop(data, tick=1)
    # @loop.on("start")
    # def loop_start_handler():
    #     print("loop start")

    # @loop.on("tick")
    # # called every tick (e.g., 1s) not every iteration
    # def loop_tick_handler():
    #     print("loop tick")

    # # @loop.on("iter")
    # # # called every iteration
    # # def loop_tick_handler():
    # #     print("loop iteration")

    # @loop.on("end")
    # def loop_end_handler():
    #     print("loop end")



