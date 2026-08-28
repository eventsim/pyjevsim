"""Native GORTI adapter using the optional :mod:`rti1516e` Python SDK.

The module itself has no GORTI dependency.  Selecting the backend loads the
SDK lazily::

    from pyjevsim.hla import create_rti

    tx = create_rti(
        "gorti",
        federation="PingPong",
        federate="ping",
        fom="examples/hla_pingpong/fom/PingPong.xml",
        fom_map=PINGPONG_FOM_MAP,
        url="grpc://127.0.0.1:7000",
    )

``fom_map`` uses the same shape as the Pitch and Portico adapters.  The
backend supports interactions, object attributes, regulating/constrained
logical time, and callback delivery through ``RTIConnector._emit``.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace
from typing import Any

from ..registry import register_rti
from ..transport import RTICapabilities, RTIConnector


_DATATYPE_ALIASES = {
    "int": "HLAinteger32BE",
    "int32": "HLAinteger32BE",
    "integer32": "HLAinteger32BE",
    "int64": "HLAinteger64BE",
    "integer64": "HLAinteger64BE",
    "float": "HLAfloat64BE",
    "float64": "HLAfloat64BE",
    "double": "HLAfloat64BE",
    "string": "HLAunicodeString",
    "unicode": "HLAunicodeString",
}
_MISSING = object()


def _load_sdk():
    """Load GORTI only when a connector is instantiated."""
    try:
        from rti1516e import (
            FederationExecutionAlreadyExists,
            Rti1516eAmbassador,
        )
        from rti1516e.encoding import codec_for
    except ImportError as exc:
        raise ImportError(
            "the GORTI backend requires the optional rti1516e SDK; "
            "install it from a GORTI source checkout with "
            "'pip install -e <gorti>/pysdk'"
        ) from exc
    return SimpleNamespace(
        FederationExecutionAlreadyExists=FederationExecutionAlreadyExists,
        Rti1516eAmbassador=Rti1516eAmbassador,
        codec_for=codec_for,
    )


def _datatype_spec(datatype: Any) -> Any:
    """Translate Pitch-compatible primitive aliases to GORTI codec names."""
    if isinstance(datatype, str):
        return _DATATYPE_ALIASES.get(datatype.lower(), datatype)
    if isinstance(datatype, dict):
        return datatype
    raise TypeError(
        "FOM datatype must be a string or a GORTI codec descriptor; "
        f"got {type(datatype).__name__}"
    )


class _GortiFieldCodec:
    """Small cache around GORTI's IEEE 1516.2 codec dispatcher."""

    def __init__(self, codec_for) -> None:
        self._codec_for = codec_for
        self._cache: dict[str, Any] = {}

    def _get(self, datatype: Any):
        spec = _datatype_spec(datatype)
        if not isinstance(spec, str):
            return self._codec_for(spec)
        codec = self._cache.get(spec)
        if codec is None:
            codec = self._cache[spec] = self._codec_for(spec)
        return codec

    def encode(self, datatype: Any, value: Any) -> bytes:
        return bytes(self._get(datatype).encode(value))

    def decode(self, datatype: Any, raw: Any) -> Any:
        data = bytes(raw)
        value, end = self._get(datatype).decode(data, 0)
        if end != len(data):
            raise ValueError(
                f"{_datatype_spec(datatype)!r} decoder consumed {end} of "
                f"{len(data)} bytes"
            )
        return value


class _GortiCallbacks:
    """Callback target kept separate from the SDK Ambassador implementation."""

    def __init__(self, owner: "GortiTransport") -> None:
        self._owner = owner

    def receiveInteraction(  # noqa: N802 - IEEE 1516.1 callback name
        self,
        class_name: str,
        parameters: dict[Any, Any],
        timestamp: "float | None",
    ) -> None:
        self._owner._on_interaction(class_name, parameters, timestamp)

    def discoverObjectInstance(  # noqa: N802
        self,
        object_handle: Any,
        class_name: str,
        instance_name: str,
        object_class: Any = None,
    ) -> None:
        self._owner._on_discover(
            object_handle, class_name, instance_name, object_class
        )

    def reflectAttributeValues(  # noqa: N802
        self,
        object_handle: Any,
        values: dict[Any, Any],
        timestamp: "float | None",
        attribute_values: "dict[Any, bytes] | None" = None,
    ) -> None:
        self._owner._on_reflect(
            object_handle, values, timestamp, attribute_values
        )

    def removeObjectInstance(  # noqa: N802
        self, object_handle: Any, tag: bytes, timestamp: "float | None"
    ) -> None:
        del tag, timestamp
        self._owner._discovered.pop(object_handle, None)

    def timeAdvanceGrant(self, time: float) -> None:  # noqa: N802
        self._owner._on_time_advance_grant(time)

    def federationHalted(  # noqa: N802
        self, cause: str, stalled_federate_handle: int
    ) -> None:
        self._owner._on_federation_halted(cause, stalled_federate_handle)

    def __getattr__(self, name: str):
        # The GORTI Ambassador can dispatch service-group callbacks that this
        # minimal connector does not consume.  Keep them harmless while still
        # rejecting Python protocol lookups.
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *args, **kwargs: None


class GortiTransport(RTIConnector):
    """RTIConnector backed by the native GORTI Python SDK."""

    capabilities = RTICapabilities(
        name="gorti",
        time_management=True,
        timestamp_ordered=True,
        interactions=True,
        object_attributes=True,
        default_lookahead=1.0,
    )

    def __init__(
        self,
        federation: str,
        federate: str,
        fom: str,
        fom_map: dict,
        *,
        url: str = "grpc://127.0.0.1:7000",
        lookahead: float = 1.0,
        time_advance_timeout: "float | None" = None,
        codec=None,
    ) -> None:
        super().__init__(codec)
        if lookahead <= 0:
            raise ValueError("lookahead must be positive")
        if time_advance_timeout is not None and time_advance_timeout <= 0:
            raise ValueError("time_advance_timeout must be positive or None")

        self._federation = federation
        self._federate = federate
        self._fom = fom
        self._fom_map = dict(fom_map)
        self._url = url
        self._lookahead = float(lookahead)
        self._time_advance_timeout = time_advance_timeout
        self._logical_time = 0.0

        self._sdk = _load_sdk()
        self._field_codec = _GortiFieldCodec(self._sdk.codec_for)
        self._amb = self._sdk.Rti1516eAmbassador()
        self._callbacks = _GortiCallbacks(self)
        self._connected = False

        self._granted = threading.Event()
        self._time_lock = threading.Lock()
        self._granted_time = 0.0
        self._halted: "str | None" = None

        self._ic_handles: dict[str, Any] = {}
        self._param_handles: dict[str, dict[str, Any]] = {}
        self._oc_handles: dict[str, Any] = {}
        self._attr_handles: dict[str, dict[str, Any]] = {}
        self._obj_instances: dict[str, Any] = {}
        self._inbound_ic: dict[Any, str] = {}
        self._inbound_ic_names: dict[str, str] = {}
        self._inbound_oc: dict[Any, str] = {}
        self._inbound_oc_names: dict[str, str] = {}
        self._discovered: dict[Any, str] = {}

        try:
            self._amb.connect(self._callbacks, self._url)
            self._connected = True
        except Exception:
            try:
                self._amb.disconnect()
            except Exception:
                pass
            raise

    # ------------------------------------------------------------- lifecycle

    def _do_join(self, federation: str, federate_name: str, fom_paths) -> None:
        modules = list(fom_paths or ([self._fom] if self._fom else []))
        self._federation = federation
        self._federate = federate_name
        try:
            self._amb.createFederationExecution(federation, modules)
        except self._sdk.FederationExecutionAlreadyExists:
            pass

        joined = False
        try:
            # Supplying modules on join populates GORTI's local FOM handle and
            # callback-name tables even when a peer created the federation.
            self._amb.joinFederationExecution(
                federate_name, federation, modules
            )
            joined = True
            self._amb.enableTimeRegulation(self._lookahead)
            self._amb.enableTimeConstrained()
        except Exception:
            if joined:
                try:
                    self._amb.resignFederationExecution(
                        "CANCEL_THEN_DELETE_THEN_DIVEST"
                    )
                except Exception:
                    pass
            raise

    def _do_publish(self, binding) -> None:
        spec = self._spec(binding)
        if spec["kind"] == "interaction":
            handle = self._interaction_handle(binding.fom_id, spec)
            self._amb.publishInteractionClass(handle)
            return
        object_class, attributes = self._object_handles(binding.fom_id, spec)
        self._amb.publishObjectClassAttributes(object_class, attributes)
        self._obj_instances[binding.fom_id] = self._amb.registerObjectInstance(
            object_class
        )

    def _do_subscribe(self, binding) -> None:
        spec = self._spec(binding)
        if spec["kind"] == "interaction":
            handle = self._interaction_handle(binding.fom_id, spec)
            self._inbound_ic[handle] = binding.fom_id
            self._inbound_ic_names[spec["class"]] = binding.fom_id
            self._inbound_ic_names[str(handle)] = binding.fom_id
            self._inbound_ic_names[_numeric_handle_key(handle)] = binding.fom_id
            self._amb.subscribeInteractionClass(handle)
            return
        object_class, attributes = self._object_handles(binding.fom_id, spec)
        self._inbound_oc[object_class] = binding.fom_id
        self._inbound_oc_names[spec["class"]] = binding.fom_id
        self._inbound_oc_names[str(object_class)] = binding.fom_id
        self._inbound_oc_names[_numeric_handle_key(object_class)] = binding.fom_id
        self._amb.subscribeObjectClassAttributes(object_class, attributes)

    def _do_resign(self) -> None:
        pending: "Exception | None" = None
        try:
            self._amb.resignFederationExecution(
                "CANCEL_THEN_DELETE_THEN_DIVEST"
            )
        except Exception as exc:
            pending = exc
        try:
            self._amb.destroyFederationExecution(self._federation)
        except Exception:
            # Destruction normally fails while peers remain joined.
            pass
        finally:
            self._obj_instances.clear()
            self._discovered.clear()
        if pending is not None:
            raise pending

    def _do_close(self) -> None:
        if not self._connected:
            return
        self._connected = False
        self._halted = self._halted or "transport closed"
        self._granted.set()
        try:
            self._amb.disconnect()
        except Exception:
            # ``RTIConnector.close`` is a best-effort, idempotent cleanup API.
            pass

    # ------------------------------------------------------------- data plane

    def _do_send(self, binding, wire: Any, timestamp: "float | None") -> None:
        spec = self._spec(binding)
        record = wire[0] if isinstance(wire, (list, tuple)) and wire else wire
        if not isinstance(record, dict):
            raise TypeError(
                "GORTI bindings require a mapping payload or a one-item "
                "list containing a mapping"
            )
        send_time = float(
            timestamp
            if timestamp is not None
            else self._logical_time + self._lookahead
        )
        if spec["kind"] == "interaction":
            handle = self._interaction_handle(binding.fom_id, spec)
            params = {
                self._param_handles[binding.fom_id][field]:
                    self._field_codec.encode(datatype, record[field])
                for field, datatype in spec["fields"].items()
            }
            self._amb.sendInteraction(handle, params, timestamp=send_time)
            return

        self._object_handles(binding.fom_id, spec)
        try:
            object_handle = self._obj_instances[binding.fom_id]
        except KeyError:
            raise RuntimeError(
                f"attribute binding {binding.fom_id!r} was not published "
                "before send()"
            ) from None
        values = {
            self._attr_handles[binding.fom_id][field]:
                self._field_codec.encode(datatype, record[field])
            for field, datatype in spec["fields"].items()
        }
        self._amb.updateAttributeValues(
            object_handle, values, timestamp=send_time
        )

    # -------------------------------------------------------------- callbacks

    def _on_interaction(
        self,
        class_name: Any,
        parameters: dict[Any, Any],
        timestamp: "float | None",
    ) -> None:
        fom_id = self._inbound_ic.get(class_name)
        if fom_id is None:
            fom_id = self._inbound_ic_names.get(str(class_name))
        if fom_id is None:
            fom_id = self._inbound_ic_names.get(_numeric_handle_key(class_name))
        if fom_id is None:
            return
        spec = self._fom_map[fom_id]
        handles = self._param_handles[fom_id]
        record = self._decode_record(spec, handles, parameters)
        self._emit("interaction", fom_id, [record], timestamp)

    def _on_discover(
        self,
        object_handle: Any,
        class_name: Any,
        instance_name: str,
        object_class: Any,
    ) -> None:
        del instance_name
        fom_id = self._inbound_oc.get(object_class)
        if fom_id is None:
            fom_id = self._inbound_oc_names.get(str(object_class))
        if fom_id is None:
            fom_id = self._inbound_oc_names.get(
                _numeric_handle_key(object_class)
            )
        if fom_id is None:
            fom_id = self._inbound_oc_names.get(str(class_name))
        if fom_id is None:
            fom_id = self._inbound_oc_names.get(_numeric_handle_key(class_name))
        if fom_id is not None:
            self._discovered[object_handle] = fom_id

    def _on_reflect(
        self,
        object_handle: Any,
        values: dict[Any, Any],
        timestamp: "float | None",
        attribute_values: "dict[Any, bytes] | None",
    ) -> None:
        fom_id = self._discovered.get(object_handle)
        if fom_id is None:
            return
        spec = self._fom_map[fom_id]
        handles = self._attr_handles[fom_id]
        wire_values = attribute_values or values
        record = self._decode_record(
            spec, handles, wire_values, allow_partial=True
        )
        if record:
            self._emit("attribute", fom_id, [record], timestamp)

    def _on_time_advance_grant(self, granted: float) -> None:
        self._granted_time = float(granted)
        self._granted.set()

    def _on_federation_halted(
        self, cause: str, stalled_federate_handle: int
    ) -> None:
        self._halted = (
            f"federation halted ({cause}); stalled federate "
            f"{stalled_federate_handle}"
        )
        self._granted.set()

    # --------------------------------------------------------------- time axis

    def _do_request_time_advance(self, target: float) -> float:
        with self._time_lock:
            if self._halted is not None:
                raise RuntimeError(self._halted)
            self._granted.clear()
            self._amb.timeAdvanceRequest(float(target))
            if not self._granted.wait(timeout=self._time_advance_timeout):
                raise TimeoutError(
                    f"timeAdvanceGrant({target:g}) was not received within "
                    f"{self._time_advance_timeout:g} seconds"
                )
            if self._halted is not None:
                raise RuntimeError(self._halted)
            self._logical_time = self._granted_time
            return self._granted_time

    # ------------------------------------------------------------ FOM helpers

    def _spec(self, binding) -> dict:
        try:
            spec = self._fom_map[binding.fom_id]
        except KeyError:
            raise KeyError(
                f"no GORTI FOM mapping for {binding.fom_id!r}"
            ) from None
        kind = spec.get("kind")
        if kind not in ("interaction", "attribute"):
            raise ValueError(
                f"FOM mapping {binding.fom_id!r} has unsupported kind "
                f"{kind!r}"
            )
        if kind != binding.kind:
            raise ValueError(
                f"binding {binding.fom_id!r} is {binding.kind!r}, but its "
                f"FOM mapping is {kind!r}"
            )
        if not isinstance(spec.get("class"), str) or not isinstance(
            spec.get("fields"), dict
        ):
            raise ValueError(
                f"FOM mapping {binding.fom_id!r} requires string 'class' "
                "and mapping 'fields' entries"
            )
        return spec

    def _interaction_handle(self, fom_id: str, spec: dict):
        handle = self._ic_handles.get(fom_id)
        if handle is None:
            handle = self._amb.getInteractionClassHandle(spec["class"])
            self._ic_handles[fom_id] = handle
            self._param_handles[fom_id] = {
                field: self._amb.getParameterHandle(handle, field)
                for field in spec["fields"]
            }
        return handle

    def _object_handles(self, fom_id: str, spec: dict):
        object_class = self._oc_handles.get(fom_id)
        if object_class is None:
            object_class = self._amb.getObjectClassHandle(spec["class"])
            self._oc_handles[fom_id] = object_class
            self._attr_handles[fom_id] = {
                field: self._amb.getAttributeHandle(object_class, field)
                for field in spec["fields"]
            }
        return object_class, list(self._attr_handles[fom_id].values())

    def _decode_record(
        self,
        spec: dict,
        handles: dict[str, Any],
        wire_values: dict[Any, Any],
        *,
        allow_partial: bool = False,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {}
        for field, datatype in spec["fields"].items():
            handle = handles[field]
            raw = _mapping_value(wire_values, handle, field)
            if raw is _MISSING:
                if allow_partial:
                    continue
                raise KeyError(f"callback omitted required field {field!r}")
            if isinstance(raw, (bytes, bytearray, memoryview)):
                record[field] = self._field_codec.decode(datatype, raw)
            else:
                # In-process SDK transports may already expose a Python value.
                record[field] = raw
        return record


def _mapping_value(values: dict[Any, Any], handle: Any, field: str) -> Any:
    keys = [handle, field, str(handle), _numeric_handle_key(handle)]
    # Older/current gRPC callback translation may expose parameter handle 1
    # under the bridge-compatible ``_payload`` alias when its local FOM name
    # table cannot account for the MIM handle offset.
    try:
        if int(handle) == 1:
            keys.append("_payload")
    except (TypeError, ValueError):
        pass
    for key in keys:
        try:
            return values[key]
        except (KeyError, TypeError):
            continue
    return _MISSING


def _numeric_handle_key(handle: Any) -> str:
    """Normalize GORTI's typed-int handles to the numeric callback key."""
    try:
        return str(int(handle))
    except (TypeError, ValueError):
        return str(handle)


register_rti("gorti", lambda **kw: GortiTransport(**kw))
