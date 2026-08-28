# HLA Ping-Pong example

Two federates, **ping** and **pong**, rally a ball across an HLA federation:

- `ping` serves at t=0 and returns each `Pong` it receives, up to `max_volleys`.
- `pong` returns every `Ping`.
- `ping` also publishes an object attribute (`PingPaddle.hits`) that `pong`
  reflects — demonstrating **object synchronization** alongside the
  **interaction** rally.

The DEVS model classes in [`pingpong_models.py`](pingpong_models.py) are used
with the in-process bus, Pitch pRTI, and Portico. Backend selection and runtime
configuration are handled outside the model classes.

## Files

| File | What |
|------|------|
| `pingpong_models.py` | `Ping` / `Pong` models + HLA bindings + Pitch FOM map |
| `fom/PingPong.xml` | IEEE 1516-2010 FOM (interactions `Ping`/`Pong`, object `PingPaddle`) |
| `run_inprocess.py` | Offline demo — two federates over `InProcessRTI` (no Java) |
| `run_pitch.py` | Live demo — two federates (two threads) in one process over Pitch pRTI (`PYJEVSIM_RTI` picks the backend) |
| `run_portico.py` | The same demo over the open-source **Portico** RTI (no CRC needed) |
| `run_pitch_federate.py` | **One federate per OS process** (`ping`/`pong` arg) |
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
   requires **Java ≥ 11**; for Java 8 pin `jpype1<=1.5`.
2. Pitch pRTI installed and a **CRC running**.
3. `PRTI_HOME` set (default `C:\Program Files\prti1516e`). Optionally
   `PYJEVSIM_JVM` to point at a specific `jvm.dll` (use a Java ≥ 11 runtime).

Single process (two federates as two threads):

```bash
python examples/hla_pingpong/run_pitch.py
```

### One federate per process

Each federate runs in its own OS process (own JVM and LRC) and joins the same
federation through the CRC. The recorded validation for this launcher is
limited to processes on one host.

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

## Run against Portico

Portico 2.1.4 uses the same model and bindings without a CRC. Install the
`hla-java` extra, use Java 11 or later, and point the launcher at
`portico.jar`:

```powershell
python -m pip install "pyjevsim[hla-java]"
$env:RTI_HOME = "C:\path\to\portico-2.1.4"
$env:PYJEVSIM_JAR = "$env:RTI_HOME\lib\portico.jar"
# Optional when Java discovery does not select the intended runtime:
$env:PYJEVSIM_JVM = "C:\path\to\jvm.dll"
python examples/hla_pingpong/run_portico.py
```

The launcher selects the repository's same-JVM RID when `RTI_RID_FILE` is
unset. Set `RTI_RID_FILE` to a suitable Portico configuration for another
process topology. The recorded validation covers only the same-process setup.

## Remote-host configuration for Pitch (not validated here)

To configure federates on separate hosts, run the CRC on one machine and point
each federate at it with
`PYJEVSIM_CRC=<crc-host>:8989` (the LRC then connects to the CRC over the
network instead of localhost):

```powershell
# host A (also runs the CRC) — responder
$env:PYJEVSIM_CRC = "192.168.1.10:8989"
python examples/hla_pingpong/run_pitch_federate.py pong
# host B — server
$env:PYJEVSIM_CRC = "192.168.1.10:8989"
python examples/hla_pingpong/run_pitch_federate.py ping
```

This is a configuration example, not evidence of a run on two physical hosts.
Firewall, routing, RTI licensing, and host-specific settings remain the
operator's responsibility. The federates synchronize on a `ready` federation
synchronization point before exchanging any event.

The backends share the model and bindings. Each live launcher supplies its own
connector and RTI configuration:

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
- `tests/hla/test_portico_backend.py` — offline codec and time-axis tests plus
  a guarded live case (`PYJEVSIM_PORTICO_LIVE=1`).
- `tests/hla/test_pitch_backend.py` — guarded; runs the encoder round-trip
  when JPype + Java ≥ 11 + `prti1516e.jar` are present, and the full live
  federation when `PYJEVSIM_PITCH_LIVE=1` with a running CRC. Skips otherwise.

## How it maps to HLA

| pyjevsim | HLA / pRTI |
|----------|-----------|
| `HLAInteraction("PingPong.Ping", "out")` on a port | `publishInteractionClass` + `sendInteraction` |
| `HLAInteraction("PingPong.Pong", "in")` on a port | `subscribeInteractionClass` + `receiveInteraction` |
| `HLAAttribute("PingPaddle.hits", "out", object_class=...)` | `registerObjectInstance` + `updateAttributeValues` |
| `HLAAttribute("PingPaddle.hits", "in")` | `subscribeObjectClassAttributes` + `reflectAttributeValues` |
| `Federate.run_until` / `SysExecutor.step` | `timeAdvanceRequest` ↔ `timeAdvanceGrant` |
