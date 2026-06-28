"""PitchTransport — IEEE 1516-2010 backend for Pitch pRTI via JPype.

Drives a pyjevsim federate against a real Pitch pRTI (``prti1516e.jar``) by
loading the RTI's Java API in-process with JPype. Implements the
:class:`~pyjevsim.hla.transport.RTIConnector` contract so the same DEVS models
that run on ``loopback`` / ``inprocess`` run unchanged against Pitch.

Registered (lazily) under the name ``"pitch"``::

    from pyjevsim.hla import create_rti
    tx = create_rti("pitch",
                    federation="PingPong",
                    federate="ping",
                    fom="examples/hla_pingpong/fom/PingPong.xml",
                    fom_map=PINGPONG_FOM_MAP,
                    jvm_path=r"C:\\Program Files\\...\\jvm.dll",   # optional
                    classpath=[r"C:\\Program Files\\prti1516e\\lib\\prti1516e.jar"])

Requirements (NOT needed to import this module — only to *use* it):
  * ``pip install jpype1`` matching your Python and Java versions
    (JPype >= 1.6 needs Java 9+; for Java 8 pin ``jpype1<=1.5``).
  * Pitch pRTI installed; its ``prti1516e.jar`` on the classpath.
  * A running CRC (Central RTI Component) to ``connect``/``join``.

``fom_map`` describes how each FOM id maps to interaction/object classes and
their field datatypes, so the transport can resolve handles and encode/decode
with the RTI's ``EncoderFactory``::

    PINGPONG_FOM_MAP = {
        "PingPong.Ping":   {"kind": "interaction",
                            "class": "HLAinteractionRoot.Ping",
                            "fields": {"count": "int32", "sender": "string"}},
        "PingPaddle.hits": {"kind": "attribute",
                            "class": "HLAobjectRoot.PingPaddle",
                            "fields": {"hits": "int32"}},
    }

This module is a reference implementation: it targets the prti1516e API
surface but, because a live RTI + matching JVM are required, it is exercised
by the guarded tests in ``tests/hla/test_pitch_backend.py`` (skipped when the
toolchain is absent), while the protocol-level ping-pong logic is verified
deterministically against ``InProcessRTI``.
"""

from __future__ import annotations

import threading
from typing import Any

from ..registry import register_rti
from ..transport import RTICapabilities, RTIConnector


# --------------------------------------------------------------- field codec


def _encode_field(ef, datatype: str, value: Any):
    """Encode one Python value to an HLA byte[] using the EncoderFactory."""
    dt = datatype.lower()
    if dt in ("int", "int32", "integer32"):
        return ef.createHLAinteger32BE(int(value)).toByteArray()
    if dt in ("int64", "integer64"):
        return ef.createHLAinteger64BE(int(value)).toByteArray()
    if dt in ("float", "float64", "double"):
        return ef.createHLAfloat64BE(float(value)).toByteArray()
    if dt in ("string", "unicode"):
        return ef.createHLAunicodeString(str(value)).toByteArray()
    raise ValueError(f"unsupported FOM datatype {datatype!r}")


def _decode_field(ef, datatype: str, raw):
    """Decode one HLA byte[] back to a Python value."""
    dt = datatype.lower()
    if dt in ("int", "int32", "integer32"):
        d = ef.createHLAinteger32BE(); d.decode(raw); return int(d.getValue())
    if dt in ("int64", "integer64"):
        d = ef.createHLAinteger64BE(); d.decode(raw); return int(d.getValue())
    if dt in ("float", "float64", "double"):
        d = ef.createHLAfloat64BE(); d.decode(raw); return float(d.getValue())
    if dt in ("string", "unicode"):
        d = ef.createHLAunicodeString(); d.decode(raw); return str(d.getValue())
    raise ValueError(f"unsupported FOM datatype {datatype!r}")


# ------------------------------------------------------------- the transport


class PitchTransport(RTIConnector):
    """RTIConnector backed by Pitch pRTI (IEEE 1516-2010) through JPype."""

    capabilities = RTICapabilities(
        name="pitch",
        time_management=True,
        timestamp_ordered=True,
        interactions=True,
        object_attributes=True,
        default_lookahead=1.0,
    )

    def __init__(self, federation: str, federate: str, fom: str,
                 fom_map: dict, *, federate_type: str = "pyjevsim",
                 jvm_path: "str | None" = None, classpath=None,
                 lookahead: float = 1.0, codec=None) -> None:
        super().__init__(codec)
        self._federation = federation
        self._federate = federate
        self._federate_type = federate_type
        self._fom = fom
        self._fom_map = dict(fom_map)
        self._jvm_path = jvm_path
        self._classpath = list(classpath or [])
        self._lookahead = float(lookahead)

        # Java handles, resolved after connect/join.
        self._jpype = None
        self._rtiamb = None
        self._ef = None                 # EncoderFactory
        self._time_factory = None
        self._granted = threading.Event()
        self._granted_time = 0.0
        self._logical_time = 0.0        # last granted logical time
        self._reg_enabled = threading.Event()
        self._con_enabled = threading.Event()

        # Federation synchronization points (used to bring multi-process
        # federations up to a common start barrier). label -> Event.
        self._sync_lock = threading.Lock()
        self._sync_announced: dict[str, "threading.Event"] = {}
        self._sync_done: dict[str, "threading.Event"] = {}

        # FOM resolution caches.
        self._ic_handles: dict[str, Any] = {}          # fom_id -> InteractionClassHandle
        self._param_handles: dict[str, dict] = {}      # fom_id -> {field: ParameterHandle}
        self._oc_handles: dict[str, Any] = {}          # fom_id -> ObjectClassHandle
        self._attr_handles: dict[str, dict] = {}       # fom_id -> {field: AttributeHandle}
        self._obj_instances: dict[str, Any] = {}       # fom_id -> ObjectInstanceHandle (ours)
        self._discovered: dict = {}                    # ObjectInstanceHandle -> fom_id (peers)
        self._inbound_oc: dict = {}                    # ObjectClassHandle -> fom_id

        self._boot_jvm()

    # ----------------------------------------------------------- JVM / connect

    def _boot_jvm(self) -> None:
        import jpype  # lazy: only needed when the backend is actually used
        self._jpype = jpype
        if not jpype.isJVMStarted():
            if self._jvm_path:
                jpype.startJVM(self._jvm_path, classpath=self._classpath)
            else:
                jpype.startJVM(classpath=self._classpath)

        RtiFactoryFactory = jpype.JClass("hla.rti1516e.RtiFactoryFactory")
        factory = RtiFactoryFactory.getRtiFactory()
        self._rtiamb = factory.getRtiAmbassador()
        self._ef = factory.getEncoderFactory()
        self._fed_amb = self._build_federate_ambassador()

        CallbackModel = jpype.JClass("hla.rti1516e.CallbackModel")
        # HLA_IMMEDIATE delivers callbacks on RTI-owned threads; our _emit ->
        # insert_external_event is lock-protected, so that is safe.
        self._rtiamb.connect(self._fed_amb, CallbackModel.HLA_IMMEDIATE)

    def _build_federate_ambassador(self):
        # JPype cannot subclass a concrete Java class (NullFederateAmbassador),
        # so we implement the FederateAmbassador *interface* with a JProxy.
        # Only the callbacks we care about are defined; __getattr__ supplies a
        # no-op for every other interface method the RTI may invoke. Method
        # name (not signature) selects the handler, so a single `*rest`
        # definition covers all overloads of an callback.
        jpype = self._jpype
        outer = self

        class _AmbImpl:
            def timeRegulationEnabled(self, theTime):
                outer._reg_enabled.set()

            def timeConstrainedEnabled(self, theTime):
                outer._con_enabled.set()

            def timeAdvanceGrant(self, theTime):
                outer._granted_time = float(theTime.getValue())
                outer._granted.set()

            def receiveInteraction(self, interactionClass, parameters, tag,
                                   *rest):
                outer._on_interaction(interactionClass, parameters, rest)

            def discoverObjectInstance(self, theObject, theObjectClass,
                                       objectName, *rest):
                fom_id = outer._inbound_oc.get(theObjectClass)
                if fom_id is not None:
                    outer._discovered[theObject] = fom_id

            def reflectAttributeValues(self, theObject, attributes, tag,
                                       *rest):
                outer._on_reflect(theObject, attributes, rest)

            def announceSynchronizationPoint(self, label, tag):
                outer._sync_event(outer._sync_announced, str(label)).set()

            def federationSynchronized(self, label, *rest):
                outer._sync_event(outer._sync_done, str(label)).set()

            def __getattr__(self, name):
                if name.startswith("__"):
                    raise AttributeError(name)
                return lambda *a, **k: None

        # Keep a strong reference so the proxy target is not garbage-collected.
        self._amb_impl = _AmbImpl()
        return jpype.JProxy("hla.rti1516e.FederateAmbassador",
                            inst=self._amb_impl)

    # ------------------------------------------------------------- lifecycle

    def _do_join(self, federation: str, federate_name: str, fom_paths) -> None:
        jpype = self._jpype
        File = jpype.JClass("java.io.File")
        modules = [File(p).toURI().toURL() for p in (fom_paths or [self._fom])]
        URLArr = jpype.JArray(jpype.JClass("java.net.URL"))
        AlreadyExists = jpype.JClass(
            "hla.rti1516e.exceptions.FederationExecutionAlreadyExists"
        )
        try:
            self._rtiamb.createFederationExecution(federation, URLArr(modules))
        except AlreadyExists:
            pass  # another federate created it first — fine
        # Any other exception (bad FOM, parse error, ...) propagates.

        self._rtiamb.joinFederationExecution(
            federate_name, self._federate_type, federation, URLArr(modules)
        )

        # Time management: regulating + constrained with our lookahead.
        self._time_factory = self._rtiamb.getTimeFactory()
        interval = self._time_factory.makeInterval(self._lookahead)
        self._rtiamb.enableTimeRegulation(interval)
        self._reg_enabled.wait(timeout=10)
        self._rtiamb.enableTimeConstrained()
        self._con_enabled.wait(timeout=10)

    def _do_publish(self, binding) -> None:
        spec = self._fom_map[binding.fom_id]
        if spec["kind"] == "interaction":
            h = self._interaction_handle(binding.fom_id, spec)
            self._rtiamb.publishInteractionClass(h)
        else:
            oc, attrs = self._object_handles(binding.fom_id, spec)
            self._rtiamb.publishObjectClassAttributes(oc, attrs)
            # Register our instance up front so updates have a target.
            self._obj_instances[binding.fom_id] = \
                self._rtiamb.registerObjectInstance(oc)

    def _do_subscribe(self, binding) -> None:
        spec = self._fom_map[binding.fom_id]
        if spec["kind"] == "interaction":
            h = self._interaction_handle(binding.fom_id, spec)
            self._rtiamb.subscribeInteractionClass(h)
        else:
            oc, attrs = self._object_handles(binding.fom_id, spec)
            self._inbound_oc[oc] = binding.fom_id
            self._rtiamb.subscribeObjectClassAttributes(oc, attrs)

    def _do_resign(self) -> None:
        jpype = self._jpype
        OAD = jpype.JClass("hla.rti1516e.ResignAction")
        try:
            self._rtiamb.resignFederationExecution(OAD.DELETE_OBJECTS_THEN_DIVEST)
        except jpype.JException:
            pass
        try:
            self._rtiamb.destroyFederationExecution(self._federation)
        except jpype.JException:
            pass  # other federates still joined — fine

    def _do_close(self) -> None:
        if self._rtiamb is not None:
            try:
                self._rtiamb.disconnect()
            except Exception:
                pass
        # We deliberately do NOT shutdown the JVM: other transports in the
        # same process may still need it, and JPype cannot restart a JVM.

    # ----------------------------------------------------------- data plane

    def _do_send(self, binding, wire: Any, timestamp: "float | None") -> None:
        spec = self._fom_map[binding.fom_id]
        # wire is the pyjevsim payload (list); ping-pong inserts one dict.
        record = wire[0] if isinstance(wire, (list, tuple)) and wire else wire
        # TSO send time: the model's output() runs inside step(granted), so the
        # earliest legal timestamp is the current logical time + lookahead.
        send_t = timestamp if timestamp is not None else \
            self._logical_time + self._lookahead
        if spec["kind"] == "interaction":
            self._send_interaction(binding.fom_id, spec, record, send_t)
        else:
            self._update_attributes(binding.fom_id, spec, record, send_t)

    def _send_interaction(self, fom_id, spec, record, send_t) -> None:
        h = self._interaction_handle(fom_id, spec)
        params = self._rtiamb.getParameterHandleValueMapFactory().create(
            len(spec["fields"])
        )
        ph = self._param_handles[fom_id]
        for field, dtype in spec["fields"].items():
            params.put(ph[field], _encode_field(self._ef, dtype, record[field]))
        tag = self._jpype.JArray(self._jpype.JByte)(0)
        self._rtiamb.sendInteraction(
            h, params, tag, self._time_factory.makeTime(float(send_t))
        )

    def _update_attributes(self, fom_id, spec, record, send_t) -> None:
        oc, _attrs = self._object_handles(fom_id, spec)
        obj = self._obj_instances[fom_id]
        amap = self._rtiamb.getAttributeHandleValueMapFactory().create(
            len(spec["fields"])
        )
        ah = self._attr_handles[fom_id]
        for field, dtype in spec["fields"].items():
            amap.put(ah[field], _encode_field(self._ef, dtype, record[field]))
        tag = self._jpype.JArray(self._jpype.JByte)(0)
        self._rtiamb.updateAttributeValues(
            obj, amap, tag, self._time_factory.makeTime(float(send_t))
        )

    # --------------------------------------------------------- inbound (RTI)

    def _on_interaction(self, interactionClass, parameters, rest) -> None:
        fom_id = self._ic_by_handle(interactionClass)
        if fom_id is None:
            return
        spec = self._fom_map[fom_id]
        ph = self._param_handles[fom_id]
        record = {
            field: _decode_field(self._ef, dtype, parameters.get(ph[field]))
            for field, dtype in spec["fields"].items()
        }
        self._emit("interaction", fom_id, [record], _extract_time(rest))

    def _on_reflect(self, theObject, attributes, rest) -> None:
        fom_id = self._discovered.get(theObject)
        if fom_id is None:
            return
        spec = self._fom_map[fom_id]
        ah = self._attr_handles[fom_id]
        record = {
            field: _decode_field(self._ef, dtype, attributes.get(ah[field]))
            for field, dtype in spec["fields"].items()
            if attributes.containsKey(ah[field])
        }
        self._emit("attribute", fom_id, [record], _extract_time(rest))

    # ------------------------------------------------------- time advance

    def _do_request_time_advance(self, target: float) -> float:
        self._granted.clear()
        self._rtiamb.timeAdvanceRequest(self._time_factory.makeTime(float(target)))
        self._granted.wait()
        self._logical_time = self._granted_time
        return self._granted_time

    # ------------------------------------------------- synchronization points

    def _sync_event(self, table, label):
        with self._sync_lock:
            ev = table.get(label)
            if ev is None:
                ev = table[label] = threading.Event()
            return ev

    def register_sync_point(self, label: str) -> None:
        """Register a federation synchronization point (one federate calls
        this; the RTI then announces it to all joined federates)."""
        tag = self._jpype.JArray(self._jpype.JByte)(0)
        self._rtiamb.registerFederationSynchronizationPoint(label, tag)

    def wait_sync_announced(self, label: str, timeout: float = 30.0) -> bool:
        """Block until the RTI announces ``label`` to this federate."""
        return self._sync_event(self._sync_announced, label).wait(timeout)

    def achieve_sync_point(self, label: str) -> None:
        """Tell the RTI this federate has reached ``label``."""
        self._rtiamb.synchronizationPointAchieved(label)

    def wait_synchronized(self, label: str, timeout: float = 30.0) -> bool:
        """Block until every federate has achieved ``label`` (the RTI then
        reports the federation as synchronized)."""
        return self._sync_event(self._sync_done, label).wait(timeout)

    # --------------------------------------------------------- FOM handles

    def _interaction_handle(self, fom_id, spec):
        h = self._ic_handles.get(fom_id)
        if h is None:
            h = self._rtiamb.getInteractionClassHandle(spec["class"])
            self._ic_handles[fom_id] = h
            self._param_handles[fom_id] = {
                field: self._rtiamb.getParameterHandle(h, field)
                for field in spec["fields"]
            }
        return h

    def _object_handles(self, fom_id, spec):
        oc = self._oc_handles.get(fom_id)
        if oc is None:
            oc = self._rtiamb.getObjectClassHandle(spec["class"])
            self._oc_handles[fom_id] = oc
            ahs = self._rtiamb.getAttributeHandleSetFactory().create()
            handles = {}
            for field in spec["fields"]:
                a = self._rtiamb.getAttributeHandle(oc, field)
                handles[field] = a
                ahs.add(a)
            self._attr_handles[fom_id] = handles
            self._attr_set_cache = getattr(self, "_attr_set_cache", {})
            self._attr_set_cache[fom_id] = ahs
        return oc, self._attr_set_cache[fom_id]

    def _ic_by_handle(self, handle):
        for fom_id, h in self._ic_handles.items():
            if h.equals(handle):
                return fom_id
        return None


def _extract_time(rest):
    """Pull a LogicalTime value out of the trailing callback args, if any."""
    for a in rest:
        getv = getattr(a, "getValue", None)
        if callable(getv):
            try:
                return float(getv())
            except Exception:
                continue
    return None


register_rti("pitch", lambda **kw: PitchTransport(**kw))
