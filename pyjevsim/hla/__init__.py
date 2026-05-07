"""HLA (IEEE 1516-2010) federate support for pyjevsim.

Decorates BehaviorExecutor with output-to-RTI / RTI-to-input bridging,
keeping BehaviorModel pure DEVS. See docs/hla/specification.md for the
contract and docs/hla/instruction.md for the developer guide.
"""

from .bindings import HLAAttribute, HLAInteraction
from .hla_executor import HLAExecutor
from .transport import LoopbackTransport, Transport, _HLARouter

__all__ = [
    "HLAAttribute",
    "HLAExecutor",
    "HLAInteraction",
    "LoopbackTransport",
    "Transport",
    "_HLARouter",
]
