"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains a StructuralModel object that allows you to implement the Discrete Event System Specification CoupledModel.
"""

from .core_model import CoreModel
from .definition import ModelType
from .system_message import SysMessage


class StructuralModel(CoreModel):
    """A DEVS coupled model: a container that aggregates child models and
    declares the message flow between them.

    A StructuralModel does **not** define its own state, transition, or
    output behavior. Its job is to expose external input / output ports,
    register child models (atomic or structural), and declare port-level
    coupling relations. ``SysExecutor`` flattens these couplings when
    routing messages so a hierarchical graph behaves identically to a
    flattened one.

    Three coupling patterns are supported through the same
    :py:meth:`coupling_relation` call:

    - **External Input Coupling (EIC):** ``self -> child.in_port``
    - **Internal Coupling (IC):** ``child_a.out -> child_b.in``
    - **External Output Coupling (EOC):** ``child.out -> self``

    See :doc:`pyjevsim_quick_start` for a complete example.
    """

    def __init__(self, _name=""):
        """Initializes a StructuralModel.

        Args:
            _name (str): Identifier used by ``SysExecutor`` for routing
                and by hierarchical lookup. Must be unique within its
                parent scope.
        """
        super().__init__(_name, ModelType.STRUCTURAL)

        self.model_map = {}  # name -> child model
        self.port_map = {}   # (src_obj, src_port) -> [(dst_obj, dst_port), ...]

    def register_entity(self, obj):
        """Registers a child model under this structural model.

        The child is keyed by ``obj.get_name()``; registering a second
        model with the same name overwrites the first.

        Args:
            obj: An ``AtomicModel``, ``BehaviorModel``, or
                ``StructuralModel`` instance to add as a child.
        """
        self.model_map[obj.get_name()] = obj

    def remove_model(self, obj):
        """Removes a child model previously added with
        :py:meth:`register_entity`.

        Existing coupling entries that reference ``obj`` are **not**
        cleaned up automatically; callers should drop them via
        ``port_map`` if needed.

        Args:
            obj: The child model to remove. Must already be registered.
        """
        del self.model_map[obj.get_name()]

    def find_model(self, name):
        """Looks up a registered child model by name.

        Args:
            name (str): The child model's name as returned by
                ``get_name()``.

        Returns:
            The child model instance.

        Raises:
            KeyError: If no child with that name is registered.
        """
        return self.model_map[name]

    def get_models(self):
        """Returns the full ``name -> child model`` mapping.

        Returns:
            dict: The internal ``model_map``. Mutating the returned
            dict mutates the structural model.
        """
        return self.model_map

    def coupling_relation(self, src_obj, src_port, dst_obj, dst_port):
        """Declares a coupling from one (model, port) to another.

        The same ``(src_obj, src_port)`` may be coupled to multiple
        destinations; each call appends a new destination. ``src_obj``
        or ``dst_obj`` may be ``self`` to express EIC or EOC.

        Note: messages are propagated **by reference**; downstream
        receivers should treat them as immutable. See
        :doc:`pyjevsim_quick_start` (Output Messages Are Shared by
        Reference) for the rationale.

        Args:
            src_obj: Source model (or ``self`` for EIC).
            src_port (str): Source port name.
            dst_obj: Destination model (or ``self`` for EOC).
            dst_port (str): Destination port name.
        """
        src = (src_obj, src_port)
        dst = (dst_obj, dst_port)

        if src not in self.port_map:
            self.port_map[src] = []

        self.port_map[src].append(dst)

    def get_couplings(self):
        """Returns the coupling map.

        Returns:
            dict: ``{(src_obj, src_port): [(dst_obj, dst_port), ...]}``
            describing every declared coupling under this structural
            model.
        """
        return self.port_map
