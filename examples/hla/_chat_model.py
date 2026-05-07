"""Shared chat federate model — used by both the Pitch and gorti examples.

This is a pure-DEVS BehaviorModel; it does not import anything from
pyjevsim.hla. The same class is wrapped by an HLAExecutor in both
example bring-ups, demonstrating that switching transports requires
zero changes to the model.

State machine:

    initial   ─► talking (period s) ──► talking (period s) ──► ...
                       │                       │
                       ▼ output()              ▼ output()
                  emits one chat message every period

External input port "inbox" prints whatever it receives. That's it.
"""

from __future__ import annotations

from pyjevsim import BehaviorModel, SysMessage


class Chatter(BehaviorModel):
    INBOX = "inbox"
    OUTBOX = "outbox"

    def __init__(self, name: str, period: float = 1.0,
                 message_count: int = 5) -> None:
        super().__init__(name)
        self.insert_state("talking", period)
        self.insert_state("done")
        self.init_state("talking")
        self.insert_input_port(self.INBOX)
        self.insert_output_port(self.OUTBOX)
        self._period = period
        self._remaining = message_count
        self._sent = 0

    def ext_trans(self, port, msg):
        if port != self.INBOX:
            return
        items = msg.retrieve() if msg is not None else []
        for item in items:
            text = item.get("text", "<no text>") if isinstance(item, dict) else str(item)
            sender = item.get("from", "?") if isinstance(item, dict) else "?"
            print(f"[{self.get_name()}] heard {sender!r}: {text}")

    def int_trans(self):
        if self._cur_state == "talking":
            self._sent += 1
            self._remaining -= 1
            if self._remaining <= 0:
                self._cur_state = "done"

    def output(self, deliver):
        if self._cur_state != "talking":
            return
        msg = SysMessage(self.get_name(), self.OUTBOX)
        msg.insert({
            "from": self.get_name(),
            "text": f"hello from {self.get_name()} #{self._sent + 1}",
        })
        deliver.insert_message(msg)
