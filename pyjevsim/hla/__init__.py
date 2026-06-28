"""HLA (IEEE 1516-2010) federate support for pyjevsim.

Decorates BehaviorExecutor with output-to-RTI / RTI-to-input bridging,
keeping BehaviorModel pure DEVS. See docs/hla/specification.md for the
contract, docs/hla/instruction.md for the developer guide, and
docs/hla/rti_interface.md for how to add a new RTI backend.
"""

from .bindings import HLAAttribute, HLAInteraction
from .factory import HLAExecutorFactory
from .federate import Federate
from .hla_executor import HLAExecutor
from .registry import (
    available_rtis,
    create_rti,
    register_rti,
    unregister_rti,
)
from .transport import (
    Codec,
    IdentityCodec,
    LoopbackTransport,
    RTICapabilities,
    RTIConnector,
    Transport,
    _HLARouter,
)

# Importing the backends package registers the built-in RTI backends
# ("inprocess" always; "pitch" lazily). Kept last to avoid import cycles.
from . import backends  # noqa: E402,F401
from .backends.inprocess import InProcessFederation, InProcessRTI  # noqa: E402

__all__ = [
    "Codec",
    "Federate",
    "HLAAttribute",
    "HLAExecutor",
    "HLAExecutorFactory",
    "HLAInteraction",
    "IdentityCodec",
    "InProcessFederation",
    "InProcessRTI",
    "LoopbackTransport",
    "RTICapabilities",
    "RTIConnector",
    "Transport",
    "_HLARouter",
    "available_rtis",
    "create_rti",
    "register_rti",
    "unregister_rti",
]
