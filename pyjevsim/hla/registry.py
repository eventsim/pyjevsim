"""RTI backend registry — select an RTI by name.

Lets applications choose an RTI without importing the backend class:

    from pyjevsim.hla import create_rti, available_rtis

    transport = create_rti("loopback")
    # transport = create_rti("pitch", fom="Chat.xml", host="localhost")

Third-party / optional backends register themselves at import time:

    from pyjevsim.hla import register_rti
    register_rti("pitch", lambda **kw: PitchTransport(**kw))

Backends are kept out of the core import path so that an optional
dependency (e.g. JPype for Pitch, a ZMQ surrogate, ...) is only required
when that backend is actually requested.
"""

from __future__ import annotations

from typing import Callable, Dict

from .transport import LoopbackTransport, RTIConnector

#: name -> factory(**kwargs) -> RTIConnector
_BACKENDS: Dict[str, Callable[..., RTIConnector]] = {}


def register_rti(name: str, factory: Callable[..., RTIConnector],
                 *, replace: bool = False) -> None:
    """Register an RTI backend factory under ``name``.

    Args:
        name: lookup key used by :func:`create_rti` (case-insensitive).
        factory: callable returning an :class:`RTIConnector` (or any object
            satisfying the ``Transport`` structural type). Called with the
            keyword arguments passed to :func:`create_rti`.
        replace: allow overwriting an existing registration. Defaults to
            False so accidental name clashes fail loudly.
    """
    key = name.lower()
    if key in _BACKENDS and not replace:
        raise ValueError(
            f"RTI backend {name!r} already registered "
            f"(pass replace=True to override)"
        )
    _BACKENDS[key] = factory


def unregister_rti(name: str) -> None:
    """Remove a backend registration if present (no error if absent)."""
    _BACKENDS.pop(name.lower(), None)


def available_rtis() -> list[str]:
    """Sorted list of registered backend names."""
    return sorted(_BACKENDS)


def create_rti(name: str, **kwargs):
    """Instantiate the named RTI backend.

    Raises:
        KeyError: if ``name`` is not registered. The message lists the
            backends that are available.
    """
    key = name.lower()
    try:
        factory = _BACKENDS[key]
    except KeyError:
        raise KeyError(
            f"unknown RTI backend {name!r}; "
            f"available: {available_rtis() or '[none registered]'}"
        ) from None
    return factory(**kwargs)


# Built-in backend(s). Optional backends register from their own modules so
# their dependencies stay lazy.
register_rti("loopback", lambda **kw: LoopbackTransport(**kw))
