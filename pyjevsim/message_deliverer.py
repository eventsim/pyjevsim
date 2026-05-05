from .definition import *
from .system_message import SysMessage

class MessageDeliverer:
    """Bag of `SysMessage` objects produced by a model's `output()`.

    Output messages are propagated **by reference** to every subscriber on
    a coupled port. This matches the prevailing Python-DEVS convention
    (xdevs.py, PythonPDEVS, and the reference engine in
    `benchmark/engines/reference/` all behave the same way). If your model
    needs to mutate a received payload, copy it on the receiver side
    (e.g. `payload = list(received)`); do not rely on the simulator to
    deep-copy outputs.
    """

    def __init__(self):
        self.data_list = []

    def insert_message(self, msg):
        """Insert a `SysMessage` into the bag.

        Args:
            msg (SysMessage): the message to deliver. Pass exactly one
                `SysMessage` per call. The bag is propagated by reference
                to every subscriber on the source port (see class
                docstring).
        """
        self.data_list.append(msg)

        #self.data_list.sort(key=lambda m: m.get_scheduled_time())

    def has_contents(self):
        """
        Checks if the data list contains any messages.

        Returns:
            bool: True if the list is not empty, otherwise False.
        """
        return len(self.data_list) > 0

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