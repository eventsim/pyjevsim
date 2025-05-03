import random

from .core_component import Statistic
from .core_component import HumanType
from .core_component import TimeStruct
from .core_component import TimeStructContstraintToDay
from .core_component import TimeStructConstraintRandom
from .core_component import TimeStructDeterministic
from .core_component import TimeStructContstraintToDayDeterministic


from config import *
class Housewife(HumanType):
    def __init__(self,_id):
        HumanType.__init__(self ,_id)
        self.out_time = TimeStructContstraintToDay(13,00, Statistic(0, AVG_TIME, TIME_STDDEV))
        #self.out_time = TimeStructContstraintToDayDeterministic(13,00)
        self.trash = Statistic(RANDOM_SEED,0.9,TRASH_STDDEV)
        pass
    
    def get_type(self):
        return "Housewife"
        
    def get_wakeup(self):
        return TimeStruct(6, 17, Statistic(RANDOM_SEED, 0, TIME_STDDEV))
    
    def get_sleep(self):
        return TimeStruct(23, 21, Statistic(RANDOM_SEED, 0, 1))
        
    def get_out(self):
        return self.out_time 
        #return TimeStructConstraintRandom(self.get_wakeup(), self.get_sleep(), Statistic(0, 10, 6))
        
    def get_in(self):
        return TimeStruct(15, 0, Statistic(RANDOM_SEED, 0, 1))
        """
                            def get_trash(self):
                                ev_t=SystemSimulator().get_engine("sname").get_global_time()
                                ev_t= ev_t-int(ev_t /8762)*8762
                                if ev_t>=8280:
                                    if ev_t <=8760:
                                        return 2.4
                                else:
                                    return 1.2
        """
    def get_trash(self):
        return self.trash.get_delta()
        
    def get_satisfaction_func(self, trash):
        if trash >= 0.8 :
            return -10
        elif trash <= 0:
            return 20
        elif trash < 0.8:
            return 10
        """
        if trash >0:
            return -10
        else:
            return 10
        """
    def is_vacation(self):
        return False

class Student(HumanType):
    def __init__(self,_id):
        HumanType.__init__(self ,_id)
        self.out_time = TimeStructContstraintToDay(7,58, Statistic(0, AVG_TIME, TIME_STDDEV))
        #self.out_time = TimeStructContstraintToDayDeterministic(9,58)
        self.trash = Statistic(RANDOM_SEED+1,0.9,TRASH_STDDEV)
        pass
    
    def get_type(self):
        return "Student"

    def get_wakeup(self):
        return TimeStruct(7,58, Statistic(RANDOM_SEED, 0, 1))
        
    def get_sleep(self):
        return TimeStruct(24,51, Statistic(RANDOM_SEED, 0, 1))
  
    def get_out(self):
        return self.out_time

    def get_in(self):
        return TimeStruct(21,00, Statistic(RANDOM_SEED, 0, 1))

    def get_trash(self):
        return self.trash.get_delta()

    def get_satisfaction_func(self, trash):
        if trash >= 0.8 :
            return -10
        elif trash <= 0:
            return 20
        elif trash < 0.8:
            return 10

    def is_vacation(self):
        return False

class StudentWithVacation(HumanType):
    def __init__(self,_id):
        HumanType.__init__(self ,_id)
        self.approach = False
        self.count=0
        self.vacation=True
        self.set_satisfaction(None)
        pass
    
    def get_type(self):
        return "Student"

    def get_wakeup(self):
        return TimeStruct(7,58, Statistic(RANDOM_SEED, 0, 1))
        
    def get_sleep(self):
        return TimeStruct(24,51, Statistic(RANDOM_SEED, 0, 1))
  
    def get_out(self):
        if self.approach == False:
            self.approach=True
            self.vacation=False
            return TimeStruct(1464,0,Statistic(RANDOM_SEED, 0, 1)) # 방학대기 

        else:
            self.count+=1
            self.vacation=False
            if self.count >= 122:
                self.vacation=True
                self.approach = False
                self.count=0    
                return TimeStructContstraintToDay(7,58, Statistic(RANDOM_SEED, AVG_TIME, TIME_STDDEV))
            else:
                
                return TimeStructContstraintToDay(7,58, Statistic(RANDOM_SEED, AVG_TIME, TIME_STDDEV))


    def get_in(self):
        return TimeStruct(21,00, Statistic(RANDOM_SEED, 0, 1))

    def get_trash(self):
        if self.vacation:
            return 0
        else:
            if self.count>115:
                return 1.8
            else:
                return 0.9

    def get_satisfaction_func(self, trash):
        if self.vacation:
            return None
        if trash >= 0.8 :
            return -10
        elif trash <= 0:
            return 20
        elif trash < 0.8:
            return 10
    
    def is_vacation(self):
        if self.vacation:
            return True
        else:
            return False

class Blue_collar(HumanType):
    def __init__(self,_id):
        HumanType.__init__(self ,_id)
        self.out_time = TimeStructContstraintToDay(6,22, Statistic(0, AVG_TIME, TIME_STDDEV))
        #self.out_time = TimeStructContstraintToDayDeterministic(6,22)
        self.trash = Statistic(RANDOM_SEED+2,0.9,TRASH_STDDEV)
        pass
    
    def get_type(self):
        return "Blue_collar"

    def get_wakeup(self):
        return TimeStruct(6,22, Statistic(RANDOM_SEED, 0, 1))
        
    def get_sleep(self):
        return TimeStruct(23,35, Statistic(RANDOM_SEED, 0, 1))
  
    def get_out(self):
        return self.out_time

    def get_in(self):
        return TimeStruct(17,30, Statistic(RANDOM_SEED, 0, 1))

    def get_trash(self):
        return self.trash.get_delta()

    def get_satisfaction_func(self, trash):
        """if trash >0:
                                    return -10
                                else:
                                    return 10"""
        
        if trash >= 0.8:
            return -10
        elif trash <= 0:
            return 20
        elif trash < 0.8:
            return 10
        
    def is_vacation(self):
        return False

class Self_employment(HumanType):
    def __init__(self,_id):
        HumanType.__init__(self ,_id)
        pass
    
    def get_type(self):
        return "Self_employment"

    def get_wakeup(self):
        return TimeStruct(6,43, Statistic(RANDOM_SEED, 0, 1))
        
    def get_sleep(self):
        return TimeStruct(23,54, Statistic(RANDOM_SEED, 0, 1))
  
    def get_out(self):
        return TimeStructContstraintToDay(RANDOM_SEED,43, Statistic(0, AVG_TIME, TIME_STDDEV))

    def get_in(self):
        return TimeStruct(20,00, Statistic(RANDOM_SEED, 0, 1))

    def get_trash(self):
        return 1          

    def get_satisfaction_func(self, trash):
        if trash >= 0.5:
            return -10
        elif trash < 0.5:
            return 10
        elif trash == 0:
            return 30

    def is_vacation(self):
        return False
class White_collar(HumanType):
    def __init__(self,_id):
        HumanType.__init__(self ,_id)
        pass
    
    def get_type(self):
        return "White_collar"

    def get_wakeup(self):
        return TimeStruct(6,36, Statistic(RANDOM_SEED, 0, 1))
        
    def get_sleep(self):
        return TimeStruct(23,53, Statistic(RANDOM_SEED, 0, 1))
  
    def get_out(self):
        return TimeStruct(6,36, Statistic(RANDOM_SEED, AVG_TIME, TIME_STDDEV))

    def get_in(self):
        return TimeStruct(17,30, Statistic(RANDOM_SEED, 0, 1))

    def get_trash(self):
        return 1          

    def get_satisfaction_func(self, trash):
        if trash >= 0.5:
            return -10
        elif trash < 0.5:
            return 10
        elif trash == 0:
            return 50

    def is_vacation(self):
        return False
    
class Inoccupation(HumanType):
    def __init__(self,_id):
        HumanType.__init__(self ,_id)
        pass
    
    def get_type(self):
        return "Inoccupation"

    def get_wakeup(self):
        return TimeStruct(6,26, Statistic(RANDOM_SEED, 0, 1))
        
    def get_sleep(self):
        return TimeStruct(23,16, Statistic(RANDOM_SEED, 0, 1))
  
    def get_out(self):
        return TimeStruct(6,26, Statistic(RANDOM_SEED, AVG_TIME, TIME_STDDEV))

    def get_in(self):
        return TimeStruct(17,00, Statistic(RANDOM_SEED, 0, 1))

    def get_trash(self):
        return 1          

    def get_satisfaction_func(self, trash):
        if trash >= 0.5:
            return -10
        elif trash < 0.5:
            return 10
        elif trash == 0:
            return 50

    def is_vacation(self):
        return False

class AFF(HumanType):
    def __init__(self, _id):
        HumanType.__init__(self, _id)
        self.out_time= TimeStructContstraintToDay(6, 30, Statistic(RANDOM_SEED, AVG_TIME, STDDEV)) #
        pass
        
    def get_type(self):
        return "AFF"

    def get_wakeup(self):
         return TimeStruct(5, 22, Statistic(RANDOM_SEED, 0, 1))
    
    def get_sleep(self):
        return TimeStruct(22, 14, Statistic(RANDOM_SEED, 0, 1))

    def get_out(self):
        return self.out_time

    def get_in(self):
        return TimeStruct(17, 0, Statistic(RANDOM_SEED, 0, 1))
    
    def get_trash(self):
        return 1
        
    def get_satisfaction_func(self, trash):
        if trash >= 0.7:
            return -10
        elif trash < 0.7:
            return 10
        elif trash <= 0:
            return 50
    def is_vacation(self):
        return False
