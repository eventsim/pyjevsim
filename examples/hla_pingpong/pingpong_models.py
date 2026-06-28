"""Ping-pong federate models + HLA bindings (RTI-agnostic).

Two paddles rally a ball:

  * ``Ping`` serves at t=0, then returns every ``Pong`` it receives, until
    ``max_volleys`` is reached.
  * ``Pong`` returns every ``Ping`` it receives.

Three FOM endpoints exercise the two HLA data paths:

  * ``PingPong.Ping`` / ``PingPong.Pong`` — **interactions** (the rally).
  * ``PingPaddle.hits`` — an **object attribute** Ping publishes and Pong
    reflects (object synchronization).

The models import nothing RTI-specific beyond the binding dataclasses; the
exact same classes run on ``inprocess``, ``loopback`` or ``pitch``.
"""

from __future__ import annotations

from pyjevsim import BehaviorModel, SysMessage
from pyjevsim.hla import HLAAttribute, HLAInteraction

PING_FOM = "PingPong.Ping"
PONG_FOM = "PingPong.Pong"
HITS_FOM = "PingPaddle.hits"


class Ping(BehaviorModel):
    """Server paddle: serves once, then returns each pong up to max_volleys."""

    def __init__(self, name: str = "ping", max_volleys: int = 3,
                 period: float = 1.0):
        super().__init__(name)
        self.insert_state("serve", 0)        # serve immediately at t=0
        self.insert_state("rally", period)   # return `period` after a pong
        self.insert_state("idle")            # Infinite — passive
        self.init_state("serve")
        self.insert_input_port("in_pong")
        self.insert_output_port("out_ping")
        self.insert_output_port("out_hits")
        self.max_volleys = max_volleys
        self.count = 0                       # current ball number
        self.received_pongs: list = []

    def ext_trans(self, port, msg):
        if port == "in_pong":
            # Inbound contract: retrieve()[0] is the peer's full
            # retrieve() list; our payload is its single dict.
            data = msg.retrieve()[0][0]
            self.received_pongs.append(data)
            self.count = int(data["count"]) + 1
            self._cur_state = "rally" if self.count <= self.max_volleys else "idle"

    def int_trans(self):
        if self._cur_state in ("serve", "rally"):
            self._cur_state = "idle"

    def output(self, deliver):
        if self._cur_state in ("serve", "rally"):
            ball = SysMessage(self.get_name(), "out_ping")
            ball.insert({"count": self.count, "sender": self.get_name()})
            deliver.insert_message(ball)
            # Object attribute: publish how many balls this paddle has hit.
            hits = SysMessage(self.get_name(), "out_hits")
            hits.insert({"hits": self.count})
            deliver.insert_message(hits)


class Pong(BehaviorModel):
    """Responder paddle: returns every ping; reflects Ping's hits attribute."""

    def __init__(self, name: str = "pong", period: float = 1.0):
        super().__init__(name)
        self.insert_state("wait")            # Infinite — passive
        self.insert_state("return", period)
        self.init_state("wait")
        self.insert_input_port("in_ping")
        self.insert_input_port("in_hits")
        self.insert_output_port("out_pong")
        self.count = 0
        self.received_pings: list = []
        self.reflected_hits: list = []       # object-sync observations

    def ext_trans(self, port, msg):
        if port == "in_ping":
            data = msg.retrieve()[0][0]
            self.received_pings.append(data)
            self.count = int(data["count"])
            self._cur_state = "return"
        elif port == "in_hits":
            data = msg.retrieve()[0][0]
            self.reflected_hits.append(int(data["hits"]))

    def int_trans(self):
        if self._cur_state == "return":
            self._cur_state = "wait"

    def output(self, deliver):
        if self._cur_state == "return":
            ball = SysMessage(self.get_name(), "out_pong")
            ball.insert({"count": self.count, "sender": self.get_name()})
            deliver.insert_message(ball)


def ping_bindings() -> dict:
    return {
        "out_ping": HLAInteraction(PING_FOM, direction="out"),
        "in_pong": HLAInteraction(PONG_FOM, direction="in"),
        "out_hits": HLAAttribute(HITS_FOM, direction="out",
                                 object_class="PingPaddle"),
    }


def pong_bindings() -> dict:
    return {
        "in_ping": HLAInteraction(PING_FOM, direction="in"),
        "out_pong": HLAInteraction(PONG_FOM, direction="out"),
        "in_hits": HLAAttribute(HITS_FOM, direction="in"),
    }


# FOM map for the Pitch backend (handle resolution + field encoding).
PINGPONG_FOM_MAP = {
    PING_FOM: {"kind": "interaction", "class": "HLAinteractionRoot.Ping",
               "fields": {"count": "int32", "sender": "string"}},
    PONG_FOM: {"kind": "interaction", "class": "HLAinteractionRoot.Pong",
               "fields": {"count": "int32", "sender": "string"}},
    HITS_FOM: {"kind": "attribute", "class": "HLAobjectRoot.PingPaddle",
               "fields": {"hits": "int32"}},
}
