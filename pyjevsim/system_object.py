"""
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""

import datetime


class SystemObject:
    # Object ID which tracks the entire instantiated Objects
    __GLOBAL_OBJECT_ID = 0

    def __init__(self):
        self.__created_time = datetime.datetime.now()
        self.__object_id = SystemObject.__GLOBAL_OBJECT_ID
        SystemObject.__GLOBAL_OBJECT_ID = SystemObject.__GLOBAL_OBJECT_ID + 1

    def __str__(self):
        return f"ID:{self.__object_id} {self.__created_time}"

    def __lt__(self, other):
        return self.__object_id < other.__object_id

    # added by cbchoi 2020-01-21
    def get_obj_id(self):
        return self.__object_id
