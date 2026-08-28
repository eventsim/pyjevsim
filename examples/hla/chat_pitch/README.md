# Pitch chat through the kdx-rti gateway

This legacy integration example runs two pyjevsim chat federates through the
external [kdx-rti](https://github.com/cbchoi/kdx-rti) Java gateway and Pitch
pRTI. It is separate from pyjevsim's built-in JPype Pitch backend under
`pyjevsim.hla.backends.pitch`.

## Prerequisites

1. A compatible Pitch pRTI installation with its CRC running.
2. A built kdx-rti gateway.
3. pyjevsim, PyZMQ, and the kdx-rti Python package:

   ```bash
   python -m pip install -e . pyzmq
   python -m pip install -e <kdx-rti>/python
   ```

Consult the kdx-rti documentation for its supported Pitch version and gateway
build command.

## Run

The two federates need separate gateway processes and disjoint ZMQ port sets.
Use five terminals:

```bash
# 1. Pitch CRC
$PRTI1516E_HOME/prti1516e

# 2. Alice gateway (5555/5556/5557)
<kdx-rti>/run-gateway.sh

# 3. Bob gateway (5558/5559/5560)
<kdx-rti>/run-gateway-bob.sh

# 4. Alice
python -m examples.hla.chat_pitch.run alice --ports 5555,5556,5557

# 5. Bob
python -m examples.hla.chat_pitch.run bob --ports 5558,5559,5560
```

Each federate should print the messages received from its peer until both have
sent the configured `--count` value.

## Implementation

`transport.py` adapts the gateway's ZMQ control, data, and callback sockets to
the pyjevsim transport interface. `run.py` installs `HLAExecutorFactory`,
registers the shared `Chatter` model with interaction bindings, and advances
the federate.

This example handles interactions only. It does not implement object-instance
lifecycle, synchronization points, ownership, data distribution management,
save/restore, or reconnect after a gateway failure.

## Troubleshooting

- A control timeout means the gateway did not answer within the configured
  interval. Check the gateway, CRC, port set, and `--timeout-s` value.
- A join error can indicate an incompatible FOM or a duplicate federate name.
- If no chat messages appear, confirm that both sides use the same interaction
  class and complementary publish/subscribe settings.
