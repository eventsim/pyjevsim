# Live RTI validation summary

These results cover application-visible functional behavior. On 2026-08-29,
Pitch, Portico, and GORTI were each invoked five times from a clean archive of
pyjevsim commit `70a27d9aa902a8a12dad7d850e4a15ac73e25df2`.
Every invocation ran both 30-tick scenarios and matched all 180 canonical
rows. Each GORTI invocation used its own hidden `rtid` process built from a
clean archive of GORTI commit
`475b23b7ea0e6714825c2d3cdbd5ec5c2f21bf6f`.

Earlier campaigns on 2026-08-19 and 2026-08-28 are retained as historical
evidence. The results and hashes below describe the 2026-08-29 clean-candidate
campaign unless explicitly labeled historical.

## Functional equivalence

The comparison requires exact equality of the sorted rows
`(tick, sense_id, x, y, z)` after coordinates are formatted with Python's
`%.10g` conversion. The committed CSV files name the identifier column
`object_name`; its values are the stable `sense_id` strings.

| Backend | Environment | Recorded runs | Result |
|---|---|---:|---|
| Pitch | pRTI Free 5.5.2; Temurin 11.0.31+11; JPype 1.7.1; CPython 3.11.15 | 5 | both 30-tick scenarios matched all 180 reference rows in every run |
| Portico | 2.1.4; `portico.connection=jvm`; Temurin 11.0.31+11; JPype 1.7.1; CPython 3.11.15 | 5 | both 30-tick scenarios matched all 180 reference rows in every run |
| GORTI (experimental) | commit `475b23b`; native Python SDK 0.9.0; grpcio 1.82.1; protobuf 7.35.1; CPython 3.11.15; Go 1.26.5 | 5 | both 30-tick scenarios matched all 180 reference rows in every run |

The GORTI observation covers object registration/discovery, six-attribute
update/reflection, and regulating/constrained logical-time paths. This AT/SIM
campaign did not exercise interaction exchange. It is not evidence of
release-grade GORTI support, complete HLA Object Management, ownership/DDM,
or formal conformance.

The reference SHA-256 values are
`0a63baaf7095c646d88a082197bf3a0cb65fe5a278781c37b00f35fe45a0a205`
for `self_propelled` and
`2357658121aa36ad4c7f17431b2e1084d577fcd0e45abe1d2d184d4f1764549c`
for `stationary`. Each hash covers the UTF-8 CSV header and numerically sorted
rows with LF line endings.

The earlier clean-checkout run also checked the bundled Portico same-JVM
configuration and the missing-peer failure path. Its historical
[2026-08-19 manifest](live-acceptance-manifest.json) records that campaign.
The current [v2.2.0 acceptance manifest](live-acceptance-v2.2.0.json) records
source, configuration, toolchain, return codes, and output hashes for all
three clean release-candidate campaigns. Its retained
[55-file evidence bundle](assets/pyjevsim-v2.2.0-live-acceptance-evidence.zip)
contains the verifier logs and scenario outputs selected for publication.
The manifest and both public ZIPs are retained by the immutable
[`validation/v2.2.0-live-acceptance`](https://github.com/eventsim/pyjevsim/tree/validation/v2.2.0-live-acceptance)
tag. The tracked GORTI SDK is independently retained by its immutable
[`validation/pyjevsim-v2.2.0-gorti-sdk-132741a`](https://github.com/cbchoi/gorti/tree/validation/pyjevsim-v2.2.0-gorti-sdk-132741a)
tree tag.

For the GORTI qualification, `git archive 475b23b` produced a clean source
tree. The protocol bindings were generated from its `proto` tree with
grpcio-tools 1.82.1. Their 58-file aggregate SHA-256 is
`21f7f992ba822bcdb85acd68956f846199835dfd048a122fcf7ca6ec0df33f17`.
The server was rebuilt with
`go build -buildvcs=false -trimpath -o rtid.exe ./rti/cmd/rtid`; the resulting
binary contains no embedded VCS revision and has SHA-256
`af0e539fb9fd6b90bb61d8510bd1826be36b66d96c3365865442ea03fc86b1c6`.
The public
[runtime source archive](assets/gorti-475b23b-runtime-source.zip) contains
the exact server, protocol, tracked SDK, and generated SDK sources used by
the campaign. The current pyjevsim connector is committed in `70a27d9`.

## Toolchain files

- Pitch JAR SHA-256:
  `48c1545b89cc741610bef59abc0d7444439e35a693386365f0a509df56871978`
- Portico JAR SHA-256:
  `146dc0a7916b168396c6e595c42aaed0bdc69d64c5c54e728b7cb53fdd94ea84`
- Temurin `jvm.dll` SHA-256:
  `de36fc880fe3ec2bd027255b96d25060b1c426ba7cc38bd31e8551a9dfd50601`
- Clean pyjevsim source archive SHA-256:
  `93935f589b51c6d68e30f139e3914762ef1bc6c690d4ffc443a2de51f3371635`
- Retained live evidence bundle SHA-256:
  `5ed41296943e8fac4d1b73173cff2e5f0f78a88a2cb186af6d34d1d4160b3da0`
- GORTI runtime source archive SHA-256:
  `b78ebdf016448041479ef8a096ca0b4b96f86b3cf8584825d725a95c9078a18f`
- GORTI buildvcs-disabled `rtid` SHA-256:
  `af0e539fb9fd6b90bb61d8510bd1826be36b66d96c3365865442ea03fc86b1c6`

## Test scope

The tests compare application-visible state on one physical host. They do not
test packet-level behavior, communication performance, operation across
physical hosts, interaction exchange in the AT/SIM campaign, interoperability
with an independently developed federate, complete HLA Object Management, or
formal IEEE 1516 conformance.
