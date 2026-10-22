# Trace oracle

The trace oracle checks that a change to pyjevsim does not change what a
simulation does. It runs 18 scenarios against a checkout, records every
model-level call (`output`, `int_trans`, `ext_trans`, `con_trans`) with its
payload, each instant's engine output and the models' states, and reduces
each scenario to one sha256. Two checkouts behave the same on a scenario
when the hashes match.

Inside one instant the record is sorted, so the order in which the engine
happens to process same-time models does not matter; the sequence of
instants, the time of each one and everything that happens in it does.
`order_check.py` looks at the unsorted order separately.

The oracle was written to check #41, #42 and #44 against their merge bases
and moved here unchanged apart from the repository adaptation. Its
module docstring describes the instrumentation in detail.

## Files

| File | Purpose |
|---|---|
| `trace_oracle.py` | Runs scenarios, writes digests or hash files, compares them. |
| `oracle_models.py` | Scenario models copied from `tests/` at v2.2.0, so that editing a unit test cannot move a hash. |
| `bank_driver.py` | Builds and runs `examples/banksim` deterministically; also a timing driver (`--repo <checkout>`). |
| `order_check.py` | Same-time order reproducibility check (not run in CI). |
| `ci_gate.sh` | The CI gate; `.github/workflows/oracle.yml` runs it. |
| `golden/v2.2.0.json` | Per-scenario hashes of v2.2.0 (the current golden). |
| `LEDGER.md` | Record of every golden change and accepted mismatch. |

## Scenarios

Verdict scenarios fail a comparison when their hash differs.
Informational ones depend on same-time processing order by construction
(set iteration in the engine); they run with a pinned executor-hash salt,
and a difference is reported as `INFO-DIFF` without failing.

| Scenario | Kind | What it exercises |
|---|---|---|
| `devstone_hi_d6_w8` | verdict | DEVStone HI, depth 6, width 8, 100 events, fully traced |
| `devstone_li_d48_w1` | verdict | DEVStone LI, depth 48, width 1, fully traced |
| `devstone_hi_d10_w10_counts` | verdict | DEVStone HI 10x10 at benchmark size, untraced; per-atomic transition counts only |
| `ring_1000` | verdict | 1000 relays in a ring with three injected tokens: sparse future-event list, `cancel_rescheduling` |
| `bank_canon` | verdict | `examples/banksim` with per-model random streams and order-independent queue and result models |
| `bank_raw` | informational | `examples/banksim` as shipped (one global random stream, FIFO in bag order) |
| `tests_structural_stm` | verdict | `StructuralModel` (generator to receiver) |
| `tests_confluent` | verdict | confluent transitions: default and overridden `con_trans`, external-event path |
| `tests_cancel_rescheduling` | verdict | `cancel_rescheduling` keeps the original deadline |
| `tests_v_time_jump` | verdict | V_TIME jump to the next event, horizon clipping, fractional time advance |
| `tests_entity_destruction` | verdict | `dest_t` destruction, messages to destroyed models, coupling clean-up |
| `same_instant_external` | verdict | external events at the same instant as internal ones; `track_uncaught` off and on; deprecated immediate delivery; HLA_TIME `step()`; R_TIME |
| `snapshot_restore` | verdict | snapshot conditions, model and simulation snapshots, restore and continue, `model_dump` round trip |
| `hla_pingpong_inprocess` | verdict | `examples/hla_pingpong` two-federate in-process run |
| `hla_atsim_rows` | verdict | AT/SIM standalone and two-federate application rows |
| `hla_atsim_trace` | informational | the same AT/SIM runs with the full model trace |
| `hla_verify_equivalence` | verdict | `examples/hla_atsim/verify_equivalence.py`: exit code and output |
| `mwmsim_433sbh` | informational, slow | `examples/mwmsim` scenario `433sbh_N100_seed0` with a fake clock (about 15 s) |

A scenario's hash covers its trace, its final summary and the first line of
any error. Model names, printed text and float reprs are part of it; object
ids, addresses, paths and wall time are not. The raw dill bytes of the
snapshot files are recorded as a warn-only `strict` section because they
embed object ids, module names and the Python version.

## Usage

Run from the repository root with an environment that has the test
dependencies (`dill`, `PyYAML`). `--repo` defaults to the repository that
contains the tool; any other checkout or `git archive` export works too,
including ones older than the tool. Each scenario runs in its own
subprocess with that checkout first on `sys.path`, and the run asserts that
`pyjevsim` was imported from it.

```bash
# compare the working tree with the current golden (hash mode, ~1 minute)
python tools/oracle/trace_oracle.py --golden

# full digests with traces, for a readable diff between two checkouts
python tools/oracle/trace_oracle.py --repo ../base --out base.json
python tools/oracle/trace_oracle.py --out cand.json
python tools/oracle/trace_oracle.py --compare base.json cand.json

# hash files only (what CI does)
python tools/oracle/trace_oracle.py --out head.json --hash-only

# subsets
python tools/oracle/trace_oracle.py --golden --scenarios tests_confluent,ring_1000
python tools/oracle/trace_oracle.py --golden --no-slow          # without mwmsim_433sbh
python tools/oracle/trace_oracle.py --list
```

`--compare` takes full digests or hash files in any combination. For a
differing scenario it prints the first differing instant and the events
only in one side when both inputs are full digests; with a hash file it can
only say whether the final summary differs too. Scenarios that a run left
out (`--scenarios`, `--skip`, `--no-slow`) compare as `SKIPPED`.

`--perturb-check DIR` reruns every scenario with several executor-hash
salts and reports which sorted digests move; that is how the three
informational scenarios were identified.

## CI gate

`.github/workflows/oracle.yml` runs `tools/oracle/ci_gate.sh` on pull
requests and on pushes to `main` (ubuntu, Python 3.13, full history). The
script:

1. finds the merge base of `HEAD` and `origin/main` (on a push, the commit
   that was pushed over), exports it with `git archive`, and runs the oracle
   in hash mode on the export and on the checkout. Any verdict-scenario
   difference fails the job; informational differences and the `strict`
   section become warnings.
2. compares `HEAD` with the current golden (`GOLDEN` in `trace_oracle.py`).
   A mismatch fails the job unless `tools/oracle/LEDGER.md` changed between
   the merge base and `HEAD`. A changed golden file without a ledger change
   fails too.

The job passes `--no-slow`, so `mwmsim_433sbh` is reported as skipped. With
it, the two oracle runs would take about 45 s of wall time on the machine
that froze the golden and an estimated two to three minutes on a hosted
runner; it is informational, so it cannot fail the job either way. Run it
locally with `python tools/oracle/trace_oracle.py --golden`.

To run the gate locally (Git Bash on Windows works too):

```bash
bash tools/oracle/ci_gate.sh                      # against origin/main
ORACLE_BASE=HEAD~1 bash tools/oracle/ci_gate.sh   # trial against the parent
```

`ORACLE_ARGS` passes extra arguments to both runs, `ORACLE_GOLDEN` replaces
the golden and `PYTHON` the interpreter.

### When a scenario changes

A performance-only change must leave every verdict hash unchanged. A
change that alters observable behaviour (an engine semantics fix, a fix to
an example used by a scenario, a change to `oracle_models.py` or to the
oracle's canonical form) goes in its own pull request with the
`semantic-change` label and:

1. adds an entry to `LEDGER.md` naming the scenarios whose hashes moved and
   why;
2. adds a new golden produced from the pull request's tree, for example
   `python tools/oracle/trace_oracle.py --golden tools/oracle/golden/<name>.json --write-golden`,
   and points `GOLDEN` in `trace_oracle.py` at it, so that later pull
   requests compare with the new behaviour. Old goldens stay for reference.

If the oracle's canonical form itself changes, also bump `ORACLE_VERSION`;
`--compare` notes when two files come from different versions.

## The v2.2.0 golden

`golden/v2.2.0.json` was produced on 2026-10-23 from `git archive 9a2b0d2`
(v2.2.0 plus the documentation-only #40, the last `main` before #41) with

```bash
python tools/oracle/trace_oracle.py --repo <export> --label "v2.2.0 (git archive 9a2b0d2)" \
    --golden tools/oracle/golden/v2.2.0.json --write-golden
```

on CPython 3.14.0, Windows 11 x86-64. Checks made at the time:

| Candidate | Python | Result |
|---|---|---|
| `main` at `f7145e6` (after #41, #42, #43, #44), full digest | 3.14.0 | all 18 scenarios match, informational ones included |
| `main` at `f7145e6`, hash mode against the golden | 3.13.13 | all 18 match; `strict` differs (warn-only, dill bytes) |
| `main` at `f7145e6`, hash mode against the golden, `--no-slow` | 3.11.15 | all 17 run match; `strict` differs (warn-only) |
| digest taken at `b447f6f` (#41's branch), which #41, #42 and #44 were checked against | 3.14.0 | all 18 match |
| a full digest of the `9a2b0d2` export compared with the `f7145e6` one | 3.14.0 | identical traces in every scenario, `strict` included |

No scenario differs between v2.2.0 and `main`: #42 and #44 changed no
observable behaviour on these scenarios. Their CHANGELOG caveats are about
monkeypatched or subclassed engine internals and the identity of the
deliverer passed to `output()`, which no scenario exercises; the same-time
order among models also stayed as it was (the informational scenarios,
pinned to one salt, match too).

All of these ran on Windows. The golden has not been checked on Linux
before CI first runs it there; nothing in the hashed data is known to be
platform dependent (no paths, `\r\n` normalised, float reprs are
platform independent), but if the first Linux run reports a golden
mismatch on an unchanged tree, it is a platform difference: record it in
the ledger and add a Linux golden rather than loosening the check.

## Order check (V2)

The oracle sorts each instant, so it cannot tell whether the engine
processes same-time models in a reproducible order. `order_check.py` runs
scenarios once per executor-hash salt, each in a fresh subprocess, and
compares the unsorted traces:

```bash
python tools/oracle/order_check.py                       # informational scenarios, salts 1-6
python tools/oracle/order_check.py --all --salts 1,2,3   # every scenario
python tools/oracle/order_check.py --vary-hashseed --json order.json
```

For each scenario it prints whether the processing order is stable across
the salts and whether the outcome (the sorted hash) is, plus the first
instant where the order differs. On `main` at `f7145e6`
(`--all --salts 1,2,3`):

- the order varies in 13 scenarios, verdict ones included (for example
  `tests_confluent` from its first instant);
- it is stable in `tests_structural_stm` and `hla_pingpong_inprocess`, and
  trivially in the three untraced scenarios (`devstone_hi_d10_w10_counts`,
  `hla_atsim_rows`, `hla_verify_equivalence`);
- the outcome varies in exactly the three informational scenarios.

The roadmap's gate for promoting an informational scenario to a verdict
one is a stable order and outcome over six salts in fresh processes. This
is a diagnostic and not part of CI.
