# Contributing to pyjevsim

Bug reports, documentation fixes, tests, and code contributions are welcome.
For a substantial change, open an issue first so the design and compatibility
impact can be discussed before implementation.

## Development setup

Create a virtual environment with Python 3.10 or later, then install the
package and test dependencies:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]" -r docs/hla-validation/requirements-validation.txt
```

Activate the environment using the command appropriate for your shell.

## Tests

Run the unit tests and the Java-free HLA checks from the repository root:

```bash
python -m pytest -q
python docs/hla-validation/results/verify_results.py
python examples/hla_atsim/verify_equivalence.py
```

Live Pitch and Portico tests are optional because they require external Java
and RTI installations. Their setup is documented in
[`docs/hla-validation/README.md`](docs/hla-validation/README.md).

## Documentation

Install the documentation dependencies and treat Sphinx warnings as errors:

```bash
python -m pip install -r requirements_docs.txt
sphinx-build -W -b html docs/source docs/build/html
```

Keep public documentation focused on supported behavior and reproducible
commands. Record limitations directly; avoid describing planned work as an
implemented feature.

## Pull requests

- Keep each pull request focused on one change.
- Add or update tests for behavior changes.
- Update user documentation and `CHANGELOG.md` when public behavior changes.
- Preserve backward compatibility unless the change is discussed and clearly
  documented.
- Do not commit RTI distributions, license files, credentials, generated build
  directories, or local validation logs.
- Confirm that the commands in the test section pass before requesting review.

## Performance and semantics changes

The trace oracle in [`tools/oracle/`](tools/oracle/README.md) runs on every
pull request. It compares what the simulation does on 18 scenarios at the
merge base and at the head of the pull request, and compares the head with
the committed golden, currently v2.2.0. The observable behaviour it checks
is described in [`docs/source/semantics.rst`](docs/source/semantics.rst).

- Never mix performance-only and semantics-changing changes in one pull
  request. A performance change must leave every verdict scenario of the
  oracle unchanged; if it cannot, split out the part that changes
  behaviour.
- A pull request that changes observable behaviour on purpose (an engine
  semantics fix, a fix to an example that a scenario runs, a change to the
  oracle's scenarios) carries the `semantic-change` label, which only a
  maintainer applies, and says in its description which scenarios change
  and why.
- Ledger rule: such a pull request adds an entry to
  [`tools/oracle/LEDGER.md`](tools/oracle/LEDGER.md) (date, pull request,
  scenarios changed, why, who approved) and a new golden produced from its
  own tree, and points `GOLDEN` in `tools/oracle/trace_oracle.py` at it, as
  described in the oracle README. Every golden change (a golden file or
  the `GOLDEN` pointer) needs a ledger entry in the same pull request.
- The oracle job must pass. A verdict-scenario difference from the merge
  base fails it unless the pull request changes both the ledger and the
  golden. `HEAD` must always match the golden that `GOLDEN` names; a
  ledger entry does not excuse a mismatch there.

Run the oracle locally before opening a pull request that touches the
engine:

```bash
python tools/oracle/trace_oracle.py --golden
```

For performance claims, state the workload, the commits compared, the
Python version and the platform, and keep the raw results (see
[`benchmark/evidence/`](benchmark/evidence/2026-10/README.md)).

By contributing, you agree that your contribution is licensed under the
project's [MIT License](LICENSE).

Maintainers can use the [release checklist](docs/releasing.md) when preparing
a tag and archival deposit.
