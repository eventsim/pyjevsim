# Live RTI validation summary

This record separates functional equivalence, callback/batch
characterization, process topology, and claims that were not tested. The
five-invocation campaigns ran on 2026-08-19 against base commit
`fee68c35491b7f8d73ddc495530dd2570dc231e0` plus the then-uncommitted
reviewer-response worktree. After committing those changes, the post-fix
acceptance gate was repeated once per backend against clean source commit
`ad9f54a6ee8b81694db2f42af2504b21e18779c4`; both scenarios passed for both
backends. A new immutable tag and archive are still required.

## Functional equivalence

Behavioral equivalence means exact equality of the sorted canonical rows
`(tick, sense_id, x, y, z)` after formatting coordinates with Python's
`%.10g`. It does not compare raw files, RTI packets, callback order, latency,
or throughput.

| Backend | Environment | Independent invocations | Result |
|---|---|---:|---|
| Pitch | pRTI Free 5.5.2; Temurin 11.0.31+11; JPype 1.7.1; CPython 3.11.15 | 5 | both 30-tick scenarios matched 180/180 rows in every invocation |
| Portico | 2.1.4; `portico.connection=jvm`; Temurin 11.0.31+11; JPype 1.7.1; CPython 3.14.0 | 5 | both 30-tick scenarios matched 180/180 rows in every invocation |

The canonical reference SHA-256 values are
`0a63baaf7095c646d88a082197bf3a0cb65fe5a278781c37b00f35fe45a0a205`
for `self_propelled` and
`2357658121aa36ad4c7f17431b2e1084d577fcd0e45abe1d2d184d4f1764549c`
for `stationary`. These hashes cover the UTF-8 header and numerically sorted
rows with LF line endings.

After adding the bundled Portico same-JVM RID and peer-reflection fail-fast
check, one additional acceptance invocation per backend again matched both
180-row scenarios. Deliberately selecting the Portico distribution's
multicast JGroups RID on a host where discovery was unavailable caused both
federates to form isolated one-member groups; the new check rejected that run
at the first grant with process status 1 instead of writing a 60-row result.
The compact [acceptance manifest](live-acceptance-manifest.json) records the
runner, verifier, configuration, reference, toolchain, return-code, and output
hashes for that post-fix check. It deliberately marks itself `archive_ready:
false` because the new immutable tag and archive/DOI have not yet been made;
the acceptance source commit itself was clean.

## Callback order and batch characterization

The following figures are descriptive measurements of this host and test
configuration, not latency guarantees or cross-RTI rankings.

| Backend and topology | Repetitions | Exactness | Batch rate, min / median / max |
|---|---:|---|---:|
| Pitch, two federates in one Python process/JVM plus an external local CRC | 5 x 10,000 | 50,000/50,000 callbacks and deliveries; exact count, sender order, and decoded identity; nondecreasing HLA timestamps | send-to-last-callback: 6,689.80 / 7,338.72 / 8,065.11 msg/s; both TAR returns: 6,687.87 / 7,336.84 / 8,062.85 msg/s |
| Portico, two federates in one Python process/JVM | 5 x 10,000 | 50,000/50,000 callbacks and deliveries; exact count, arrival order, and decoded identity | send-to-last-callback: 4,938.71 / 5,507.63 / 5,950.90 msg/s; full batch cycle: 4,281.99 / 4,621.25 / 4,878.58 msg/s |

For Pitch, the pooled instrumented Python callback-entry-to-application
delivery interval was 0.0378 ms at p50, 0.0971 ms at p95, and 0.1446 ms at
p99 (`n=50,000`). It is not network, one-way, or round-trip latency. Portico
callbacks in this configuration are receive-order callbacks; their observed
order is not evidence of timestamp ordering or formal IEEE conformance.

## Process and network scope

- Pitch ping-pong completed four independent same-host runs with two OS
  processes and two embedded JVM/LRC instances. Each run joined,
  synchronized, exchanged interaction and attribute data, and resigned;
  one sampled run showed a distinct TCP session from each federate process to
  the live CRC at `127.0.0.1:8989`.
- A Portico exploratory campaign exchanged 10,000 messages in each of five
  same-host two-process runs over loopback TCP with exact count/order/digest.
  It used a temporary JGroups TCP stack override and a bounded join retry, so
  it characterizes that harness rather than the unmodified shipped adapter.
- No successful raw PCAP/PCAPNG payload capture was produced. PktMon attempts
  yielded connection/drop metadata but header-only PCAPNG output.
- No run used two physical hosts. Same-host threads, processes, JVMs, and TCP
  sessions must not be described as multi-host validation.

The Pitch JAR SHA-256 was
`48c1545b89cc741610bef59abc0d7444439e35a693386365f0a509df56871978`;
the Portico JAR SHA-256 was
`146dc0a7916b168396c6e595c42aaed0bdc69d64c5c54e728b7cb53fdd94ea84`;
and the Temurin `jvm.dll` SHA-256 was
`de36fc880fe3ec2bd027255b96d25060b1c426ba7cc38bd31e8551a9dfd50601`.

## Excluded claims

These campaigns do not establish raw wire-format equivalence between RTIs,
network RTT or one-way latency, throughput across physical hosts,
multi-host scalability, loss behavior, third-party federate
interoperability, or formal IEEE 1516 conformance.
