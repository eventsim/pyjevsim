# gorti chat federate

Two `pyjevsim` chat federates exchanging interactions through
[gorti](https://github.com/cbchoi/gorti) — an open-source IEEE
1516-2010 RTI implemented in Go with a Python SDK. Demonstrates
`pyjevsim.hla` against an open-source RTI.

## Prerequisites

```sh
pip install pyjevsim
pip install -e <gorti>/pysdk
# A built rtid binary if you want a real cross-process federation:
go build -o rtid ./cmd/rtid    # in the gorti repo
```

## Run

### A — quick in-process smoke test (no RTI binary)

Both federates share an in-memory RTI keyed by URL. Run in two
terminals; both must use the **same** memory URL.

```sh
# Terminal 1
python -m examples.hla.chat_gorti.run alice --url memory://chat-rti

# Terminal 2
python -m examples.hla.chat_gorti.run bob   --url memory://chat-rti
```

(Note: the `memory://` URL only shares state within a single Python
process. For two processes you need rtid via gRPC — option B.)

### B — against a real rtid

```sh
# Terminal 1 — gorti server
./rtid --listen :7000

# Terminal 2 — alice
python -m examples.hla.chat_gorti.run alice --url grpc://localhost:7000

# Terminal 3 — bob
python -m examples.hla.chat_gorti.run bob   --url grpc://localhost:7000
```

Expected output: alternating "heard 'bob': hello from bob #N" /
"heard 'alice': hello from alice #N" lines until both federates
finish their `--count` (default 5) sends.

## What this example shows

- Same `Chatter` model as `chat_pitch/` — no HLA awareness.
- `GortiTransport` (~120 LOC) wraps `rti1516e.Rti1516eAmbassador`
  (Layer 2 of the gorti pysdk). The ambassador's
  `receiveInteraction` callback forwards into the pyjevsim
  `_HLARouter`; outbound `send()` calls map directly to
  `sendInteraction`.
- `request_time_advance` posts `nextMessageRequest` and blocks on the
  ambassador's `timeAdvanceGrant` callback via a condition variable.

## Limitations of this example transport

- Object-instance lifecycle (register / discover / update with
  handle) not wired — interactions only.
- DDM regions, ownership, sync points not handled.
- `reflectAttributeValues` is forwarded but mapped to a synthetic
  fom_id (the object handle as a string) — production code should
  track object class via `discoverObjectInstance`.

For production use, extend `GortiTransport` or import a more complete
transport from a downstream package.

## Troubleshooting

- **`TimeoutError: timeAdvanceGrant did not arrive within 5s`** — the
  RTI didn't grant. Either the federation isn't time-regulated /
  time-constrained yet (check `enable_time_*` ran), or another
  federate is stuck. Bump `--timeout-s` while debugging.
- **Empty output** — verify both federates use the **same** federation
  name and interaction class FQN. Both default to
  `"HLAinteractionRoot.Communication"`; change in `run.py` if your
  FOM uses something else.
- **`memory://...` URLs don't share** — that scheme is in-process only.
  Use `grpc://...` against a real `rtid` for cross-process.
