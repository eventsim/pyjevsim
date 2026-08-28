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

By contributing, you agree that your contribution is licensed under the
project's [MIT License](LICENSE).

Maintainers can use the [release checklist](docs/releasing.md) when preparing
a tag and archival deposit.
