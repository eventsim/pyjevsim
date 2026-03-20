"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains BankUser data class
"""


class BankUser:
    def __init__(self, _id: int, s_t: float):
        """
        Args:
            _id (int): User ID
            s_t (float): Service time
        """
        self.user_id = _id
        self.wait_t = 0.0
        self.done_t = 0.0
        self.arrival_t = 0.0
        self.service_t = s_t

    def get_id(self) -> int:
        return self.user_id

    def get_wait_time(self) -> float:
        return self.wait_t

    def get_arrival_time(self) -> float:
        return self.arrival_t

    def get_service_time(self) -> float:
        return self.service_t

    def set_arrival_time(self, a_t: float) -> None:
        self.arrival_t = a_t

    def calc_wait_time(self, w_t: float) -> None:
        self.done_t = w_t
        self.wait_t = w_t - self.arrival_t

    def __str__(self):
        return f"{self.get_id()}, {self.service_t}, {self.arrival_t}, {self.done_t}, {self.wait_t}"
