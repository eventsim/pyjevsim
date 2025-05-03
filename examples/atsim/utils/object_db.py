import threading

class ObjectDB:
    _instance = None
    _lock = threading.Lock()

    _obj_list = []

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:  # double-checked locking
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'items'):
            self.items = [] 

