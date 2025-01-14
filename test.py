import PyProgress

@PyProgress.transform_decorator
def my_function(x):
    accum = 0
    tem = 0
    
    for idx in range(len(x)):
        accum += x[idx]
        print(accum)

    average = accum / len(x)

    for idx in range(len(x)):
        tem += (x[idx] - average) **2
        print("esvar:", tem/len(x))
    print("var:", tem / len(x))
    var = tem/len(x)
    return var




if __name__ == "__main__":
    test_list = [10, 20, 30, 21, 5, 42, 11, 14, 34, 13] # 분산: 127.2
    print(my_function(test_list))