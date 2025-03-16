import os
from config import *

import time
from functools import wraps

def timefn(fn):
    @wraps(fn)
    def measure_time(*args, **kwargs):
        t1 = time.perf_counter()
        result = fn(*args, **kwargs)
        t2 = time.perf_counter()
        print("@timefn: {} took {} seconds".format(fn.__name__, t2 - t1))
        return result
    return measure_time

@timefn
def execute_fn(executable):
	os.system(ex)

if not os.path.exists("output"):
    os.makedirs("output")

ex_list = []

for item in os.listdir("./scenario"):
    filename = item.split('.')[0]
    command = "python3 exp.py {0}  > ./output/{1}".format(filename, filename.split("_")[0])
    command += str(TIME_STDDEV)+"trash"+str(TRASH_STDDEV)+"_"+str(GARBAGECAN_SIZE)+"_"+str(RANDOM_SEED)+".log"
    ex_list.append(command)

total = len(ex_list)
for idx, ex in enumerate(ex_list):
    print(f"Processing {idx+1}/{total}:", ex)
    execute_fn(ex)
