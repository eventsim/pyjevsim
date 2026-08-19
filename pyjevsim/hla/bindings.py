"""Binding dataclasses linking pyjevsim ports to HLA FOM identifiers.

Spec: docs/hla/specification.md §1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Direction = Literal["in", "out", "inout"]
_VALID_DIRECTIONS = frozenset(("in", "out", "inout"))


def _validate_direction(direction: object) -> None:
    """Reject binding directions that the runtime cannot route safely."""
    if not isinstance(direction, str) or direction not in _VALID_DIRECTIONS:
        allowed = ", ".join(sorted(_VALID_DIRECTIONS))
        raise ValueError(
            f"direction must be one of {{{allowed}}}; got {direction!r}"
        )


@dataclass(frozen=True)
class HLAInteraction:
    fom_id: str
    direction: Direction = "out"
    kind: str = field(default="interaction", init=False)

    def __post_init__(self) -> None:
        _validate_direction(self.direction)


@dataclass(frozen=True)
class HLAAttribute:
    fom_id: str
    direction: Direction = "out"
    kind: str = field(default="attribute", init=False)
    object_class: str | None = None

    def __post_init__(self) -> None:
        _validate_direction(self.direction)
