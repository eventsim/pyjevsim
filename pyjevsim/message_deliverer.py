from .definition import *
from .system_message import SysMessage

class MessageDeliverer:
    def __init__(self):
        self.data_list = []

    def insert_message(self, msg):
        """
        Inserts a message into the data list.
       
        Args:
            msg: Message object to be inserted.
        """
        self.data_list.append(msg) #SysMessage type

        #self.data_list.sort(key=lambda m: m.get_scheduled_time())

    def has_contents(self):
        """
        Checks if the data list contains any messages.

        Returns:
            bool: True if the list is not empty, otherwise False.
        """
        return not self.data_list

    def get_contents(self):
        """
        Retrieves the list of messages.

        Returns:
            list: The list of Message objects.
        """
        return self.data_list

    def get_first_event_time(self):
        """
        Retrieves the scheduled time of the first message in the list.

        Returns:
            float: Scheduled time of the first message or Infinity if the list is empty.
        """
        return float("inf") if not self.data_list else self.data_list[0].get_scheduled_time()