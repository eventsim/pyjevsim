# Pitch RTI chat federate (via kdx-rti gateway)

Two `pyjevsim` chat federates exchanging interactions through a Pitch
RTI, mediated by [kdx-rti](https://github.com/cbchoi/kdx-rti)'s Java
gateway. Demonstrates `pyjevsim.hla` against a real (commercial) RTI.

## Prerequisites

1. **Pitch pRTI 11.0.22+** running. Set `PRTI1516E_HOME` and start the CRC.
2. **kdx-rti gateway** built and ready (`mvn -f kdx-rti/pom.xml package`).
3. **Python environment** with:
   ```sh
   pip install pyjevsim pyzmq
   pip install -e <kdx-rti>/python
   ```

## Run (two-federate chat)

Five terminals, mirroring kdx-rti's M6 runbook. Two federate seats
require two gateway processes bound to disjoint ZMQ port triples.

```sh
# Terminal 1 — Pitch CRC
$PRTI1516E_HOME/prti1516e

# Terminal 2 — alice's gateway (ports 5555/5556/5557)
<kdx-rti>/run-gateway.sh

# Terminal 3 — bob's gateway   (ports 5558/5559/5560)
<kdx-rti>/run-gateway-bob.sh

# Terminal 4 — alice federate
python -m examples.hla.chat_pitch.run alice --ports 5555,5556,5557

# Terminal 5 — bob federate
python -m examples.hla.chat_pitch.run bob   --ports 5558,5559,5560
```

Expected output on each side: alternating "heard 'bob': hello from bob #N"
/ "heard 'alice': hello from alice #N" lines until both federates
finish their `--count` (default 5) sends.

## What this example shows

- The `Chatter` model (`examples/hla/_chat_model.py`) is **pure DEVS**
  — no HLA imports, no transport awareness. The same class is reused
  by `chat_gorti/`.
- `PitchTransport` (in `transport.py`) is a ~200-line implementation
  of `pyjevsim.hla.Transport` wrapping `kdx_rti.GatewayClient`'s ZMQ
  sockets. All HLA-specific lifecycle (`connect / join / publish / ...`)
  is delegated to the gateway via JSON envelopes.
- `run.py` wires it up: builds the `SysExecutor` in `HLA_TIME` mode,
  swaps in `HLAExecutorFactory`, registers the model with bindings,
  and drives `Federate.run_until`.

## Limitations of this example transport

- Object-instance lifecycle (register / discover / delete / remove) is
  not wired — interactions only.
- Sync points, ownership, DDM regions, save/restore are not handled.
- No reconnect on gateway crash — federate exits.

For production use, extend `PitchTransport` (or upstream
`kdx_rti.HLAAdapter` once it's been ported to the Transport contract).

## Troubleshooting

- **`TimeoutError: no control envelope from gateway within 5s`** — the
  gateway didn't respond. Check it's running and reachable on the
  control port. Bump `--timeout-s` if your CRC is slow to grant.
- **`gateway error on joinFederation`** — federation already exists with
  a different FOM, or your federate name is taken. Use a unique name.
- **Empty output (no chat lines)** — both federates joined but neither
  is publishing/subscribing the right interaction class. Check
  `chat_class` in `run.py` matches your gateway's loaded FOM.
