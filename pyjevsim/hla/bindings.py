"""Binding dataclasses linking pyjevsim ports to HLA FOM identifiers.

Spec: docs/hla/specification.md §1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["in", "out", "inout"]


@dataclass(frozen=True)
class HLAInteraction:
    fom_id: str
    direction: Direction = "out"
    kind: str = "interaction"


@dataclass(frozen=True)
class HLAAttribute:
    fom_id: str
    direction: Direction = "out"
    kind: str = "attribute"
    object_class: str | None = None
