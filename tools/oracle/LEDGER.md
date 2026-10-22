# Golden-change ledger

Every change to a trace-oracle golden, and so every merged pull request
that changes a verdict scenario, gets an entry here, newest first, in the
same pull request. The CI job accepts a verdict difference from the merge
base only when this file and the golden both changed, and fails a changed
golden (a file, or `GOLDEN` in `trace_oracle.py`) without a change here.

An entry records:

- **Date** of the merge (YYYY-MM-DD).
- **PR**: the pull request number, and the commit that was measured.
- **Scenarios changed**: each verdict scenario whose hash moved, with the
  old and new sha256 prefixes (informational scenarios only if a golden
  regeneration touched them).
- **Why**: the observable behaviour that changed and the reason it is
  intended. Name the CHANGELOG entry. A performance-only pull request
  should never need an entry; if it does, split it (see CONTRIBUTING.md).
- **Approved by**: the maintainer who accepted the change (the person who
  applied the `semantic-change` label).

Regenerate a golden with
`python tools/oracle/trace_oracle.py --repo <export> --golden <file> --write-golden`
and say in the entry which checkout, Python version and platform produced it.

---

## 2026-10-23 — snapshot hooks see the real state; restore keeps IDs unique

- **PR**: the pull request from branch `fix/snapshot-termination-ids`
  (golden written from its tree on CPython 3.14.0, Windows 11 x86-64;
  file `golden/v2.3.0-dev.json`, which becomes the 2.3.0 golden).
- **Scenarios changed**:
  `snapshot_restore`: c0ba53e6a30a… → b889add70990…
- **Why**: `snapshot_restore` digests the `SnapshotCondition` hook
  arguments and the snapshot's `model_map.json`. Two intended fixes move
  it: the hooks now receive the model's real `cur_state` instead of `""`
  (CHANGELOG [Unreleased] Fixed: `SnapshotCondition` hooks /
  `SnapshotExecutor.con_trans`), and the snapshot records
  `next_object_id` so a restore in a fresh process cannot reuse the IDs of
  restored objects (CHANGELOG Fixed: object IDs across restore). With
  those two fields normalised the traces are identical to v2.2.0; no other
  scenario moved.
- **Approved by**: pending maintainer review (Changbeom Choi).

---

## 2026-10-23 — freeze the v2.2.0 golden

- **PR**: the pull request that adds `tools/oracle/` (branch
  `infra/trace-oracle`).
- **Scenarios changed**: none; first golden. `golden/v2.2.0.json` holds
  all 18 scenarios (15 verdict, 3 informational), produced with
  `--write-golden` from `git archive 9a2b0d2` (the last main before #41:
  v2.2.0 plus the documentation PR #40) on CPython 3.14.0, Windows 11
  x86-64.
- **Why**: fixes the observable behaviour of v2.2.0 as the reference for
  the 2.3.0 performance release. Main at `f7145e6` (after #41, #42, #43
  and #44) reproduces every scenario hash, including the three
  informational ones at the pinned salt; so does the same tree under
  CPython 3.13.13. The digest taken at `b447f6f`, against which #41, #42
  and #44 were checked, matches as well.
- **Approved by**: pending maintainer review (Changbeom Choi).
