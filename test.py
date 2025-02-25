import progressive as pp

if __name__ == "__main__":
    # do we actually need to create a session?

    ps = pp.Session()
    array = pp.Array([10, 20, 0, 21, 5, 42, 11, 14, 34, 13])
    array2 = pp.Array([100, -20, 10, 71, 900, 422, 161, 144, 434, 173])
    array3 = pp.Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])


    with ps.loop([array, array2, array3], interval=1) as loop:
        psum = loop.add_variable(0)
        pssum = loop.add_variable(0)
        psssum = loop.add_variable(0)

        

        @loop.on("tick")
        def tick_handler():
            print(psum.value(), pssum.value(), psssum.value())

        @loop.on("end")
        def end_handler():
            print("Computation end")
            print(psum.value(), pssum.value())

        for i in loop:
            # for j in loop:
            psum += array2[i]
            # psum += i + 1
            # array[i+1]
            # psum += iff(array[i] > 5, 10, 0)
            # if array[i] > 5:
            #     if array[i] < 10:
            #         psum += 1
        
        # arr = env.AddArray(array)
        # i = env.itertaor()
        # program = InLoop(array, MultipleStatements(Accumulate(psum, arr), Accumulate(psum, 1)))

        psum /= len(array)


        for i in loop:
            # print("pssum")
            # (array[i] - loop.variables[0]).print()
            pssum += array3[i]

        pssum /= len(array)

        psssum+=(psum-pssum)





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



