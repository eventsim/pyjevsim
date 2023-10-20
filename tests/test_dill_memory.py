import dill
import datetime

class Test :
    def __init__(self):
        print("start")
        self.count = 0
        self.time = datetime.datetime.now()
        
    def test(self) :
        print("count : ", self.count)
        self.count += 1
        print("")
        #if self.count == 20 :
        #    with open("test.simx", "wb") as f :
        #        dill.dump(x, f)
        
        
x = Test()

#with open("test.simx", "rb") as f :
#    x = dill.load(f)

data = dill.dump_module("test.simx", datetime, refimported=True)

dill.load_module('test.simx')
with open("test.simx", "rb") as f:
    f.read()
    print(f)
x.test()
