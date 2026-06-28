# pyjevsim 2.1: HLA federate support for distributed and interoperable DEVS simulation

SoftwareX *Software Update* — draft manuscript material.

- **Software:** pyjevsim
- **Version:** v2.1.2
- **Author:** Changbeom Choi (Hanbat National University), ORCID 0000-0002-4826-7949
- **Repository:** https://github.com/eventsim/pyjevsim
- **Archive (DOI):** https://doi.org/10.5281/zenodo.21002028 (concept) · v2.1.2: 10.5281/zenodo.21002029
- **License:** MIT

> Bracketed `[ ]` items are placeholders for the author to confirm/insert
> (e.g. citation of the original pyjevsim publication, application domain).

---

## Abstract

pyjevsim is a Python DEVS (Discrete Event System Specification) modelling
and simulation framework with state journaling and virtual- and real-time
execution. **This update makes pyjevsim interoperable and distributable:
DEVS models run, unchanged, as High Level Architecture (HLA, IEEE
1516-2010) federates.** Its central contribution is an *RTI-agnostic
federate layer* — HLA bindings declared on existing model ports are bridged
to an RTI through a transport that is selected at run time, so the same
model executes standalone, on an in-process multi-federate bus, or against
a live RTI without any modelling-code change. A new RTI backend requires
implementing only two methods; direction enforcement, FOM
(de)serialization, callback dispatch, and the join/resign lifecycle are
inherited. We provide and validate a backend for the commercial **Pitch
pRTI**, demonstrating federation join/resign, time-stamp-ordered
interaction exchange, and object-attribute synchronization under HLA time
management — including a **fully distributed configuration with one
federate per operating-system process**. A unifying two-phase simulation
tick further guarantees correct Parallel-DEVS confluent and
time-stamp-ordered semantics across all execution modes. The update
transforms an isolated DEVS simulator into an interoperable, distributable
one while preserving its modelling API and existing features.

---

## Statement of contribution

Prior to this update pyjevsim was a self-contained simulator: models could
be coupled within one engine but could not interoperate with other
simulators or run distributed. The update adds, as its primary
contribution, the ability to run **unmodified DEVS models as HLA (IEEE
1516-2010) federates**, with four individually reusable advances:

- **Distributed & interoperable DEVS via HLA.** DEVS models join standard
  HLA federations, gaining distributed execution and interoperability with
  heterogeneous simulators — the lingua franca of [defence/aerospace/
  large-scale engineering] M&S.
- **RTI-agnostic, low-effort backend interface.** A template-method
  `RTIConnector` separates *what to exchange* (port bindings) from *how to
  transport it* (the RTI). Supporting a new RTI (CERTI, Portico, OpenRTI,
  MÄK, …) is ~two methods; the FOM codec is pluggable and orthogonal.
- **Zero modelling-code change (separation of concerns).** The same
  `BehaviorModel` runs standalone, on an in-process bus, or on a live RTI;
  only the factory and transport differ. Existing features (journaling,
  real-time mode) are preserved.
- **Validated, time-managed distribution.** A Pitch pRTI backend is
  validated live — join/resign, time-stamp-ordered interactions,
  object-attribute reflection, time regulation/constraint — in a genuinely
  distributed, one-federate-per-process configuration over the network.
- **Cross-mode correctness.** A single two-phase tick unifies
  V_TIME/R_TIME/HLA execution, guaranteeing correct Parallel-DEVS
  confluent (δ_con) and time-stamp-ordered delivery in every mode.

**Why it matters.** The contribution is not "an HLA adapter" but a clean
architectural extension: interoperability is added behind a thin
binding/transport seam, so the modelling abstraction stays pure DEVS,
models remain portable across execution backends, and the framework
becomes extensible to arbitrary RTIs while being proven against a
commercial one.

---

## 1. Motivation and significance

pyjevsim [cite original publication] is a Python DEVS modelling and
simulation framework offering atomic/coupled models, a priority-queue
scheduler, virtual- and real-time execution, and snapshot/restore
journaling. It executed only as a self-contained simulator — models could
be coupled within one engine, but the tool could not interoperate with
other simulators or run in a distributed setting. This update enables a
pyjevsim model to run, unchanged, as a federate in an HLA (IEEE 1516-2010)
federation, the established standard for distributed and interoperable
simulation.

## 2. Software description

### 2.1 RTI-agnostic federate interface

A new subsystem (`pyjevsim.hla`) bridges DEVS ports to HLA without changing
the model layer. Users declare *bindings* (`HLAInteraction`,
`HLAAttribute`) on existing ports; an `HLAExecutorFactory` routes bound
ports to a transport; and a `Federate` helper drives the lifecycle
(join/publish/subscribe/resign) and the time-advance loop. Transports
implement an `RTIConnector` base that provides direction enforcement, a
pluggable FOM `Codec`, single-callback dispatch, the join/resign state
machine, and idempotent shutdown — so a concrete backend needs only two
RTI-specific methods (`_do_send`, `_do_request_time_advance`). A registry
(`create_rti`) selects a backend by name; the same model runs standalone,
on an in-process multi-federate bus, or on a live RTI.

| Component | Role |
|-----------|------|
| `RTIConnector` | Base class for RTI backends (implement two methods) |
| `RTICapabilities` / `Codec` | Feature negotiation / pluggable FOM (de)serialization |
| `HLAInteraction`, `HLAAttribute` | Port-to-FOM bindings |
| `HLAExecutorFactory`, `Federate` | Wire models to a transport; drive time advance |
| Backends | `loopback`, `inprocess` (no Java), `pitch` (Pitch pRTI via JPype) |
| `create_rti` / `register_rti` | Select / add a backend by name |

### 2.2 Pitch pRTI backend

A backend for Pitch pRTI (IEEE 1516-2010), realized as an in-process JVM
bridge (JPype), implements connect (with a configurable CRC endpoint),
federation create/join/resign, interaction and object-class
publish/subscribe, time regulation/constraint with Time-Advance-Request/
Grant, time-stamp-ordered interaction send/receive, object
registration/update/reflection, and federation synchronization points.
FOM datatype encoding uses the RTI's standard encoder factory.

### 2.3 Unified, confluent-correct tick

The standalone and HLA-stepped execution paths share one Parallel-DEVS
two-phase tick (`SysExecutor._run_instant`), guaranteeing that
RTI-delivered events coinciding with a model's internal event invoke the
correct confluent transition (δ_con) and preserving IEEE 1516
time-stamp-ordered semantics across all execution modes.

## 3. Illustrative example

A two-federate "ping-pong" example ships with the release. Federates *ping*
and *pong* join one federation, rally a token via HLA interactions, and
synchronize a paddle state via an HLA object attribute under RTI-granted
logical time. It runs from identical model code as (i) an offline
in-process bus and (ii) a live federation, **including a fully distributed
configuration in which each federate runs as a separate operating-system
process** (independent JVM and RTI ambassador), coordinated solely by the
RTI through a federation synchronization point. Validated against Pitch
pRTI [Free 5.5.2], both federates exchanged the expected interaction
sequence and object-attribute reflections and resigned cleanly. The test
suite reports 110 passed, 2 skipped (Pitch live cases skip without a JVM).

## 4. Impact

By turning DEVS models into HLA federates, the update lets pyjevsim
participate in distributed simulations and interoperate with heterogeneous
simulators within a federation — capabilities central to [your domain] M&S,
where HLA is the interoperability standard. Because interoperability sits
behind a thin binding/transport layer, existing models and the framework's
snapshot and real-time features are reused without modification, and
supporting additional RTIs is a localized extension.

## 5. Limitations and future work

The release implements and validates one RTI backend (Pitch pRTI);
additional backends (CERTI, Portico, OpenRTI, MÄK) and large-scale,
multi-host scalability studies are future work. Multi-host deployment is
supported via a configurable CRC endpoint and verified over the network;
a multi-machine benchmark is planned.

---

## Code metadata

| Nr | Code metadata description | Value |
|----|---------------------------|-------|
| C1 | Current code version | v2.1.2 |
| C2 | Permanent link to code/repository used for this version | https://github.com/eventsim/pyjevsim/releases/tag/v2.1.2 |
| C3 | Permanent link to Reproducible Capsule (archive) | https://doi.org/10.5281/zenodo.21002028 (concept; v2.1.2: 10.5281/zenodo.21002029) |
| C4 | Legal Code License | MIT |
| C5 | Code versioning system used | git |
| C6 | Software code languages, tools, and services used | Python; (HLA backend) Java, JPype, IEEE 1516-2010 RTI (Pitch pRTI) |
| C7 | Compilation requirements, operating environments & dependencies | Python ≥ 3.10; `dill`. Optional `pitch` backend: `jpype1` + Java ≥ 9 + an IEEE 1516-2010 RTI (e.g. Pitch pRTI) with a running CRC. `pytest` for tests. OS-independent. |
| C8 | Link to developer documentation/manual | https://pyjevsim.readthedocs.io/ ; HLA backend guide: `docs/hla/rti_interface.md` |
| C9 | Support email for questions | me@cbchoi.info |

## How to cite

> Choi, C. *pyjevsim: a Python DEVS modelling and simulation framework with
> HLA federate support* (v2.1.2). Zenodo.
> https://doi.org/10.5281/zenodo.21002028

---

## Scope / accuracy notes (for review; remove before submission)

- "Validated against Pitch pRTI" — one RTI is implemented and measured; the
  interface is designed for, but does not yet implement, other RTIs.
- "Fully distributed, one-federate-per-process" — multi-process is measured
  live; multi-host is enabled via the configurable CRC endpoint and the
  network path is verified on a LAN. Add a two-machine run to assert
  "across hosts" unconditionally.
