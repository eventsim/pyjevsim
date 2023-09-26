import datetime

class SysObject(object):
    # Object ID which tracks the entire instantiated Objects
    __GLOBAL_OBJECT_ID = 0

    def __init__(self):
        self.__created_time = datetime.datetime.now()
        self.__object_id = SysObject.__GLOBAL_OBJECT_ID
        SysObject.__GLOBAL_OBJECT_ID = SysObject.__GLOBAL_OBJECT_ID + 1

    def __str__(self):
        return "ID:%10d %s" % (self.__object_id, self.__created_time)

    def set_req_time(self, global_time):
        pass

    def get_req_time(self):
        pass

    def __lt__(self, other):
        return self.__object_id < other.__object_id

    # added by cbchoi 2020-01-21
    def get_obj_id(self):
        return self.__object_id