"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT. The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Unit tests for TerminationCondition classes.
"""

import pytest
from pyjevsim.termination_condition import (
    TerminationCondition,
    TimeBasedTermination,
    AttributeBasedTermination,
    CompositeTermination
)
from pyjevsim.system_executor import SysExecutor
from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType


class SimpleCounter(BehaviorModel):
    """Simple model for testing attribute-based termination."""

    def __init__(self, name):
        super().__init__(name)
        self.counter = 0
        self.init_state("COUNT")
        self.insert_state("COUNT", 1)

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        self.counter += 1

    def output(self, msg_deliver):
        return msg_deliver


def test_time_based_termination_basic():
    """Test TimeBasedTermination with simple time limit."""
    termination = TimeBasedTermination(100)

    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)

    # Should not terminate at start
    assert termination.should_terminate(se) is False

    # Simulate to time 50
    se.simulate(50)
    assert termination.should_terminate(se) is False

    # Simulate to time 100
    se.simulate(50)
    assert termination.should_terminate(se) is True


def test_time_based_termination_invalid():
    """Test TimeBasedTermination with invalid input."""
    with pytest.raises(ValueError):
        TimeBasedTermination(-10)


def test_attribute_based_termination_basic():
    """Test AttributeBasedTermination with counter model."""
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)

    counter_model = SimpleCounter("counter")
    se.register_entity(counter_model)

    # Terminate when counter reaches 5
    termination = AttributeBasedTermination(
        model_name="counter",
        attribute_path="counter",
        condition_fn=lambda count: count >= 5
    )

    # Should not terminate at start
    se.init_sim()
    assert termination.should_terminate(se) is False

    # Run simulation - counter increments during int_trans in schedule()
    # After 5 schedules, counter should be >= 5
    for i in range(6):  # Run 6 times to ensure counter reaches 5
        se.schedule()

    # Now counter should be >= 5
    model = se.get_model("counter")
    assert model.counter >= 5
    assert termination.should_terminate(se) is True


def test_attribute_based_termination_nested():
    """Test AttributeBasedTermination with nested attribute."""

    class NestedModel(BehaviorModel):
        def __init__(self, name):
            super().__init__(name)
            self.state_obj = type('obj', (object,), {'value': 0})()
            self.init_state("IDLE")
            self.insert_state("IDLE", 1)

        def ext_trans(self, port, msg):
            pass

        def int_trans(self):
            self.state_obj.value += 1

        def output(self, msg_deliver):
            return msg_deliver

    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)
    model = NestedModel("nested")
    se.register_entity(model)

    termination = AttributeBasedTermination(
        model_name="nested",
        attribute_path="state_obj.value",
        condition_fn=lambda v: v >= 3
    )

    se.init_sim()
    assert termination.should_terminate(se) is False

    for i in range(4):  # Run 4 times to ensure value reaches 3
        se.schedule()

    retrieved_model = se.get_model("nested")
    assert retrieved_model.state_obj.value >= 3
    assert termination.should_terminate(se) is True


def test_attribute_based_termination_model_not_found():
    """Test AttributeBasedTermination when model doesn't exist."""
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)

    termination = AttributeBasedTermination(
        model_name="nonexistent",
        attribute_path="counter",
        condition_fn=lambda x: x >= 10
    )

    # Should return False (not terminate) if model not found
    assert termination.should_terminate(se) is False


def test_attribute_based_termination_invalid():
    """Test AttributeBasedTermination with invalid inputs."""
    with pytest.raises(ValueError):
        AttributeBasedTermination("", "attr", lambda x: True)

    with pytest.raises(ValueError):
        AttributeBasedTermination("model", "", lambda x: True)

    with pytest.raises(ValueError):
        AttributeBasedTermination("model", "attr", "not_callable")


def test_composite_termination_or():
    """Test CompositeTermination with OR logic."""
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)

    counter = SimpleCounter("counter")
    se.register_entity(counter)

    # Terminate when EITHER time >= 100 OR counter >= 5
    termination = CompositeTermination([
        TimeBasedTermination(100),
        AttributeBasedTermination("counter", "counter", lambda c: c >= 5)
    ], mode="OR")

    se.init_sim()
    assert termination.should_terminate(se) is False

    # Run 6 steps to ensure counter reaches 5
    for _ in range(6):
        se.schedule()

    # Should terminate even though time < 100
    assert se.get_global_time() < 100
    model = se.get_model("counter")
    assert model.counter >= 5
    assert termination.should_terminate(se) is True


def test_composite_termination_and():
    """Test CompositeTermination with AND logic."""
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)

    counter = SimpleCounter("counter")
    se.register_entity(counter)

    # Terminate when BOTH time >= 10 AND counter >= 5
    termination = CompositeTermination([
        TimeBasedTermination(10),
        AttributeBasedTermination("counter", "counter", lambda c: c >= 5)
    ], mode="AND")

    se.init_sim()
    assert termination.should_terminate(se) is False

    # Run 5 steps (counter = 5, time = 5)
    for _ in range(5):
        se.schedule()

    # Should NOT terminate (counter is 5 but time < 10)
    assert termination.should_terminate(se) is False

    # Run 5 more steps (counter = 10, time = 10)
    for _ in range(5):
        se.schedule()

    # Now should terminate (both conditions met)
    assert termination.should_terminate(se) is True


def test_composite_termination_invalid():
    """Test CompositeTermination with invalid inputs."""
    with pytest.raises(ValueError):
        CompositeTermination([], mode="OR")

    with pytest.raises(ValueError):
        CompositeTermination([TimeBasedTermination(10)], mode="INVALID")

    with pytest.raises(ValueError):
        CompositeTermination(["not_a_condition"], mode="OR")


def test_on_terminate_callback():
    """Test on_terminate callback is called."""

    class CallbackTermination(TerminationCondition):
        def __init__(self):
            self.callback_called = False

        def should_terminate(self, executor):
            return True

        def on_terminate(self, executor):
            self.callback_called = True

    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)
    termination = CallbackTermination()

    termination.on_terminate(se)
    assert termination.callback_called is True


def test_composite_on_terminate():
    """Test CompositeTermination calls on_terminate for triggered conditions."""

    class TrackingTermination(TerminationCondition):
        def __init__(self, should_term):
            self.should_term = should_term
            self.callback_called = False

        def should_terminate(self, executor):
            return self.should_term

        def on_terminate(self, executor):
            self.callback_called = True

    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)

    term1 = TrackingTermination(True)
    term2 = TrackingTermination(False)

    composite = CompositeTermination([term1, term2], mode="OR")
    composite.on_terminate(se)

    # Only term1 should have callback called
    assert term1.callback_called is True
    assert term2.callback_called is False
