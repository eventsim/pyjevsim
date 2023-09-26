from .system_object import  SysObject


class SysMessage(SysObject):
    def __init__(self, src_name="", dst_name=""):
        super(SysMessage, self).__init__()
        self._src = src_name
        self._dst = dst_name
        self._msg_time = -1
        self._msg_list = []

    def __str__(self):
        return super(SysMessage, self).__str__() + \
                f"\tSRC:{self._src}\t DST:{self._dst}"

    def insert(self, msg):
        self._msg_list.append(msg)

    def extend(self, _list):
        self._msg_list.extend(_list)

    def retrieve(self):
        return self._msg_list

    def get_src(self):
        return self._src

    def get_dst(self):
        return self._dst

    def set_msg_time(self, t):
        self._msg_time = t

    def get_msg_time(self):
        return self._msg_time