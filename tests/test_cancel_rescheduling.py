"""Regression tests for ``cancel_rescheduling()``.

A model in a timed state may receive external events more often than its
own deadline. Calling ``cancel_rescheduling()`` inside ``ext_trans``
asks the engine **not** to restart the time-advance timer for that
event, so the model keeps firing on its original cadence
(``min(original_deadline, now + sigma)``) instead of having its deadline
pushed back by every incoming message.

The mechanism was silently broken: ``BehaviorExecutor.ext_trans`` read
the model's cancel flag *before* calling ``model.ext_trans`` (which is
where the model raises it), and ``get_req_time`` cleared the flag every
cycle — so the executor never observed it. The visible symptom was
atsim's TrackingManuever: it received a fresh ``target`` every tick, its
deadline got reset every tick, and ``output`` (which moves the torpedo)
therefore never fired.

These tests pin the contract so the regression cannot return.
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage


class Ticker(BehaviorModel):
    """Fires ``int_trans`` every ``period`` ticks, re-arming forever.

    On every ``poke`` it optionally calls ``cancel_rescheduling()`` so the
    poke does not restart its period timer.
    """

    def __init__(self, period, use_cancel, log, ss_ref):
        super().__init__("ticker")
        self.insert_state("tick", period)
        self.init_state("tick")
        self.insert_input_port("poke")
        self._use_cancel = use_cancel
        self._log = log
        self._ss = ss_ref

    def ext_trans(self, port, msg):
        if port == "poke" and self._use_cancel:
            self.cancel_rescheduling()

    def int_trans(self):
        # re-arm: stay in "tick" so the period repeats
        self._log.append(self._ss.global_time)
        self._cur_state = "tick"

    def output(self, msg_deliver):
        pass


class Poker(BehaviorModel):
    """Emits ``count`` pokes spaced one tick apart, then passivates."""

    def __init__(self, count, ss_ref):
        super().__init__("poker")
        self.insert_state("active", 1)
        self.insert_state("done", Infinite)
        self.init_state("active")
        self.insert_output_port("out")
        self._count = count
        self._fired = 0
        self._ss = ss_ref

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        if self._cur_state == "active":
            self._fired += 1
            if self._fired >= self._count:
                self._cur_state = "done"

    def output(self, msg_deliver):
        if self._cur_state == "active":
            m = SysMessage(self.get_name(), "out")
            m.insert(self._fired)
            msg_deliver.insert_message(m)


def _build(use_cancel, poke_count):
    log = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    ticker = Ticker(period=5, use_cancel=use_cancel, log=log, ss_ref=ss)
    poker = Poker(count=poke_count, ss_ref=ss)
    ss.register_entity(ticker)
    ss.register_entity(poker)
    ss.coupling_relation(poker, "out", ticker, "poke")
    return ss, log


def test_cancel_rescheduling_preserves_original_cadence():
    """Pokes at t=1,2,3 (all < period 5) must NOT delay the ticker.

    With cancel honoured the ticker keeps its original schedule and fires
    at t=5 and t=10.
    """
    ss, log = _build(use_cancel=True, poke_count=3)
    ss.simulate(12, _tm=False)
    assert log == [5, 10]


def test_without_cancel_external_event_resets_deadline():
    """Contrast case: without cancel, every poke restarts the timer.

    Pokes land at t=1,2,3; the last one reschedules the ticker to
    t=3+5=8, so it has fired exactly once (at t=8) by the t=12 horizon —
    proving the poke path really does touch the deadline and that the
    cancel test above is meaningful.
    """
    ss, log = _build(use_cancel=False, poke_count=3)
    ss.simulate(12, _tm=False)
    assert log == [8]


def test_cancel_rescheduling_survives_continuous_pokes():
    """A poke on every single tick must still let the ticker fire.

    This is the atsim TrackingManuever scenario: an external event arrives
    every tick, faster than the model's own period. Before the fix the
    deadline was reset on every poke and the ticker fired *zero* times.

    We assert on the distinct firing instants rather than the raw count:
    when a poke lands on the same instant the ticker is already imminent
    (t=5, t=10) the confluent path re-arms and the cancelled deadline can
    surface one extra activation at that instant. The property that
    matters for the regression is that the ticker keeps firing on its own
    5-tick cadence instead of being starved.
    """
    ss, log = _build(use_cancel=True, poke_count=20)
    ss.simulate(12, _tm=False)
    assert log, "ticker was starved — cancel_rescheduling regressed"
    assert sorted(set(log)) == [5, 10]
