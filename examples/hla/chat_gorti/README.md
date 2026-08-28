# gorti chat example

This legacy integration example connects pyjevsim chat federates to the
external [gorti](https://github.com/cbchoi/gorti) RTI and Python SDK. It is not
one of the built-in pyjevsim backends.

## Prerequisites

From the pyjevsim repository and a gorti checkout:

```bash
python -m pip install -e .
python -m pip install -e <gorti>/pysdk
go build -o rtid ./cmd/rtid
```

Run the Go build command from the gorti repository.

## Run

The supplied runner expects a reachable gRPC `rtid`. Start the server and the
two federates in separate terminals:

```bash
# 1. gorti server
./rtid --listen :7000

# 2. Alice
python -m examples.hla.chat_gorti.run alice --url grpc://localhost:7000

# 3. Bob
python -m examples.hla.chat_gorti.run bob --url grpc://localhost:7000
```

Each federate should print peer messages until both have sent the configured
`--count` value. A `memory://` URL is process-local and cannot connect the two
separate runner processes shown above.

## Implementation

`GortiTransport` wraps the gorti Python ambassador. Interaction callbacks pass
through pyjevsim's HLA router, outbound data maps to `sendInteraction`, and
time requests wait for the ambassador's grant callback.

This example implements the interaction path only. Object-class tracking,
ownership, data distribution management, and synchronization points are not
implemented. Reflected attributes use a synthetic FOM identifier based on the
object handle.

## Troubleshooting

- A time-advance timeout can mean that time services were not enabled or that
  another federate stopped advancing.
- If no messages appear, verify the federation name, server URL, and fully
  qualified interaction class on both sides.
- Use a gRPC URL for separate processes; `memory://` state is not shared across
  processes.
