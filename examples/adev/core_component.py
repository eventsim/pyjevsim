from abc import *
#import numpy as np
import copy
import random
from datetime import datetime

class Statistic(object):
    def __init__(self, seed, mean, stddev):
        self.mean = mean
        self.stddev = stddev
        self.rseed = datetime.now().timestamp()
        self.random = random.Random(self.rseed)
        #self.random.seed(datetime.now())

    def get_mean(self):
        return self.mean
        
    def get_stddev(self):
        return self.stddev
    
    def get_seed(self):
        return self.rseed
        
    def get_delta(self):
        #val=np.random.normal(self.mean,self.stddev)
        # calculate delta
        val = self.random.normalvariate(self.mean, self.stddev)
        return val
        
class TimeStruct(object):
    def __init__(self, hour, minute, stat):
        self.hour = hour
        self.minute = minute
        self.stat = stat

    def get_unit_time(self):
        delta = self.stat.get_delta()
        return self.hour + float(self.minute)/60 + delta

class TimeStructDeterministic(TimeStruct):
    def __init__(self, hour, minute):
        super(TimeStructDeterministic, self).__init__(hour, minute, None)

    def get_unit_time(self):
        return self.hour + float(self.minute)/60
        
class TimeStructContstraintToDay(TimeStruct):
    #ID = 0
    def __init__(self, hour, minute, stat):
        super(TimeStructContstraintToDay, self).__init__(hour, minute, stat)
        self.prev_time = 0
        #TimeStructContstraintToDay.ID += 1
        #print(TimeStructContstraintToDay.ID)

    def get_unit_time(self):
        delta = self.stat.get_delta()
        prev_time = self.prev_time
        cur_time = self.hour + float(self.minute)/60 + delta
        self.prev_time = 24 - cur_time

        #print("prev_time:", prev_time, ", self.prev_time", id(self.prev_time), ", out_time:", prev_time+cur_time, )
        return prev_time + cur_time

class TimeStructContstraintToDayDeterministic(TimeStruct):
    #ID = 0
    def __init__(self, hour, minute):
        super(TimeStructContstraintToDayDeterministic, self).__init__(hour, minute, None)
        self.prev_time = 0

    def get_unit_time(self):
        prev_time = self.prev_time
        cur_time = self.hour + float(self.minute)/60 
        self.prev_time = 24 - cur_time
        return prev_time + cur_time

class TimeStructConstraintRandom(TimeStruct):
    def __init__(self, start_hour, end_hour, stat):
        super(TimeStructConstraintRandom, self).__init__(0, 0, stat)
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.prev_time = 0
        self.initial = False

    def get_unit_time(self):
        # inital: start_hour + random delta; prev_hour = start_hour + random delta
        # next : prev_hour + random delta < end_hour;  prev_hour = prev_hour + random_delta
        #      : prev_hour + random delta > end_hour then (24 - end_hour) + start_hour + random delta; prev_hour = start_hour + random delta

        if self.initial == False:
            self.prev_time = self.start_hour.get_unit_time() + self.stat.get_delta()
            self.initial=True
            return self.prev_time
        else:
            calc_time = self.prev_time + self.stat.get_delta()
            if calc_time < self.end_hour.get_unit_time():
                self.prev_time = calc_time
                return self.prev_time
            else:
                self.prev_time = calc_time
                return 24 - self.end_hour.get_unit_time() + self.prev_time


class HumanType(object):
    def __init__(self, _id):
        self.h_id = _id
        self.satisfaction = 100
        pass
    
    def get_name(self):
        return '{0}_{1}'.format(self.get_type(), self.h_id)
        
    def get_id(self):
        return self.h_id
        
    @abstractmethod
    def get_type(self):
        pass

    @abstractmethod
    def get_wakeup(self):
        pass
    
    @abstractmethod
    def get_sleep(self):
        pass

    @abstractmethod
    def get_out(self):
        pass

    @abstractmethod
    def get_in(self):
        pass
        
    @abstractmethod
    def get_trash(self):
        pass
        
    @abstractmethod
    def get_satisfaction_func(self, trash):
        pass
    @abstractmethod
    def is_vacation(self):
        pass

    def get_satisfaction(self):
        return self.satisfaction 

    def set_satisfaction(self,satis):
        self.satisfaction=satis
        

import random

class FamilyType(object):
    def __init__(self, garbage_size):
        self.family_member = {}
        self.garbage_storage_size = garbage_size
        self.current_storage_size = 0
        
    def register_member(self, htype):
        self.family_member[htype] = 0

    def get_members(self):
        return self.family_member
    
    def stack_garbage(self, amount):
        self.current_storage_size += amount
    
    def should_empty(self):
        if self.garbage_storage_size > self.current_storage_size:
            return False
        else:
            return True

    def is_flush(self, member):
        if member == self.select_member():
            return True
        else:
            return False
    
    def select_member(self):
        # random
        # 지정
        # ... 
        lst = list(self.family_member.keys())
        #random.shuffle(lst)
        return lst[0]
    
    def get_stack_amount(self):
        return self.current_storage_size
        
    def empty_stack(self):
        self.current_storage_size = 0
        for k in self.family_member.keys():
            self.family_member[k] = 0