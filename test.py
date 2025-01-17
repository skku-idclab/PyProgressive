import PyProgressive

@PyProgressive.fy
def my_function(x):
    accum = 0
    for idx in range(len(x)):
        accum += x[idx]
    
    return accum

# if __name__ == "__main__":
#     test_list = [10, 20, 0, 21, 5, 42, 11, 14, 34, 13] # 분산: 127.2
#     print(my_function(test_list))

import progressive as pp

if __name__ == "__main__":
    # do we actually need to create a session?
    # ps = pp.Session()

    # @ps.on("start")
    # def start_handler():
    #     print("session start")

    data = pp.Array([10, 20, 0, 21, 5, 42, 11, 14, 34, 13])
    loop = pp.Loop(data, tick=1)

    psum = pp.Variable(0)
    pssum = pp.Variable(0)

    @loop.on("start")
    def loop_start_handler():
        print("loop start")
    
    @loop.on("tick") 
    # called every tick (e.g., 1s) not every iteration
    def loop_tick_handler():
        print("loop tick")

    # @loop.on("iter")
    # # called every iteration 
    # def loop_tick_handler():
    #     print("loop iteration")
        
    @loop.on("end")
    def loop_end_handler():
        print("loop end")    

    for tick in loop:
        print(tick)

        for i in tick.range():
            psum += data[i]

        psum /= len(data)

        for i in tick.range():
            pssum += (data[i] - psum) ** 2

        pssum /= len(data)

        print(psum, pssum)





        




