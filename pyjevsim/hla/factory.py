"""Create HLA-aware executors for models that have port bindings.

Assign an ``HLAExecutorFactory`` to ``sys_exec.exec_factory`` before
registering models. Models absent from ``bindings_by_model`` continue to use
``BehaviorExecutor``. See ``docs/hla/specification.md`` section 4.
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
        # Bindings are indexed by model name.
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
