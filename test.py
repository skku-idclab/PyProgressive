import PyProgressive

@PyProgressive.fy
def my_function(x):
    accum = 0
    for idx in range(len(x)):
        accum += x[idx]
    
    return accum

if __name__ == "__main__":
    test_list = [10, 20, 30, 21, 5, 42, 11, 14, 34, 13] # 분산: 127.2
    print(my_function(test_list))
