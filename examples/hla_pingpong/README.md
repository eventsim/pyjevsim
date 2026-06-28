# HLA Ping-Pong example

Two federates, **ping** and **pong**, rally a ball across an HLA federation:

- `ping` serves at t=0 and returns each `Pong` it receives, up to `max_volleys`.
- `pong` returns every `Ping`.
- `ping` also publishes an object attribute (`PingPaddle.hits`) that `pong`
  reflects — demonstrating **object synchronization** alongside the
  **interaction** rally.

The DEVS models ([`pingpong_models.py`](pingpong_models.py)) are
**RTI-agnostic**: the exact same classes run on the in-process bus and on real
Pitch pRTI. Only the transport (chosen via `create_rti(...)`) changes.

## Files

| File | What |
|------|------|
| `pingpong_models.py` | `Ping` / `Pong` models + HLA bindings + Pitch FOM map |
| `fom/PingPong.xml` | IEEE 1516-2010 FOM (interactions `Ping`/`Pong`, object `PingPaddle`) |
| `run_inprocess.py` | Offline demo — two federates over `InProcessRTI` (no Java) |
| `run_pitch.py` | Live demo — two federates (two threads) in one process over Pitch pRTI |
| `run_pitch_federate.py` | **One federate per OS process** (`ping`/`pong` arg) — true distributed run |
| `run_pitch_multiprocess.py` | Launcher that spawns both federate processes and streams their output |

## Run offline (no Java / RTI needed)

```bash
python examples/hla_pingpong/run_inprocess.py
```

Expected:

```
federation members after join: 2
pong received pings: [0, 1, 2, 3]
ping received pongs: [0, 1, 2, 3]
pong reflected hits (object sync): [0, 1, 2, 3]
federation members after resign: 0
```

## Run against Pitch pRTI

> Verified live against **Pitch pRTI Free 5.5.2** with **Temurin 11** —
> produces the same rally as the offline demo:
> `pong received pings: [0, 1, 2, 3]`, `ping received pongs: [0, 1, 2, 3]`,
> `pong reflected hits: [0, 1, 2, 3]`.

Prerequisites:

1. `pip install jpype1` — must match your Python **and** Java. JPype ≥ 1.6
   requires **Java ≥ 9**; for Java 8 pin `jpype1<=1.5`.
2. Pitch pRTI installed and a **CRC running**.
3. `PRTI_HOME` set (default `C:\Program Files\prti1516e`). Optionally
   `PYJEVSIM_JVM` to point at a specific `jvm.dll` (use a Java ≥ 9 runtime).

Single process (two federates as two threads):

```bash
python examples/hla_pingpong/run_pitch.py
```

### Distributed: one federate per process

Each federate runs in its own OS process (own JVM and LRC), joined to the
same federation through the CRC — a genuine distributed run. The federates
may live on different hosts; point each at the CRC (e.g. `PYJEVSIM_CRC` /
your pRTI client settings).

One command (spawns both, starts `pong` then `ping`):

```bash
python examples/hla_pingpong/run_pitch_multiprocess.py
```

Or two terminals (start `pong` first so the start sync-point is announced
to both federates):

```bash
# terminal 1
python examples/hla_pingpong/run_pitch_federate.py pong
# terminal 2
python examples/hla_pingpong/run_pitch_federate.py ping
```

> Verified live (two processes, Pitch pRTI Free 5.5.2 + Temurin 11):
> `pong received pings: [0, 1, 2, 3]`, `ping received pongs: [0, 1, 2, 3]`,
> `pong reflected hits: [0, 1, 2, 3]`, both `resigned`, exit 0. The two
> federates synchronize on a `ready` federation synchronization point
> before exchanging any event.

Switching backend is the only change — the models and wiring are identical:

```python
# offline
tx = create_rti("inprocess", federation=shared_bus)
# pitch
tx = create_rti("pitch", federation="PingPong", federate="ping",
                fom="fom/PingPong.xml", fom_map=PINGPONG_FOM_MAP,
                classpath=[r"...\\prti1516e.jar"], lookahead=1.0)
```

## Tests

- `tests/hla/test_pingpong.py` — always runs; verifies join/resign,
  interaction exchange (both directions) and object sync deterministically
  over the in-process bus.
- `tests/hla/test_pitch_backend.py` — guarded; runs the encoder round-trip
  when JPype + Java ≥ 9 + `prti1516e.jar` are present, and the full live
  federation when `PYJEVSIM_PITCH_LIVE=1` with a running CRC. Skips otherwise.

## How it maps to HLA

| pyjevsim | HLA / pRTI |
|----------|-----------|
| `HLAInteraction("PingPong.Ping", "out")` on a port | `publishInteractionClass` + `sendInteraction` |
| `HLAInteraction("PingPong.Pong", "in")` on a port | `subscribeInteractionClass` + `receiveInteraction` |
| `HLAAttribute("PingPaddle.hits", "out", object_class=...)` | `registerObjectInstance` + `updateAttributeValues` |
| `HLAAttribute("PingPaddle.hits", "in")` | `subscribeObjectClassAttributes` + `reflectAttributeValues` |
| `Federate.run_until` / `SysExecutor.step` | `timeAdvanceRequest` ↔ `timeAdvanceGrant` |
