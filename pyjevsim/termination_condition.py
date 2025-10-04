"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT. The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module provides termination condition classes for Design of Experiments.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, List

if TYPE_CHECKING:
    from .system_executor import SysExecutor


class TerminationCondition(ABC):
    """Abstract base class for simulation termination conditions."""

    @abstractmethod
    def should_terminate(self, executor: 'SysExecutor') -> bool:
        """
        Determines if the simulation should terminate.

        Args:
            executor (SysExecutor): The simulation executor

        Returns:
            bool: True if simulation should terminate, False otherwise
        """
        pass

    def on_terminate(self, executor: 'SysExecutor') -> None:
        """
        Optional callback when termination condition is met.

        Args:
            executor (SysExecutor): The simulation executor
        """
        pass


class TimeBasedTermination(TerminationCondition):
    """Terminates simulation after specified time."""

    def __init__(self, max_time: float):
        """
        Initialize time-based termination condition.

        Args:
            max_time (float): Maximum simulation time

        Raises:
            ValueError: If max_time is negative
        """
        if max_time < 0:
            raise ValueError(f"max_time must be non-negative, got {max_time}")

        self.max_time = max_time

    def should_terminate(self, executor: 'SysExecutor') -> bool:
        """
        Check if simulation time exceeds maximum time.

        Args:
            executor (SysExecutor): The simulation executor

        Returns:
            bool: True if global_time >= max_time
        """
        return executor.get_global_time() >= self.max_time


class AttributeBasedTermination(TerminationCondition):
    """Terminates when model attribute meets condition."""

    def __init__(self, model_name: str, attribute_path: str,
                 condition_fn: Callable[[any], bool]):
        """
        Initialize attribute-based termination condition.

        Args:
            model_name (str): Name of model to monitor
            attribute_path (str): Dot-separated path to attribute (e.g., "counter" or "state.value")
            condition_fn (Callable): Function that takes attribute value and returns bool

        Raises:
            ValueError: If parameters are invalid
        """
        if not model_name:
            raise ValueError("model_name cannot be empty")
        if not attribute_path:
            raise ValueError("attribute_path cannot be empty")
        if not callable(condition_fn):
            raise ValueError("condition_fn must be callable")

        self.model_name = model_name
        self.attribute_path = attribute_path
        self.condition_fn = condition_fn

    def should_terminate(self, executor: 'SysExecutor') -> bool:
        """
        Check if model attribute meets termination condition.

        Args:
            executor (SysExecutor): The simulation executor

        Returns:
            bool: True if condition is met, False if model not found or condition not met
        """
        try:
            model = executor.get_model(self.model_name)
            value = self._get_nested_attribute(model, self.attribute_path)
            return self.condition_fn(value)
        except (KeyError, AttributeError, IndexError):
            return False

    def _get_nested_attribute(self, obj: any, path: str) -> any:
        """
        Navigate nested attributes using dot notation.

        Args:
            obj (any): Object to navigate
            path (str): Dot-separated attribute path

        Returns:
            any: Attribute value

        Raises:
            AttributeError: If attribute not found
        """
        attrs = path.split('.')
        for attr in attrs:
            obj = getattr(obj, attr)
        return obj


class CompositeTermination(TerminationCondition):
    """Combines multiple termination conditions with AND/OR logic."""

    def __init__(self, conditions: List[TerminationCondition], mode: str = "OR"):
        """
        Initialize composite termination condition.

        Args:
            conditions (list[TerminationCondition]): Conditions to combine
            mode (str): "AND" or "OR" logic

        Raises:
            ValueError: If conditions is empty or mode is invalid
        """
        if not conditions:
            raise ValueError("conditions list cannot be empty")
        if not all(isinstance(c, TerminationCondition) for c in conditions):
            raise ValueError("All conditions must be TerminationCondition instances")

        self.conditions = conditions
        self.mode = mode.upper()

        if self.mode not in ["AND", "OR"]:
            raise ValueError("mode must be 'AND' or 'OR'")

    def should_terminate(self, executor: 'SysExecutor') -> bool:
        """
        Evaluate composite termination condition.

        Args:
            executor (SysExecutor): The simulation executor

        Returns:
            bool: True if composite condition is met
        """
        if self.mode == "AND":
            return all(c.should_terminate(executor) for c in self.conditions)
        else:  # OR
            return any(c.should_terminate(executor) for c in self.conditions)

    def on_terminate(self, executor: 'SysExecutor') -> None:
        """
        Call on_terminate for all conditions that triggered.

        Args:
            executor (SysExecutor): The simulation executor
        """
        for condition in self.conditions:
            if condition.should_terminate(executor):
                condition.on_terminate(executor)
