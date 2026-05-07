"""HLAExecutorFactory — produces HLAExecutor for models with bindings.

Spec: docs/hla/specification.md §4.

Users opt in by replacing `sys_exec.exec_factory`. Models listed in
`bindings_by_model` get an HLAExecutor; others get a plain
BehaviorExecutor.
"""

from __future__ import annotations

from ..behavior_executor import BehaviorExecutor
from ..executor_factory import ExecutorFactory
from .hla_executor import HLAExecutor
from .transport import _HLARouter


class HLAExecutorFactory(ExecutorFactory):
    def __init__(self, transport, bindings_by_model: dict) -> None:
        super().__init__()
        self._transport = transport
        self._bindings_by_model = dict(bindings_by_model)
        self._router = _HLARouter(transport)
        # Reject duplicate model names up front — bindings are keyed by
        # name, so two models sharing one name would silently collide.
        if len(self._bindings_by_model) != len({k for k in self._bindings_by_model}):
            raise ValueError("bindings_by_model has duplicate model names")

    def create_behavior_executor(self, _, ins_t, des_t, en_name, model, parent):
        bindings = self._bindings_by_model.get(model.get_name())
        if not bindings:
            return BehaviorExecutor(ins_t, des_t, en_name, model, parent)
        return HLAExecutor(
            ins_t, des_t, en_name, model, parent,
            transport=self._transport,
            bindings=bindings,
            router=self._router,
        )
