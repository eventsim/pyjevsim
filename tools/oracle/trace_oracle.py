#!/usr/bin/env python
"""Order-insensitive behavioural trace oracle for pyjevsim engine changes.

``--repo`` defaults to the repository that contains this file.  Run all
scenarios against a checkout and write a full digest (traces included, for
local diffs):

    python tools/oracle/trace_oracle.py [--repo <checkout>] --out <digest.json>
                                        [--jobs 4] [--scenarios a,b,...]
                                        [--skip a,b,...] [--no-slow] [--salt N]

Write only the per-scenario hashes (small enough to commit or to compare in
CI), or compare a run with a committed golden file:

    python tools/oracle/trace_oracle.py --out <hashes.json> --hash-only
    python tools/oracle/trace_oracle.py --golden tools/oracle/golden/v2.2.0.json
    python tools/oracle/trace_oracle.py --golden <new.json> --write-golden

Compare two digests or hash files (exit 0 = every verdict scenario matches):

    python tools/oracle/trace_oracle.py --compare base.json cand.json [--max-lines 25]

Check which scenarios are order-sensitive on one checkout (re-runs every
scenario with the executor hash perturbed, i.e. a different same-time
set-iteration order, and reports digests that move):

    python tools/oracle/trace_oracle.py --perturb-check <dir> [--salts 1,2,3]

``order_check.py`` does the same without sorting inside an instant.

How it works
------------
Each scenario runs in a fresh ``python`` subprocess with ``<checkout>`` at
``sys.path[0]`` (asserted), so this file can check any checkout or ``git
archive`` export, including ones that predate it.  Scenario models that are
not part of the checkout under test come from ``oracle_models.py`` next to
this file.  Inside the subprocess the runner monkey-patches (never edits)
the checkout:

* ``SysExecutor._run_instant`` is wrapped so every call opens a *group*
  (engine label, instant).  If a candidate removes ``_run_instant`` the runner
  falls back to wrapping ``schedule``/``step`` and splitting a group whenever
  an ``output`` follows a transition (same boundaries in normal operation);
  the digest records ``grouping`` so ``--compare`` can warn.
* ``output / int_trans / ext_trans / con_trans`` are wrapped on every
  ``BehaviorModel`` subclass (model level, so it is independent of how the
  executors / SnapshotExecutor / HLAExecutor / StructuralExecutor dispatch).
  Each call records ``label|kind|port|gt=<model.global_time at entry>|payload``;
  output records the messages it inserted; con_trans records its bag sorted;
  nested calls (default con_trans -> int/ext) are tagged ``con>int`` etc.
* SnapshotCondition hooks are recorded where the snapshot scenario uses them.
* At group close: new ``output_event_queue`` entries, the canonical state of
  every model touched in the group, and captured ``print`` lines are added.
  Events, states, emits and print lines are SORTED within the group (so
  same-time processing order does not matter); groups stay in sequence.
* Models are labelled by name, with ``#k`` (rank by ``get_obj_id``) when
  names repeat.  Object ids, memory addresses and wall time never enter the
  digest.

A scenario marked ``informational`` is inherently order-sensitive (its
outcome depends on set-iteration order, which the engine does not fix yet);
its mismatch is reported but does not fail ``--compare``.  The ``strict``
section (raw dill bytes of snapshot files) is warn-only because it embeds
object ids.

A scenario's hash covers its trace, its final summary and the first line of
any error.  Model names, printed text and float reprs are part of it; object
ids, memory addresses, paths and wall time are not.
"""

import argparse
import copy
import gzip
import hashlib
import io
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import types

ORACLE_VERSION = 1
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO = os.path.dirname(os.path.dirname(HERE))
FIXED_SALT = 7919           # used for informational (order-sensitive) scenarios
INLINE_LIMIT = 4000          # groups; larger traces go to the sidecar gz only
HASHES_FORMAT = "pyjevsim-oracle-hashes"
# The golden CI compares with. When a semantic change is accepted (see
# LEDGER.md), its pull request adds a new golden and points this at it.
GOLDEN = os.path.join(HERE, "golden", "v2.2.0.json")


# --------------------------------------------------------------------------
# canonical representation
# --------------------------------------------------------------------------

_SKIP_ATTR_PREFIX = ("_SystemObject__",)
STATIC_MODEL_KEYS = {
    "external_input_ports", "external_output_ports",
    "external_transition_map_tuple", "external_transition_map_state",
    "internal_transition_map_tuple", "internal_transition_map_state",
    "model_type", "_name",
}
_BIG = 256


class Canon:
    """Canonical, address/id-free repr of arbitrary model data."""

    def __init__(self):
        self.SysMessage = None
        self.CoreModel = None
        self.Executor = None
        self.SysExecutor = None

    def bind(self):
        from pyjevsim.system_message import SysMessage
        from pyjevsim.core_model import CoreModel
        from pyjevsim.executor import Executor
        from pyjevsim.system_executor import SysExecutor
        self.SysMessage, self.CoreModel = SysMessage, CoreModel
        self.Executor, self.SysExecutor = Executor, SysExecutor

    def __call__(self, o, d=0, path=None):
        t = type(o)
        if o is None or t is bool or t is int or t is str or t is float:
            return repr(o)
        if t is bytes:
            return "b#" + hashlib.sha1(o).hexdigest()[:16]
        if d > 7:
            return "<" + t.__name__ + ">"
        if path is None:
            path = set()
        oid = id(o)
        if oid in path:
            return "<cycle " + t.__name__ + ">"
        if self.SysMessage is not None and isinstance(o, self.SysMessage):
            path.add(oid)
            try:
                r = "Msg(%s,%s,%s,%s)" % (self(o.get_src(), d + 1, path), self(o.get_dst(), d + 1, path),
                                          self(o.get_msg_time(), d + 1, path),
                                          self(o.retrieve(), d + 1, path))
            finally:
                path.discard(oid)
            return r
        if self.SysExecutor is not None and isinstance(o, self.SysExecutor):
            return "<SysExecutor>"
        if self.CoreModel is not None and isinstance(o, self.CoreModel):
            try:
                return "M<" + str(o.get_name()) + ">"
            except Exception:
                return "M<?>"
        if self.Executor is not None and isinstance(o, self.Executor):
            try:
                return "X<" + str(o.get_name()) + ">"
            except Exception:
                return "X<?>"
        if isinstance(o, random.Random):
            return "Random#" + hashlib.sha1(repr(o.getstate()).encode()).hexdigest()[:12]
        if isinstance(o, (types.FunctionType, types.MethodType, types.BuiltinFunctionType, type, types.ModuleType)):
            return "<fn " + getattr(o, "__qualname__", getattr(o, "__name__", t.__name__)) + ">"
        path.add(oid)
        try:
            if t is list or t is tuple or isinstance(o, (list, tuple)) or t.__name__ == "deque":
                items = list(o)
                if len(items) > _BIG:
                    body = ",".join(self(x, d + 1, path) for x in items)
                    return "%s[%d]#%s" % (t.__name__, len(items), hashlib.sha1(body.encode()).hexdigest()[:16])
                br = "()" if isinstance(o, tuple) else "[]"
                return br[0] + ",".join(self(x, d + 1, path) for x in items) + br[1]
            if isinstance(o, dict):
                parts = sorted(self(k, d + 1, path) + ":" + self(v, d + 1, path) for k, v in o.items())
                if len(parts) > _BIG:
                    return "dict[%d]#%s" % (len(parts), hashlib.sha1(",".join(parts).encode()).hexdigest()[:16])
                return "{" + ",".join(parts) + "}"
            if isinstance(o, (set, frozenset)):
                return "set{" + ",".join(sorted(self(x, d + 1, path) for x in o)) + "}"
            if hasattr(o, "__dict__") and not isinstance(o, type):
                try:
                    v = vars(o)
                except TypeError:
                    v = None
                if v is not None:
                    kv = {k: x for k, x in v.items() if not k.startswith(_SKIP_ATTR_PREFIX)}
                    return t.__name__ + self(kv, d + 1, path)
            if hasattr(o, "__slots__"):
                kv = {s: getattr(o, s) for s in o.__slots__ if hasattr(o, s)}
                return t.__name__ + self(kv, d + 1, path)
            r = repr(o)
            if " at 0x" in r:
                return "<" + t.__name__ + ">"
            return r
        finally:
            path.discard(oid)


canon = Canon()


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# recorder
# --------------------------------------------------------------------------

class _Capture(io.TextIOBase):
    def __init__(self, rec):
        self.rec = rec

    def write(self, s):
        self.rec.text(s)
        return len(s)

    def flush(self):
        pass


class Group:
    __slots__ = ("eng", "t", "mode", "events", "touched", "text", "emits", "oq_len", "seq", "had_trans")

    def __init__(self, eng, t, mode, seq):
        self.eng, self.t, self.mode, self.seq = eng, t, mode, seq
        self.events = []          # (model, kind, port, gt, payload)
        self.touched = {}         # model -> None (ordered set)
        self.text = []
        self.emits = []
        self.oq_len = None
        self.had_trans = False


class Recorder:
    def __init__(self):
        self.lines = []           # finished group records (with model refs)
        self.stack = []           # open groups
        self.mstack = []          # (model, kind) of model methods executing
        self.seq = 0
        self.engines = []
        self.models = {}          # model -> first-seen index
        self.labels_override = {}
        self.state_fns = {}       # class -> fn(model) -> obj
        self.exclude = set()
        self.grouping = "run_instant"
        self.finals = []
        self.strict = {}
        self.info = {}
        self.outside = None
        self.armed = False
        self._real_stdout = None
        self.heuristic = False

    # ---- labels
    def see(self, m):
        if m not in self.models:
            self.models[m] = len(self.models)

    def set_label(self, m, label):
        self.labels_override[m] = label
        self.see(m)

    def compute_labels(self):
        # include every registered model of every known engine
        for e in self.engines:
            try:
                for lst in list(getattr(e, "model_map", {}).values()):
                    for ex in lst:
                        self.see(ex.get_core_model())
            except Exception:
                pass
        by_name = {}
        for m in self.models:
            if m in self.labels_override:
                continue
            by_name.setdefault(str(m.get_name()), []).append(m)
        lab = dict(self.labels_override)
        for name, ms in by_name.items():
            if len(ms) == 1:
                lab[ms[0]] = name
            else:
                ms.sort(key=lambda x: (x.get_obj_id(), self.models[x]))
                for k, m in enumerate(ms):
                    lab[m] = "%s#%d" % (name, k)
        self._labels = lab
        el = {}
        for k, e in enumerate(sorted(self.engines, key=lambda x: x.get_obj_id())):
            el[e] = "E%d" % k
        self._elabels = el

    def label(self, m):
        return self._labels.get(m, str(m.get_name()))

    def elabel(self, e):
        return self._elabels.get(e, "E?") if e is not None else "-"

    # ---- groups
    def _cur(self):
        if self.stack:
            return self.stack[-1]
        if self.outside is None:
            self.seq += 1
            self.outside = Group(None, None, "outside", self.seq)
        return self.outside

    def _close_outside(self):
        if self.outside is not None:
            self._finish(self.outside)
            self.outside = None

    def open_group(self, eng, t, mode="instant"):
        self._close_outside()
        self.seq += 1
        g = Group(eng, t, mode, self.seq)
        try:
            g.oq_len = len(eng.output_event_queue)
        except Exception:
            g.oq_len = None
        self.stack.append(g)
        return g

    def close_group(self):
        g = self.stack.pop()
        self._finish(g)

    def _finish(self, g):
        if g.eng is not None and g.oq_len is not None:
            try:
                q = list(g.eng.output_event_queue)
                if len(q) >= g.oq_len:
                    g.emits = [canon(x) for x in q[g.oq_len:]]
            except Exception:
                pass
        states = []
        for m in g.touched:
            states.append((m, self.state_of(m)))
        txt = "".join(g.text).splitlines()
        if not g.events and not txt and not g.emits:
            return
        self.lines.append(("G", g.eng, g.t, g.mode, g.events, states, txt, g.emits))

    def state_of(self, m):
        fn = None
        for c in type(m).__mro__:
            fn = self.state_fns.get(c)
            if fn is not None:
                break
        if fn is not None:
            return canon(fn(m))
        try:
            v = vars(m)
        except TypeError:
            return "?"
        kv = {k: x for k, x in v.items()
              if k not in STATIC_MODEL_KEYS and k not in self.exclude and not k.startswith(_SKIP_ATTR_PREFIX)}
        return canon(kv)

    def heuristic_split(self, is_output):
        """In fallback mode split the open group when an output follows a transition."""
        if not self.heuristic or not self.stack:
            return
        g = self.stack[-1]
        if g.mode != "heur":
            return
        if is_output and g.had_trans:
            eng = g.eng
            self.close_group()
            self.open_group(eng, eng.global_time, "heur")

    def event(self, m, kind, port, payload):
        if self.mstack:
            kind = self.mstack[-1][1] + ">" + kind
        g = self._cur()
        self.see(m)
        try:
            gt = repr(m.global_time)
        except Exception:
            gt = "NA"
        rec = [m, kind, port, gt, payload]
        g.events.append(rec)
        g.touched[m] = None
        if kind in ("int_trans", "ext_trans", "con_trans"):
            g.had_trans = True
        return rec

    def text(self, s):
        self._cur().text.append(s)

    def checkpoint(self, tag, data):
        self._close_outside()
        self.lines.append(("C", tag, canon(data)))

    def current_model(self):
        return self.mstack[-1][0] if self.mstack else None

    # ---- serialise
    def canonical_lines(self, raw_order=False):
        """One JSON line per group or checkpoint.

        Events, print lines and emits are sorted within a group unless
        ``raw_order`` is set, in which case they keep the order in which
        the engine produced them (used by ``order_check.py``)."""
        self.compute_labels()
        order = list if raw_order else sorted
        out = []
        for rec in self.lines:
            if rec[0] == "C":
                out.append(json.dumps(["CP", rec[1], rec[2]], ensure_ascii=False))
                continue
            _, eng, t, mode, events, states, txt, emits = rec
            ev = order("%s|%s|%s|gt=%s|%s" % (self.label(m), k, p, gt, pl) for m, k, p, gt, pl in events)
            st = sorted("%s=%s" % (self.label(m), s) for m, s in states)
            out.append(json.dumps([self.elabel(eng), repr(t), mode, ev, st, order(txt), order(emits)],
                                  ensure_ascii=False))
        return out


REC = Recorder()


# --------------------------------------------------------------------------
# instrumentation
# --------------------------------------------------------------------------

def _payload_of_bag(port_msgs):
    return "[" + ",".join(sorted("(%s,%s)" % (canon(p), canon(m)) for p, m in port_msgs)) + "]"


def _make_wrapper(kind, f):
    rec = REC
    if kind == "output":
        def w(self, md, *a, **k):
            ev = rec.heuristic_split(True)
            ev = rec.event(self, "output", "", "")
            try:
                before = len(md.get_contents())
            except Exception:
                before = None
            rec.mstack.append((self, "output"))
            try:
                r = f(self, md, *a, **k)
            finally:
                rec.mstack.pop()
            try:
                new = md.get_contents()[before:] if before is not None else []
                ev[4] = "[" + ",".join(canon(x) for x in new) + "]"
            except Exception:
                ev[4] = "?"
            return r
    elif kind == "int_trans":
        def w(self, *a, **k):
            rec.event(self, "int_trans", "", "")
            rec.mstack.append((self, "int_trans"))
            try:
                return f(self, *a, **k)
            finally:
                rec.mstack.pop()
    elif kind == "ext_trans":
        def w(self, port, msg, *a, **k):
            rec.event(self, "ext_trans", str(port), canon(msg))
            rec.mstack.append((self, "ext_trans"))
            try:
                return f(self, port, msg, *a, **k)
            finally:
                rec.mstack.pop()
    elif kind == "con_trans":
        def w(self, port_msgs, *a, **k):
            if not isinstance(port_msgs, (list, tuple)):
                port_msgs = list(port_msgs)
            rec.event(self, "con_trans", "", _payload_of_bag(port_msgs))
            rec.mstack.append((self, "con_trans"))
            try:
                return f(self, port_msgs, *a, **k)
            finally:
                rec.mstack.pop()
    w._oracle_wrapped = True
    w.__wrapped__ = f
    w.__name__ = getattr(f, "__name__", kind)
    w.__qualname__ = getattr(f, "__qualname__", kind)
    return w


def arm():
    """Wrap model methods on every BehaviorModel subclass (idempotent)."""
    from pyjevsim.behavior_model import BehaviorModel
    stack, seen = [BehaviorModel], set()
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(c.__subclasses__())
        for kind in ("output", "int_trans", "ext_trans", "con_trans"):
            f = c.__dict__.get(kind)
            if f is None or getattr(f, "_oracle_wrapped", False):
                continue
            if isinstance(f, (staticmethod, classmethod)):
                continue
            setattr(c, kind, _make_wrapper(kind, f))
    REC.armed = True


def install_engine_hooks(salt=None):
    from pyjevsim import system_executor as se_mod
    SE = se_mod.SysExecutor
    canon.bind()

    orig_init = SE.__init__

    def init_w(self, *a, **k):
        REC.engines.append(self)
        return orig_init(self, *a, **k)
    SE.__init__ = init_w

    if hasattr(SE, "_run_instant"):
        orig_ri = SE._run_instant

        def ri_w(self, instant, imminent, *a, **k):
            REC.open_group(self, instant)
            try:
                return orig_ri(self, instant, imminent, *a, **k)
            finally:
                REC.close_group()
        SE._run_instant = ri_w
        REC.grouping = "run_instant"
    else:
        REC.grouping = "heuristic"
        REC.heuristic = True
        for name in ("schedule", "step"):
            orig = getattr(SE, name)

            def mk(orig):
                def w(self, *a, **k):
                    REC.open_group(self, self.global_time, "heur")
                    try:
                        return orig(self, *a, **k)
                    finally:
                        REC.close_group()
                return w
            setattr(SE, name, mk(orig))

    if salt is not None:
        from pyjevsim.executor import Executor

        def h(self):
            return hash((salt, self.get_obj_id()))
        Executor.__hash__ = h


# --------------------------------------------------------------------------
# helpers used by scenarios
# --------------------------------------------------------------------------

def req_time_of(ex):
    for o in (ex, getattr(ex, "behavior_executor", None)):
        if o is not None and hasattr(o, "request_time"):
            return o.request_time
    return "NA"


def engine_final(ss):
    """Labelled end-of-run engine summary (call from a REC.finals callback)."""
    act = []
    for ex in list(ss.active_obj_map.values()):
        m = ex.get_core_model()
        act.append("%s@%s" % (REC.label(m), repr(req_time_of(ex))))
    wait = {}
    for t, lst in getattr(ss, "waiting_obj_map", {}).items():
        wait[repr(t)] = sorted(REC.label(ex.get_core_model()) for ex in lst)
    try:
        q = [canon(x) for x in ss.get_generated_event()]
    except Exception:
        q = "?"
    return {
        "global_time": repr(ss.global_time),
        "next_event_time": repr(ss.get_next_event_time()),
        "active_req_times": sorted(act),
        "waiting": wait,
        "output_event_queue": q if q == "?" else sorted(q),
        "input_event_queue_len": len(ss.input_event_queue),
        "terminated": ss.is_terminated(),
    }


def final_states(models):
    return {REC.label(m): REC.state_of(m) for m in models}


def all_models(ss):
    out = []
    for lst in ss.model_map.values():
        for ex in lst:
            out.append(ex.get_core_model())
    return out


def active_labels(ss):
    """Names (not labels: labels are assigned after the run) of active models."""
    return sorted(str(ex.get_core_model().get_name()) for ex in ss.active_obj_map.values())


# --------------------------------------------------------------------------
# scenarios
# --------------------------------------------------------------------------

def sc_devstone(variant, depth, width, events):
    def run(repo):
        from benchmark.devstone.topology import build_devstone
        ss, h = build_devstone(variant=variant, depth=depth, width=width,
                               gen_count=events, gen_period=1.0, dhrystones=0)
        arm()
        ss.simulate(events * 1.0 + depth + 2, _tm=False)
        ext_total = int_total = 0
        counts = {}
        for level in h["levels"]:
            for a in level:
                e, i = a.get_counts()
                counts[a.get_name()] = [e, i]
                ext_total += e
                int_total += i
        REC.info["transitions"] = ext_total + int_total
        REC.finals.append(lambda: {
            "counts": counts, "transitions": ext_total + int_total, "ext": ext_total, "int": int_total,
            "sink_received": h["sink"].get_received(), "gen_fired": h["gen"].get_fired(),
            "engine": engine_final(ss), "states": final_states(all_models(ss))})
    return run


def sc_devstone_counts(variant, depth, width, events):
    """Uninstrumented run (benchmark-sized): only per-atomic counts are digested."""
    def run(repo):
        from benchmark.devstone.topology import build_devstone
        ss, h = build_devstone(variant=variant, depth=depth, width=width,
                               gen_count=events, gen_period=1.0, dhrystones=0)
        ss.simulate(events * 1.0 + depth + 2, _tm=False)
        counts, ext_total, int_total = {}, 0, 0
        for level in h["levels"]:
            for a in level:
                e, i = a.get_counts()
                counts[a.get_name()] = [e, i]
                ext_total += e
                int_total += i
        REC.info["transitions"] = ext_total + int_total
        REC.finals.append(lambda: {
            "counts": counts, "transitions": ext_total + int_total, "ext": ext_total, "int": int_total,
            "sink_received": h["sink"].get_received(), "gen_fired": h["gen"].get_fired(),
            "global_time": repr(ss.global_time)})
    return run


def sc_ring(repo):
    """1000 relay models in a ring; 3 tokens injected as external events at
    different times; most models are idle at any instant (sparse FEL)."""
    from pyjevsim.behavior_model import BehaviorModel
    from pyjevsim.definition import ExecutionType, Infinite
    from pyjevsim.system_executor import SysExecutor
    from pyjevsim.system_message import SysMessage

    class Relay(BehaviorModel):
        def __init__(self, name, delay):
            super().__init__(name)
            self.insert_state("idle", Infinite)
            self.insert_state("busy", delay)
            self.init_state("idle")
            self.insert_input_port("in")
            self.insert_output_port("out")
            self.tokens = []
            self.passed = 0

        def ext_trans(self, port, msg):
            self.tokens.append(msg.retrieve()[0])
            self.tokens.sort()
            if self._cur_state == "idle":
                self._cur_state = "busy"
            else:
                self.cancel_rescheduling()

        def int_trans(self):
            self.passed += len(self.tokens)
            self.tokens = []
            self._cur_state = "idle"

        def output(self, md):
            for tok in self.tokens:
                m = SysMessage(self.get_name(), "out")
                m.insert((tok[0], tok[1] + 1))
                md.insert_message(m)

    N = 1000
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    ring = [Relay("r%04d" % i, 1 + (i % 3) * 0.5) for i in range(N)]
    for r in ring:
        ss.register_entity(r)
    for i in range(N):
        ss.coupling_relation(ring[i], "out", ring[(i + 1) % N], "in")
    for k, (start, at) in enumerate(((0, 0), (333, 5), (0, 7.5))):
        port = "inj%d" % k
        ss.insert_input_port(port)
        ss.coupling_relation(None, port, ring[start], "in")
        ss.insert_external_event(port, ("tok%d" % k, 0), scheduled_time=at)
    arm()
    for chunk in range(6):
        ss.simulate(500, _tm=False)
        REC.checkpoint("ring%d" % chunk, {"t": ss.global_time, "next": ss.get_next_event_time(),
                                          "passed": sum(r.passed for r in ring)})
    REC.finals.append(lambda: {"engine": engine_final(ss),
                               "passed": {r.get_name(): r.passed for r in ring if r.passed}})


def _bank_common(repo, canonical):
    import bank_driver
    if canonical:
        from examples.banksim.model import model_user_gen, model_queue, model_result
        model_user_gen.random = _RngProxy("bank1")
        _make_replay(model_queue.BankQueue,
                     ["user", "dropped_user", "usable_proc", "_cur_state", "_states", "_cancel_reschedule_f"])
        _make_replay(model_result.BankResult,
                     ["user", "drop_user", "user_count", "drop_user_count", "_cur_state"])
        REC.state_fns[model_result.BankResult] = lambda m: {
            "user_count": m.user_count, "drop_user_count": m.drop_user_count,
            "n_user": len(m.user), "n_drop": len(m.drop_user), "gt": m.global_time}
    ss, h = bank_driver.build_bank(repo, seed=1)
    if not canonical:
        from examples.banksim.model import model_result
        REC.state_fns[model_result.BankResult] = lambda m: {
            "user_count": m.user_count, "drop_user_count": m.drop_user_count,
            "n_user": len(m.user), "n_drop": len(m.drop_user), "gt": m.global_time}
    arm()

    def tick(k):
        if (k + 1) % 250 == 0:
            REC.checkpoint("tick%d" % (k + 1), {"t": ss.global_time, "next": ss.get_next_event_time(),
                                               "out": bank_driver.outcome(ss, h, False)})
    stopped = bank_driver.run_bank(ss, 3000, tick)
    res = bank_driver.outcome(ss, h, stopped)
    REC.info["outcome"] = res
    REC.finals.append(lambda: {"outcome": res, "engine": engine_final(ss),
                               "states": final_states(all_models(ss))})


def sc_bank_raw(repo):
    _bank_common(repo, canonical=False)


def sc_bank_canon(repo):
    _bank_common(repo, canonical=True)


class _RngProxy:
    """Per-model RNG: ``random.X`` resolves to the RNG of the model whose
    method is executing (seeded by name), so draws do not depend on the
    order in which same-time models are processed."""

    def __init__(self, seed):
        self._seed = seed
        self._ctor = random.Random(seed + ":ctor")
        self._per = {}

    def _rng(self):
        m = REC.current_model()
        if m is None:
            return self._ctor
        r = self._per.get(m)
        if r is None:
            r = self._per[m] = random.Random("%s:%s" % (self._seed, m.get_name()))
        return r

    def __getattr__(self, n):
        return getattr(self._rng(), n)


_REPLAY = {}


def _make_replay(cls, attrs):
    """Make ``cls.ext_trans`` independent of message order within one group:
    on each call the pre-bag state is restored and the bag-so-far is
    replayed in canonical order (only for order-sensitive example models)."""
    orig = cls.__dict__["ext_trans"]

    def ext(self, port, msg):
        st = _REPLAY.get(self)
        key = REC.stack[-1].seq if REC.stack else -REC.seq
        if st is None or st[0] != key:
            snap = {a: copy.copy(getattr(self, a)) for a in attrs}
            st = _REPLAY[self] = [key, snap, []]
        st[2].append((port, msg))
        for a, v in st[1].items():
            setattr(self, a, copy.copy(v))
        for p, m in sorted(st[2], key=lambda pm: (str(pm[0]), canon(pm[1]))):
            orig(self, p, m)
    ext.__name__ = "ext_trans"
    cls.ext_trans = ext


def sc_structural(repo):
    from pyjevsim.definition import ExecutionType
    from pyjevsim.system_executor import SysExecutor
    from oracle_models import STM
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    gen = STM("Gen")
    se.register_entity(gen)
    se.insert_input_port("start")
    se.coupling_relation(None, "start", gen, "start")
    se.insert_external_event("start", None)
    arm()
    se.simulate(5)
    sub = list(gen.get_models().values())
    REC.finals.append(lambda: {"engine": engine_final(se), "sub_states": final_states(sub)})


def sc_confluent(repo):
    from pyjevsim.behavior_model import BehaviorModel
    from pyjevsim.definition import ExecutionType
    from pyjevsim.system_executor import SysExecutor
    from pyjevsim.system_message import SysMessage
    from oracle_models import CounterAtomic, OneShotEmitter
    REC.exclude.add("_log")       # shared append-log: order-sensitive by design

    class _TimedAtomic(BehaviorModel):   # replica of the local class in the test
        def __init__(self, name, deadline):
            super().__init__(name)
            self.insert_state("active", deadline)
            self.insert_state("done")
            self.init_state("active")
            self.insert_input_port("in")
            self.insert_output_port("out")
            self.n_int = self.n_ext = self.n_con = 0

        def ext_trans(self, port, msg):
            self.n_ext += 1

        def int_trans(self):
            self.n_int += 1
            self._cur_state = "done"

        def con_trans(self, port_msgs):
            self.n_con += 1
            self._cur_state = "done"

        def output(self, md):
            if self._cur_state == "active":
                m = SysMessage(self.get_name(), "out")
                m.insert(1)
                md.insert_message(m)

    engines = []
    # 1) test_confluent_fires_when_both_imminent_and_receiving
    log = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    seed, a, b = OneShotEmitter(), CounterAtomic("A", log), CounterAtomic("B", log)
    for m in (seed, a, b):
        ss.register_entity(m)
    ss.coupling_relation(seed, "out", a, "in")
    ss.coupling_relation(seed, "out", b, "in")
    ss.coupling_relation(a, "out", b, "in")
    arm()
    ss.simulate(5, _tm=False)
    REC.checkpoint("c1", {"log": sorted(log), "A": [a.n_int, a.n_ext, a.n_con], "B": [b.n_int, b.n_ext, b.n_con]})
    engines.append(ss)
    # 2) test_confluent_on_external_event_path_v_time
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    ta = _TimedAtomic("TA", deadline=2.0)
    ss.register_entity(ta)
    ss.insert_input_port("ext_in")
    ss.coupling_relation(None, "ext_in", ta, "in")
    ss.insert_external_event("ext_in", None, scheduled_time=2)
    arm()
    ss.simulate(5, _tm=False)
    REC.checkpoint("c2", {"TA": [ta.n_int, ta.n_ext, ta.n_con]})
    engines.append(ss)
    # 3) test_no_confluent_when_only_imminent
    log3 = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    a3 = CounterAtomic("A3", log3)
    ss.register_entity(a3)
    ss.insert_input_port("kick")
    ss.coupling_relation(None, "kick", a3, "in")
    ss.insert_external_event("kick", None)
    ss.simulate(5, _tm=False)
    REC.checkpoint("c3", {"log": log3, "A3": [a3.n_int, a3.n_ext, a3.n_con]})
    engines.append(ss)
    REC.finals.append(lambda: {"engines": [engine_final(e) for e in engines]})


def sc_cancel(repo):
    from oracle_models import build_cancel
    engines = []
    for use_cancel, n in ((True, 3), (False, 3), (True, 20)):
        ss, log = build_cancel(use_cancel=use_cancel, poke_count=n)
        arm()
        ss.simulate(12, _tm=False)
        REC.checkpoint("cancel_%s_%d" % (use_cancel, n), {"log": log})
        engines.append(ss)
    REC.finals.append(lambda: {"engines": [engine_final(e) for e in engines]})


def sc_vtime(repo):
    from pyjevsim.behavior_model import BehaviorModel
    from pyjevsim.definition import ExecutionType
    from pyjevsim.system_executor import SysExecutor
    from pyjevsim.system_message import SysMessage
    from oracle_models import build_vtime
    engines = []
    for period, count, horizon in ((1, 5, 20), (1000, 3, 5000), (1000, 100, 120_000), (10, 10, 25)):
        ss, gl, sl = build_vtime(period=period, count=count)
        arm()
        ss.simulate(horizon, _tm=False)
        REC.checkpoint("vt_%s_%s_%s" % (period, count, horizon), {"gen": gl, "sink": sl})
        engines.append(ss)

    class FractionalGen(BehaviorModel):   # replica of the local class in the test
        def __init__(self, log, ss_ref):
            super().__init__("fgen")
            self.insert_state("active", 2.5)
            self.insert_state("done")
            self.init_state("active")
            self.insert_output_port("out")
            self.fired = 0
            self._log = log
            self._ss = ss_ref

        def ext_trans(self, port, msg):
            pass

        def int_trans(self):
            if self._cur_state == "active":
                self.fired += 1
                self._log.append(self._ss.global_time)
                if self.fired >= 3:
                    self._cur_state = "done"

        def output(self, md):
            if self._cur_state == "active":
                m = SysMessage(self.get_name(), "out")
                m.insert(self.fired)
                md.insert_message(m)

    log = []
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    ss.register_entity(FractionalGen(log, ss))
    arm()
    ss.simulate(20, _tm=False)
    REC.checkpoint("vt_frac", {"log": log})
    engines.append(ss)
    REC.finals.append(lambda: {"engines": [engine_final(e) for e in engines]})


def sc_destruction(repo):
    from pyjevsim.behavior_model import BehaviorModel
    from pyjevsim.definition import ExecutionType, Infinite
    from pyjevsim.system_executor import SysExecutor
    from pyjevsim.system_message import SysMessage
    from oracle_models import build_destruction
    engines = []
    # test_entities_destroyed_at_correct_time
    times = [50, 25, 75, 10, 100, 5, 30, 60, 15, 40]
    ss = build_destruction(times)
    arm()
    ss.simulate(1, _tm=False)
    REC.checkpoint("d0", {"active": active_labels(ss), "pending": ss._destructs_pending})
    prev = 1
    for ct in sorted(set(times)):
        ss.simulate(ct - prev, _tm=False)
        prev = ct
        REC.checkpoint("d%d" % ct, {"t": ss.global_time, "active": active_labels(ss),
                                    "pending": ss._destructs_pending})
    engines.append(ss)
    # test_no_destruction_when_all_infinite
    ss = build_destruction([Infinite, Infinite])
    ss.simulate(1000, _tm=False)
    REC.checkpoint("dinf", {"active": active_labels(ss), "pending": ss._destructs_pending})
    engines.append(ss)

    # coupled variant: a generator and a receiver are destroyed mid-run;
    # messages to a destroyed receiver must be dropped, couplings cleaned up.
    class Gen(BehaviorModel):
        def __init__(self, name, period):
            super().__init__(name)
            self.insert_state("active", period)
            self.init_state("active")
            self.insert_output_port("out")
            self.n = 0

        def ext_trans(self, port, msg):
            pass

        def int_trans(self):
            self.n += 1

        def output(self, md):
            m = SysMessage(self.get_name(), "out")
            m.insert(self.n)
            md.insert_message(m)

    class Recv(BehaviorModel):
        def __init__(self, name):
            super().__init__(name)
            self.insert_state("idle", Infinite)
            self.insert_state("busy", 0.5)
            self.init_state("idle")
            self.insert_input_port("in")
            self.insert_output_port("ack")
            self.got = []

        def ext_trans(self, port, msg):
            self.got.append(msg.retrieve()[0])
            self.got.sort()          # keep the model order-insensitive
            self._cur_state = "busy"

        def int_trans(self):
            self._cur_state = "idle"

        def output(self, md):
            m = SysMessage(self.get_name(), "ack")
            m.insert(len(self.got))
            md.insert_message(m)

    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    g1, g2 = Gen("g1", 1), Gen("g2", 1.5)
    r1, r2 = Recv("r1"), Recv("r2")
    ss.register_entity(g1, inst_t=0, dest_t=7)
    ss.register_entity(g2, inst_t=2)
    ss.register_entity(r1, inst_t=0, dest_t=10)
    ss.register_entity(r2)
    ss.insert_output_port("acks")
    ss.coupling_relation(g1, "out", r1, "in")
    ss.coupling_relation(g1, "out", r2, "in")
    ss.coupling_relation(g2, "out", r1, "in")
    ss.coupling_relation(g2, "out", r2, "in")
    ss.coupling_relation(r1, "ack", None, "acks")
    ss.coupling_relation(r2, "ack", None, "acks")
    arm()
    for k in range(16):
        ss.simulate(1, _tm=False)
        REC.checkpoint("dc%d" % k, {"t": ss.global_time, "active": active_labels(ss),
                                    "ports": len(ss.port_map)})
    engines.append(ss)
    REC.finals.append(lambda: {"engines": [engine_final(e) for e in engines],
                               "states": final_states([g1, g2, r1, r2])})


def _instant_models():
    from pyjevsim.behavior_model import BehaviorModel
    from pyjevsim.definition import Infinite
    from pyjevsim.system_message import SysMessage

    class Timed(BehaviorModel):
        """Periodic model; counts transitions; ext on 'in2' cancels rescheduling."""

        def __init__(self, name, deadline, period, emit_port="out"):
            super().__init__(name)
            self.insert_state("active", deadline)
            self.insert_state("idle", Infinite)
            self.init_state("active")
            for p in ("in", "in2"):
                self.insert_input_port(p)
            self.insert_output_port(emit_port)
            self._emit_port = emit_port
            self._period = period
            self.n_int = self.n_ext = self.n_out = 0
            self.recv = {}

        def ext_trans(self, port, msg):
            self.n_ext += 1
            vals = msg.retrieve()
            key = "%s:%s" % (port, ",".join(sorted(repr(v) for v in vals)))
            self.recv[key] = self.recv.get(key, 0) + 1
            if port == "in2":
                self.cancel_rescheduling()
            else:
                self.update_state("active", self._period)
                self._cur_state = "active"

        def int_trans(self):
            self.n_int += 1
            if self.n_int >= 6:
                self._cur_state = "idle"
            else:
                self.update_state("active", self._period)

        def output(self, md):
            self.n_out += 1
            m = SysMessage(self.get_name(), self._emit_port)
            m.insert(self.get_name())
            m.insert(self.n_out)
            md.insert_message(m)

    class CustomCon(Timed):
        def con_trans(self, port_msgs):
            # ext-then-int ordering, as allowed by the API
            for port, msg in port_msgs:
                self.ext_trans(port, msg)
            self.int_trans()

    return Timed, CustomCon


def _instant_build(ex_mode, res, scale, track_uncaught=False):
    from pyjevsim.system_executor import SysExecutor
    Timed, CustomCon = _instant_models()
    ss = SysExecutor(res, ex_mode=ex_mode, snapshot_manager=None, track_uncaught=track_uncaught)
    A = Timed("A", 2 * scale, 1.5 * scale)
    B = CustomCon("B", 3 * scale, 1 * scale)
    C = Timed("C", 4 * scale, 2 * scale, emit_port="loose")   # 'loose' is uncoupled
    D = Timed("D", 2 * scale, 2 * scale)
    for m in (A, B, C, D):
        ss.register_entity(m)
    for p in ("x1", "x2", "bcast"):
        ss.insert_input_port(p)
    ss.insert_output_port("eo")
    ss.coupling_relation(None, "x1", A, "in")
    ss.coupling_relation(None, "x2", C, "in")
    ss.coupling_relation(None, "bcast", A, "in2")
    ss.coupling_relation(None, "bcast", B, "in2")
    ss.coupling_relation(None, "bcast", C, "in2")
    ss.coupling_relation(A, "out", B, "in")
    ss.coupling_relation(B, "out", None, "eo")
    ss.coupling_relation(B, "out", C, "in")
    ss.coupling_relation(D, "out", A, "in")
    ss.coupling_relation(D, "out", None, "eo")
    # external events coinciding with internal ones (A, D imminent at 2*scale)
    ss.insert_external_event("x1", "e-x1@2", scheduled_time=2 * scale)
    ss.insert_external_event("x2", "e-x2a@2", scheduled_time=2 * scale)
    ss.insert_external_event("x2", "e-x2b@2", scheduled_time=2 * scale)
    ss.insert_external_event("bcast", "e-b@3", scheduled_time=3 * scale)
    ss.insert_custom_external_event("bcast", ["c1", "c2"], scheduled_time=3 * scale)
    ss.insert_external_event("x1", "e-x1@5.5", scheduled_time=5.5 * scale)
    ss.insert_external_event("nope", "bad-port", scheduled_time=1)    # prints Port Not Found
    return ss, [A, B, C, D]


def sc_same_instant(repo):
    from pyjevsim.definition import ExecutionType
    engines, models = [], []
    # V_TIME, default uncaught handling, events inserted between simulate calls
    for tu in (False, True):
        ss, ms = _instant_build(ExecutionType.V_TIME, 1, 1, track_uncaught=tu)
        arm()
        for k in range(4):
            ss.simulate(1, _tm=False)
            REC.checkpoint("v%d_%d" % (tu, k), {"t": ss.global_time, "next": ss.get_next_event_time()})
        ss.insert_external_event("x2", "late@now", 0)          # due at the current instant
        ss.insert_external_event("bcast", "late@+0.5", 0.5)
        ss.simulate(12, _tm=False)
        try:
            rel = sorted("%s.%s->%s" % (canon(k[0]), k[1], canon(v)) for k, v in ss.get_relation().items())
        except Exception as e:   # get_relation fails on SysExecutor-sourced couplings in the base
            rel = "raises %s" % type(e).__name__
        REC.checkpoint("v%d_end" % tu, {"t": ss.global_time, "relation": rel})
        engines.append(ss)
        models += ms
    # legacy immediate delivery path (deprecated API, still public)
    ss, ms = _instant_build(ExecutionType.V_TIME, 1, 1)
    arm()
    ss.simulate(1, _tm=False)
    ss.insert_external_event("x2", "legacy", 0)
    ss.handle_external_input_event()
    ss.simulate(6, _tm=False)
    REC.checkpoint("legacy_end", {"t": ss.global_time})
    engines.append(ss)
    models += ms
    # HLA_TIME: step(granted)
    ss, ms = _instant_build(ExecutionType.HLA_TIME, 1, 1)
    arm()
    ss.init_sim()
    for g in (0, 1, 2, 2, 3, 3.5, 5.5, 6, 9, 20):
        out = ss.step(g)
        REC.checkpoint("step%s" % g, {"t": ss.global_time, "out": [canon(x) for x in out],
                                      "next": ss.get_next_event_time()})
    engines.append(ss)
    models += ms
    # R_TIME with a small resolution (sleeps ~0.25 s)
    ss, ms = _instant_build(ExecutionType.R_TIME, 0.01, 0.01)
    arm()
    ss.simulate(0.25, _tm=False)
    REC.checkpoint("rtime_end", {"t": ss.global_time})
    engines.append(ss)
    models += ms
    REC.finals.append(lambda: {"engines": [engine_final(e) for e in engines], "states": final_states(models)})


def sc_snapshot(repo):
    import dill
    from pyjevsim.definition import ExecutionType
    from pyjevsim.system_executor import SysExecutor
    from pyjevsim.snapshot_condition import SnapshotCondition
    from pyjevsim.snapshot_manager import SnapshotManager
    from pyjevsim.restore_handler import RestoreHandler
    from oracle_models import MsgRecv, PEG

    class RecCond(SnapshotCondition):
        @staticmethod
        def create_executor(behavior_executor):
            return RecCond(behavior_executor)

        def __init__(self, behavior_executor):
            super().__init__(behavior_executor)
            self.fired = set()

        def _hook(self, name, args, fire):
            m = self.behavior_executor.get_core_model()
            g = REC._cur()
            REC.see(m)
            g.events.append([m, "cond:" + name, "", "NA", canon(args)])
            if fire and name not in self.fired:
                self.fired.add(name)
                return True
            return False

        def snapshot_time_condition(self, global_time):
            return self._hook("time", [global_time], global_time >= 3)

        def snapshot_pre_condition_ext(self, port, msg, cur_state):
            return self._hook("pre_ext", [port, msg, cur_state], False)

        def snapshot_post_condition_ext(self, port, msg, cur_state):
            return self._hook("post_ext", [port, msg, cur_state], True)

        def snapshot_pre_condition_int(self, cur_state):
            return self._hook("pre_int", [cur_state], False)

        def snapshot_post_condition_int(self, cur_state):
            return self._hook("post_int", [cur_state], False)

        def snapshot_pre_condition_out(self, cur_state):
            return self._hook("pre_out", [cur_state], False)

        def snapshot_post_condition_out(self, *args):
            return self._hook("post_out", list(args), len(REC.lines) > 3)

    sm = SnapshotManager()
    sm.register_snapshot_condition("Gen", RecCond.create_executor)
    sm.register_snapshot_condition("Proc", RecCond.create_executor)
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=sm)
    se.insert_input_port("start")
    gen, proc = PEG("Gen"), MsgRecv("Proc")
    se.register_entity(gen)
    se.register_entity(proc)
    se.coupling_relation(se, "start", gen, "start")
    se.coupling_relation(gen, "process", proc, "recv")
    se.insert_external_event("start", None)
    arm()
    for _ in range(6):
        se.simulate(1)
    REC.checkpoint("exec_types", sorted("%s:%s" % (ex.get_name(), type(ex).__name__)
                                        for ex in se.active_obj_map.values()))
    files = {}
    strict = {}
    snapdir = os.path.join(os.getcwd(), "snapshot")
    for fn in sorted(os.listdir(snapdir)) if os.path.isdir(snapdir) else []:
        with open(os.path.join(snapdir, fn), "rb") as f:
            data = f.read()
        info = dill.loads(data)
        files[fn] = {"type": canon(info["type"]), "name": info["name"], "state": REC.state_of(info["data"])}
        strict["model_snapshot/" + fn] = hashlib.sha256(data).hexdigest()
    REC.checkpoint("model_snapshots", files)
    # whole-simulation snapshot + restore + continue
    simdir = os.path.join(os.getcwd(), "simsnap")
    se.snapshot_simulation(name="proj", directory_path=simdir)
    pdir = os.path.join(simdir, "proj")
    listing = {}
    for fn in sorted(os.listdir(pdir)):
        p = os.path.join(pdir, fn)
        with open(p, "rb") as f:
            data = f.read()
        strict["sim_snapshot/" + fn] = hashlib.sha256(data).hexdigest()
        if fn.endswith(".json"):
            listing[fn] = json.loads(data.decode("utf-8"))
        else:
            info = dill.loads(data)
            listing[fn] = {"type": canon(info["type"]), "name": info["name"], "state": REC.state_of(info["data"])}
    REC.checkpoint("sim_snapshot", listing)
    rh = RestoreHandler(1, ExecutionType.V_TIME, "proj", path=simdir)
    re_ss = rh.get_engine()
    for name, m in rh.model_map.items():
        REC.set_label(m, "restored:" + name)
    arm()
    for _ in range(4):
        re_ss.simulate(1)
    # model_dump / load_snapshot round trip
    snap_ex = [ex for ex in se.active_obj_map.values() if type(ex).__name__ == "SnapshotExecutor"]
    dumps = {}
    for ex in sorted(snap_ex, key=lambda e: e.get_name()):
        b = ex.model_dump()
        strict["model_dump/" + ex.get_name()] = hashlib.sha256(b).hexdigest()
        m2 = sm.load_snapshot(None, b) if sm.restore_handler else dill.loads(b)["data"]
        dumps[ex.get_name()] = REC.state_of(m2)
    REC.checkpoint("model_dump", dumps)
    REC.strict.update(strict)
    REC.finals.append(lambda: {"engine": engine_final(se), "restored": engine_final(re_ss),
                               "states": final_states([gen, proc] + list(rh.model_map.values()))})


def sc_hla_pingpong(repo):
    d = os.path.join(repo, "examples", "hla_pingpong")
    sys.path.insert(1, d)
    import importlib.util
    spec = importlib.util.spec_from_file_location("oracle_pp_run", os.path.join(d, "run_inprocess.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # pyjevsim was already imported from the checkout (asserted in worker())
    arm()
    mod.main(max_volleys=3, rounds=8)
    arm()
    REC.finals.append(lambda: {"engines": [engine_final(e) for e in REC.engines],
                               "exec_types": sorted("%s:%s" % (ex.get_name(), type(ex).__name__)
                                                    for e in REC.engines for ex in e.active_obj_map.values())})


def sc_hla_atsim(trace):
    """AT/SIM standalone + two-federate in-process HLA run.

    trace=False: only the application rows (tick, object, x, y, z) per tick are
    recorded (models are not instrumented) -- these are order-independent by
    design.  trace=True: full model-level trace; its intra-tick cascade depends
    on same-time processing order, so that variant is informational."""
    def run(repo):
        d = os.path.join(repo, "examples", "hla_atsim")
        sys.path.insert(1, d)
        import importlib
        stand = importlib.import_module("run_standalone_headless")
        hla = importlib.import_module("run_hla_inprocess")
        if trace:
            arm()
        rows = {}
        for tag in ("self_propelled", "stationary"):
            path = stand.SCENARIOS[tag]
            r1 = sorted(stand.run(path))
            if trace:
                arm()
            REC.checkpoint("standalone_" + tag, {"n": len(r1), "rows": [list(map(str, r)) for r in r1]})
            r2 = sorted(hla.run(path))
            if trace:
                arm()
            REC.checkpoint("hla_" + tag, {"n": len(r2), "rows": [list(map(str, r)) for r in r2]})
            rows[tag] = [sha(repr(r1)), sha(repr(r2)), r1 == r2]
        REC.finals.append(lambda: {"rows": rows, "n_engines": len(REC.engines)})
    return run


def sc_hla_verify(repo):
    p = subprocess.run([sys.executable, os.path.join("examples", "hla_atsim", "verify_equivalence.py")],
                       cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = p.stdout.replace("\r\n", "\n")
    REC.checkpoint("verify_equivalence", {"returncode": p.returncode, "stdout": out,
                                          "stdout_sha": sha(out)})
    REC.info["stderr_tail"] = p.stderr[-2000:]
    REC.finals.append(lambda: {"returncode": p.returncode, "stdout_sha": sha(out)})


def sc_mwmsim(repo):
    d = os.path.join(repo, "examples", "mwmsim")
    sys.path.insert(1, d)
    import runpy
    from examples.mwmsim import core_component

    class _FakeNow:
        n = [0]

        def timestamp(self):
            return 1.0e9 + _FakeNow.n[0]

    class _FakeDT:
        @staticmethod
        def now():
            _FakeNow.n[0] += 1
            return _FakeNow()

    core_component.datetime = _FakeDT
    old = os.getcwd()
    os.chdir(d)
    argv = sys.argv
    sys.argv = ["exp.py", "433sbh_N100_seed0"]
    try:
        # exp.py builds and runs at import time; arm() must run before simulate,
        # so patch SysExecutor.simulate to arm first.
        from pyjevsim.system_executor import SysExecutor
        orig_sim = SysExecutor.simulate

        def sim(self, *a, **k):
            arm()
            return orig_sim(self, *a, **k)
        SysExecutor.simulate = sim
        runpy.run_path(os.path.join(d, "exp.py"), run_name="__main__")
    finally:
        sys.argv = argv
        os.chdir(old)
    REC.finals.append(lambda: {"engines": [engine_final(e) for e in REC.engines]})


SCENARIOS = [
    # name, function, informational (order-sensitive by construction)
    ("devstone_hi_d6_w8", sc_devstone("hi", 6, 8, 100), False),
    ("devstone_li_d48_w1", sc_devstone("li", 48, 1, 100), False),
    ("devstone_hi_d10_w10_counts", sc_devstone_counts("hi", 10, 10, 100), False),
    ("ring_1000", sc_ring, False),
    ("bank_canon", sc_bank_canon, False),
    ("bank_raw", sc_bank_raw, True),
    ("tests_structural_stm", sc_structural, False),
    ("tests_confluent", sc_confluent, False),
    ("tests_cancel_rescheduling", sc_cancel, False),
    ("tests_v_time_jump", sc_vtime, False),
    ("tests_entity_destruction", sc_destruction, False),
    ("same_instant_external", sc_same_instant, False),
    ("snapshot_restore", sc_snapshot, False),
    ("hla_pingpong_inprocess", sc_hla_pingpong, False),
    ("hla_atsim_rows", sc_hla_atsim(False), False),
    ("hla_atsim_trace", sc_hla_atsim(True), True),
    ("hla_verify_equivalence", sc_hla_verify, False),
    ("mwmsim_433sbh", sc_mwmsim, True),
]
SC_BY_NAME = {n: (f, inf) for n, f, inf in SCENARIOS}
# Left out by --no-slow (about 15 s of one core on the machine that froze
# the golden; every other scenario takes under 7 s).
SLOW = {"mwmsim_433sbh"}


# --------------------------------------------------------------------------
# worker
# --------------------------------------------------------------------------

def worker(name, repo, part, salt, raw_order=False):
    repo = os.path.abspath(repo)
    # make sure THIS checkout is what gets imported
    sys.path[:] = [repo] + [p for p in sys.path if os.path.abspath(p or ".") not in (HERE, repo)]
    for k in list(sys.modules):
        if k == "pyjevsim" or k.startswith("pyjevsim."):
            del sys.modules[k]
    import pyjevsim
    pj = os.path.abspath(pyjevsim.__file__)
    assert pj.startswith(repo + os.sep), "imported %s, expected under %s" % (pj, repo)
    # oracle_models and bank_driver come from this directory, after the
    # checkout so that they can never shadow it.
    sys.path.insert(1, HERE)
    # snapshot files are written relative to the cwd
    work = tempfile.mkdtemp(prefix="oracle_")
    os.chdir(work)
    fn, informational = SC_BY_NAME[name]
    if salt is None and informational:
        # order-sensitive scenario: pin the same-time order (executor hash =
        # f(salt, obj_id)) so that base runs are reproducible across processes
        salt = FIXED_SALT
    install_engine_hooks(salt)
    REC._real_stdout = sys.stdout
    cap = _Capture(REC)
    t0 = time.perf_counter()
    err = None
    sys.stdout = cap
    try:
        fn(repo)
    except BaseException as e:   # noqa: BLE001 - record any failure as data
        err = "%s: %s\n%s" % (type(e).__name__, e, traceback.format_exc())
    finally:
        sys.stdout = REC._real_stdout
    while REC.stack:
        REC.close_group()
    REC._close_outside()
    lines = REC.canonical_lines()
    finals = []
    for cb in REC.finals:
        try:
            finals.append(cb())
        except Exception as e:  # noqa: BLE001
            finals.append({"final_error": "%s: %s" % (type(e).__name__, e)})
    final_c = json.loads(json.dumps(finals, default=canon))
    res = {
        "name": name, "error": err, "grouping": REC.grouping, "informational": informational,
        "lines": lines, "final": final_c, "strict": REC.strict,
        "info": json.loads(json.dumps(REC.info, default=str)),
        "elapsed_s": round(time.perf_counter() - t0, 3), "pyjevsim": pj, "salt": salt,
    }
    if raw_order:
        res["raw_lines"] = REC.canonical_lines(raw_order=True)
    with open(part, "w", encoding="utf-8") as f:
        json.dump(res, f)
    os.chdir(os.path.dirname(os.path.abspath(part)))
    shutil.rmtree(work, ignore_errors=True)
    return 0


# --------------------------------------------------------------------------
# driver / digest
# --------------------------------------------------------------------------

def git_info(repo):
    def g(*a):
        try:
            return subprocess.run(["git", "-C", repo] + list(a), capture_output=True, text=True).stdout.strip()
        except Exception:
            return ""
    if not os.path.exists(os.path.join(repo, ".git")):
        # a `git archive` export: do not report an enclosing repository
        return {"head": "", "branch": "", "dirty_files": []}
    return {"head": g("rev-parse", "HEAD"), "branch": g("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty_files": g("status", "--porcelain", "--", "pyjevsim").splitlines()}


def scenario_hash(lines, final, error):
    """sha256 over the trace lines, the final summary and the error's first line."""
    final_s = json.dumps(final, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256()
    for ln in lines:
        h.update(ln.encode("utf-8"))
        h.update(b"\n")
    h.update(b"FINAL\n")
    h.update(final_s.encode("utf-8"))
    if error:
        h.update(b"ERROR\n")
        h.update(error.split("\n")[0].encode("utf-8"))
    return h.hexdigest(), final_s


def run_scenarios(repo, names, jobs, salt=None, raw_order=False, hashseed="0"):
    """Run each scenario in a fresh subprocess; return ({name: result}, wall_s)."""
    repo = os.path.abspath(repo)
    tmp = tempfile.mkdtemp(prefix="oracle_parts_")
    procs = {}
    pending = list(names)
    results = {}
    t0 = time.perf_counter()
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONHASHSEED=hashseed)
    try:
        while pending or procs:
            while pending and len(procs) < jobs:
                n = pending.pop(0)
                part = os.path.join(tmp, n + ".json")
                cmd = [sys.executable, os.path.abspath(__file__), "--worker", n, "--repo", repo, "--part", part]
                if salt is not None:
                    cmd += ["--salt", str(salt)]
                if raw_order:
                    cmd.append("--raw-order")
                lf = open(os.path.join(tmp, n + ".log"), "w", encoding="utf-8")
                procs[n] = (subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, env=env, cwd=tmp), part,
                            lf, time.perf_counter())
            time.sleep(0.05)
            for n in list(procs):
                p, part, lf, ts = procs[n]
                if p.poll() is None:
                    if time.perf_counter() - ts > 1800:
                        p.kill()
                    continue
                lf.close()
                del procs[n]
                if os.path.exists(part):
                    with open(part, encoding="utf-8") as f:
                        results[n] = json.load(f)
                else:
                    with open(os.path.join(tmp, n + ".log"), encoding="utf-8", errors="replace") as f:
                        results[n] = {"name": n,
                                      "error": "worker crashed rc=%s\n%s" % (p.returncode, f.read()[-4000:]),
                                      "lines": [], "final": None, "strict": {}, "info": {},
                                      "informational": SC_BY_NAME[n][1], "grouping": "?"}
    finally:
        for p, _, lf, _ in procs.values():
            p.kill()
            lf.close()
        shutil.rmtree(tmp, ignore_errors=True)
    return results, round(time.perf_counter() - t0, 1)


def run_all(repo, out, names, jobs, salt, hash_only=False, skipped=(), label=None):
    """Run ``names`` and write a full digest, or only the hashes if ``hash_only``."""
    repo = os.path.abspath(repo)
    out = os.path.abspath(out)
    if label is None:
        label = os.path.basename(repo)
    results, wall = run_scenarios(repo, names, jobs, salt)
    digest = {"oracle_version": ORACLE_VERSION, "label": label, "git": git_info(repo), "salt": salt,
              "python": platform.python_version(), "implementation": platform.python_implementation(),
              "platform": "%s-%s" % (platform.system(), platform.machine()),
              "created": time.strftime("%Y-%m-%d %H:%M:%S"), "skipped": sorted(skipped), "scenarios": {}}
    if hash_only:
        digest = dict({"format": HASHES_FORMAT}, **digest)
    else:
        digest["repo"] = repo
        digest["wall_s"] = wall
        side = out[:-5] + ".traces" if out.endswith(".json") else out + ".traces"
        os.makedirs(side, exist_ok=True)
    for n in names:
        r = results[n]
        lines = r.get("lines") or []
        h, final_s = scenario_hash(lines, r.get("final"), r.get("error"))
        n_events = 0
        for ln in lines:
            o = json.loads(ln)
            if o[0] != "CP":
                n_events += len(o[3])
        strict = r.get("strict") or {}
        if hash_only:
            digest["scenarios"][n] = {
                "sha256": h, "final_sha256": sha(final_s), "informational": r.get("informational"),
                "grouping": r.get("grouping"), "n_groups": len(lines), "n_events": n_events,
                "error": (r.get("error") or "").split("\n")[0] or None,
                "strict_sha256": sha(json.dumps(strict, sort_keys=True)) if strict else None,
            }
            continue
        trace_path = os.path.join(side, n + ".jsonl.gz")
        with gzip.open(trace_path, "wt", encoding="utf-8") as f:
            for ln in lines:
                f.write(ln + "\n")
        idx = []
        for ln in lines:
            head = json.loads(ln)
            idx.append([head[0], head[1], hashlib.sha256(ln.encode("utf-8")).hexdigest()[:16]])
        entry = {
            "sha256": h, "informational": r.get("informational"), "grouping": r.get("grouping"),
            "error": r.get("error"), "n_groups": len(lines), "n_events": n_events,
            "final": r.get("final"), "final_sha256": sha(final_s), "strict": strict,
            "info": r.get("info"), "elapsed_s": r.get("elapsed_s"), "pyjevsim": r.get("pyjevsim"),
            "index": idx, "trace_file": trace_path,
        }
        if len(lines) <= INLINE_LIMIT:
            entry["trace"] = lines
        digest["scenarios"][n] = entry
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(digest, f, indent=1, ensure_ascii=False)
        f.write("\n")
    bad = 0
    for n in names:
        e = digest["scenarios"][n]
        status = "ERROR" if e["error"] else "ok"
        if e["error"]:
            bad += 1
        print("%-28s %-5s groups=%-6d events=%-7d %6.1fs sha=%s%s" % (
            n, status, e["n_groups"], e["n_events"], results[n].get("elapsed_s") or 0, e["sha256"][:16],
            "  (informational)" if e["informational"] else ""))
        if e["error"]:
            print("    " + e["error"].strip().split("\n")[0])
    if skipped:
        print("not run: " + ", ".join(skipped))
    print("wrote %s (%.1f s)%s" % (out, wall, "" if hash_only else " (traces in %s)" % side))
    return 1 if bad else 0


def _load_trace(entry):
    if entry.get("trace") is not None:
        return entry["trace"]
    p = entry.get("trace_file")
    if p and os.path.exists(p):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return [ln.rstrip("\n") for ln in f]
    return None


def _diff_group(la, lb, max_lines):
    a, b = json.loads(la), json.loads(lb)
    out = []
    if a[0] == "CP" or b[0] == "CP":
        out.append("  base: %s" % la[:600])
        out.append("  cand: %s" % lb[:600])
        return out
    if a[:3] != b[:3]:
        out.append("  header base=%s cand=%s" % (a[:3], b[:3]))
    names = ["events", "states", "stdout", "engine_emits"]
    for k, nm in enumerate(names, start=3):
        sa, sb = a[k], b[k]
        if sa == sb:
            continue
        ma, mb = {}, {}
        for x in sa:
            ma[x] = ma.get(x, 0) + 1
        for x in sb:
            mb[x] = mb.get(x, 0) + 1
        only_a = sorted(x for x in ma if ma[x] > mb.get(x, 0))
        only_b = sorted(x for x in mb if mb[x] > ma.get(x, 0))
        out.append("  %s: %d only in base, %d only in candidate" % (nm, len(only_a), len(only_b)))
        for x in only_a[:max_lines]:
            out.append("    - " + x[:400])
        for x in only_b[:max_lines]:
            out.append("    + " + x[:400])
    return out


def _diff_obj(a, b, path="final", out=None, limit=20):
    if out is None:
        out = []
    if len(out) >= limit:
        return out
    if type(a) is not type(b):
        out.append("  %s: base=%s cand=%s" % (path, json.dumps(a)[:300], json.dumps(b)[:300]))
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                _diff_obj(a.get(k), b.get(k), "%s.%s" % (path, k), out, limit)
    elif isinstance(a, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                _diff_obj(x, y, "%s[%d]" % (path, i), out, limit)
    elif a != b:
        out.append("  %s: base=%s cand=%s" % (path, json.dumps(a)[:300], json.dumps(b)[:300]))
    return out


def _describe(d):
    src = d.get("label") or d.get("repo") or "?"
    head = (d.get("git") or {}).get("head", "")[:10]
    return "%s %s (Python %s, %s)" % (src, head, d.get("python", "?").split()[0], d.get("platform", "?"))


def _strict_of(e):
    if "strict_sha256" in e:
        return e["strict_sha256"]
    s = e.get("strict") or {}
    return sha(json.dumps(s, sort_keys=True)) if s else None


def compare(pa, pb, max_lines):
    """Compare two digests or hash files; return 0 when every verdict scenario matches."""
    with open(pa, encoding="utf-8") as f:
        A = json.load(f)
    with open(pb, encoding="utf-8") as f:
        B = json.load(f)
    fails = 0
    warns = 0
    print("base: " + _describe(A))
    print("cand: " + _describe(B))
    if A.get("platform") and B.get("platform") and (A["python"], A["platform"]) != (B["python"], B["platform"]):
        print("NOTE      base and candidate ran on different Python versions or platforms")
    if A.get("oracle_version") != B.get("oracle_version"):
        print("NOTE      oracle versions differ (%s vs %s): hashes are not comparable"
              % (A.get("oracle_version"), B.get("oracle_version")))
    skipped = set(A.get("skipped") or ()) | set(B.get("skipped") or ())
    names = list(A["scenarios"]) + [n for n in B["scenarios"] if n not in A["scenarios"]]
    for n in names:
        ea, eb = A["scenarios"].get(n), B["scenarios"].get(n)
        if ea is None or eb is None:
            if n in skipped:
                print("SKIPPED   %s" % n)
            else:
                print("MISSING   %s (only in %s)" % (n, "base" if eb is None else "candidate"))
                fails += 1
            continue
        informational = bool(ea.get("informational"))
        tag = "INFO-" if informational else ""
        if ea.get("grouping") != eb.get("grouping"):
            print("WARN      %s grouping base=%s cand=%s" % (n, ea.get("grouping"), eb.get("grouping")))
            warns += 1
        if ea.get("error") or eb.get("error"):
            if (ea.get("error") or "").split("\n")[0] != (eb.get("error") or "").split("\n")[0]:
                print("%sERROR %s\n  base: %s\n  cand: %s" % (tag, n, (ea.get("error") or "-").split("\n")[0],
                                                           (eb.get("error") or "-").split("\n")[0]))
                if not informational:
                    fails += 1
                continue
        if ea["sha256"] == eb["sha256"]:
            print("%sMATCH %-28s groups=%d events=%d" % (tag, n, ea["n_groups"], ea["n_events"]))
        else:
            if not informational:
                fails += 1
            print("%sDIFF  %-28s groups %d vs %d, events %d vs %d" % (
                tag, n, ea["n_groups"], eb["n_groups"], ea["n_events"], eb["n_events"]))
            ia, ib = ea.get("index"), eb.get("index")
            if ia is None or ib is None:
                print("  %s; run both checkouts with --out (full digest) to see the first differing group"
                      % ("final summary differs too" if ea.get("final_sha256") != eb.get("final_sha256")
                         else "final summary matches, trace differs"))
                continue
            first = None
            for i in range(min(len(ia), len(ib))):
                if ia[i][2] != ib[i][2]:
                    first = i
                    break
            if first is None and len(ia) != len(ib):
                first = min(len(ia), len(ib))
            if first is not None:
                ra = ia[first] if first < len(ia) else None
                rb = ib[first] if first < len(ib) else None
                print("  first differing group #%d: base=%s cand=%s" % (first, ra and ra[:2], rb and rb[:2]))
                ta, tb = _load_trace(ea), _load_trace(eb)
                if ta is not None and tb is not None and first < len(ta) and first < len(tb):
                    for ln in _diff_group(ta[first], tb[first], max_lines):
                        print(ln)
                elif ta is not None and first < len(ta):
                    print("  base only: " + ta[first][:600])
                elif tb is not None and first < len(tb):
                    print("  cand only: " + tb[first][:600])
            else:
                print("  trace identical; final summary differs:")
                for ln in _diff_obj(ea.get("final"), eb.get("final")):
                    print(ln)
        sa, sb = _strict_of(ea), _strict_of(eb)
        if sa != sb:
            warns += 1
            ks = []
            if "strict" in ea and "strict" in eb:   # hash files carry only a hash
                ka, kb = set(ea["strict"].items()), set(eb["strict"].items())
                ks = sorted({k for k, _ in ka ^ kb})
            print("WARN      %s strict (raw dill bytes) differ%s" % (n, (": " + ", ".join(ks[:6])) if ks else ""))
    print("RESULT: %s (%d failing, %d warnings)" % ("PASS" if fails == 0 else "FAIL", fails, warns))
    return 0 if fails == 0 else 1


def perturb_check(repo, outdir, salts, names, jobs):
    os.makedirs(outdir, exist_ok=True)
    digests = {}
    for s in [None] + salts:
        p = os.path.join(outdir, "salt_%s.json" % ("none" if s is None else s))
        run_all(repo, p, names, jobs, s)
        with open(p, encoding="utf-8") as f:
            digests[s] = json.load(f)
    print("\norder-sensitivity (digest per salt):")
    for n in names:
        shas = {str(s): digests[s]["scenarios"][n]["sha256"][:12] for s in digests}
        stable = len(set(shas.values())) == 1
        print("  %-28s %s  %s" % (n, "STABLE   " if stable else "SENSITIVE", " ".join(
            "%s:%s" % kv for kv in shas.items())))
    return 0


def select(scenarios, skip, no_slow):
    """Scenario names to run, and the remaining ones (reported as skipped)."""
    wanted = [n for n in scenarios.split(",") if n] or [n for n, _, _ in SCENARIOS]
    drop = {n for n in skip.split(",") if n}
    if no_slow:
        drop |= SLOW
    for n in wanted + sorted(drop):
        if n not in SC_BY_NAME:
            raise ValueError("unknown scenario %s" % n)
    run = [n for n in wanted if n not in drop]
    return run, [n for n, _, _ in SCENARIOS if n not in run]


def main(argv=None):
    ap = argparse.ArgumentParser(description="pyjevsim order-insensitive trace oracle")
    ap.add_argument("--repo", default=DEFAULT_REPO,
                    help="checkout or export to run (default: the repository containing this tool)")
    ap.add_argument("--out", help="write a full digest (or, with --hash-only, a hash file) here")
    ap.add_argument("--hash-only", action="store_true", help="write per-scenario hashes only, no traces")
    ap.add_argument("--golden", metavar="JSON", nargs="?", const=GOLDEN,
                    help="compare a hash-only run with this golden file (or write it with --write-golden);"
                         " without a value, the current golden %s" % os.path.relpath(GOLDEN, DEFAULT_REPO))
    ap.add_argument("--write-golden", action="store_true")
    ap.add_argument("--label", help="free-text name of the checkout, recorded in the output")
    ap.add_argument("--scenarios", default="", help="comma-separated subset (default: all)")
    ap.add_argument("--skip", default="", help="comma-separated scenarios to leave out")
    ap.add_argument("--no-slow", action="store_true", help="leave out " + ", ".join(sorted(SLOW)))
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    ap.add_argument("--salt", type=int, default=None,
                    help="perturb executor hashing (set-iteration order) with this salt")
    ap.add_argument("--compare", nargs=2, metavar=("BASE", "CAND"))
    ap.add_argument("--max-lines", type=int, default=25)
    ap.add_argument("--perturb-check", metavar="DIR")
    ap.add_argument("--salts", default="1,2,3")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--worker", help=argparse.SUPPRESS)
    ap.add_argument("--part", help=argparse.SUPPRESS)
    ap.add_argument("--raw-order", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.list:
        for n, _, inf in SCENARIOS:
            print(" ".join([n] + ["(informational)"] * inf + ["(slow)"] * (n in SLOW)))
        return 0
    if a.compare:
        return compare(a.compare[0], a.compare[1], a.max_lines)
    if a.worker:
        return worker(a.worker, a.repo, a.part, a.salt, a.raw_order)
    try:
        names, skipped = select(a.scenarios, a.skip, a.no_slow)
    except ValueError as e:
        ap.error(str(e))
    if a.perturb_check:
        return perturb_check(a.repo, a.perturb_check, [int(x) for x in a.salts.split(",") if x], names, a.jobs)
    if a.golden and a.write_golden:
        return run_all(a.repo, a.golden, names, a.jobs, a.salt, True, skipped, a.label)
    if a.golden:
        out = a.out
        tmp = None
        if not out:
            tmp = tempfile.mkdtemp(prefix="oracle_golden_")
            out = os.path.join(tmp, "candidate.json")
        try:
            rc = run_all(a.repo, out, names, a.jobs, a.salt, True, skipped, a.label)
            print()
            return compare(a.golden, out, a.max_lines) or rc
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)
    if not a.out:
        ap.error("--out, --golden, --compare, --perturb-check or --list is required")
    return run_all(a.repo, a.out, names, a.jobs, a.salt, a.hash_only, skipped, a.label)


if __name__ == "__main__":
    raise SystemExit(main())
