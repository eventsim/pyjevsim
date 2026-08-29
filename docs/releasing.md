# Release checklist

This checklist is for project maintainers. Replace `2.2.0` and `v2.2.0` with
the intended version when preparing another release.

## 1. Prepare the source

- Confirm that `main` contains the intended changes and that the working tree
  is clean.
- Update the version in `pyproject.toml`, `CITATION.cff`, `.zenodo.json`, and
  `docs/source/conf.py`.
- Set `date-released` in `CITATION.cff` only when the release date is known.
- Move release notes from `Unreleased` to a dated section in `CHANGELOG.md`
  and add its version comparison link.
- Check that the README and documentation describe the released behavior and
  do not refer to pending implementation work.
- Keep existing tags and Zenodo records unchanged.

## 2. Validate

```bash
python -m pytest -q
python docs/hla-validation/results/verify_results.py
python examples/hla_atsim/verify_equivalence.py
python -m compileall -q pyjevsim examples
sphinx-build -W -b html docs/source <temporary-directory>/docs-html
```

Build and documentation commands require the packages in
`requirements_docs.txt` plus `build` and `twine`. Live RTI checks are optional
release checks and should be recorded separately with the RTI, Java, Python,
and source versions used.

After the validation commit is pushed and CI is green, export that exact clean
commit into a new directory outside the repository. Build there so stale
artifacts and source-tree imports cannot affect the result:

```powershell
$releaseCommit = (git rev-parse HEAD).Trim()
if (git status --porcelain) { throw "dirty worktree" }
if ($releaseCommit -ne (git rev-parse origin/main).Trim()) {
    throw "HEAD and origin/main differ"
}

$releaseRoot = Join-Path $env:TEMP ("pyjevsim-2.2.0-" + [guid]::NewGuid())
$sourceDir = Join-Path $releaseRoot "source"
$distDir = Join-Path $releaseRoot "dist"
New-Item -ItemType Directory -Path $sourceDir, $distDir | Out-Null
git archive --format=tar --output=(Join-Path $releaseRoot "source.tar") $releaseCommit
tar -xf (Join-Path $releaseRoot "source.tar") -C $sourceDir
python -m build --outdir $distDir $sourceDir
python -m twine check --strict (Join-Path $distDir "pyjevsim-2.2.0*")
```

Require exactly one wheel and one source distribution. Inspect both archives
to confirm that `pyjevsim/hla/backends/gorti.py` is present and that the
external GORTI SDK is not bundled.

Before tagging, install the wheel and source distribution, with dependencies,
in separate fresh environments under `$releaseRoot`. Run `pip check`, then use
Python's isolated mode to prevent the source checkout from shadowing the
installed package:

```powershell
python -m venv (Join-Path $releaseRoot "wheel-venv")
python -m venv (Join-Path $releaseRoot "sdist-venv")
$wheelPy = Join-Path $releaseRoot "wheel-venv\Scripts\python.exe"
$sdistPy = Join-Path $releaseRoot "sdist-venv\Scripts\python.exe"
& $wheelPy -m pip install --no-cache-dir (Join-Path $distDir "pyjevsim-2.2.0-py3-none-any.whl")
& $wheelPy -m pip check
& $wheelPy -I -c "from importlib.metadata import version; import pyjevsim; from pyjevsim.hla import available_rtis; assert version('pyjevsim') == '2.2.0'; assert 'gorti' in available_rtis(); print(version('pyjevsim'))"
& $sdistPy -m pip install --no-cache-dir (Join-Path $distDir "pyjevsim-2.2.0.tar.gz")
& $sdistPy -m pip check
& $sdistPy -I -c "from importlib.metadata import version; import pyjevsim; from pyjevsim.hla import available_rtis; assert version('pyjevsim') == '2.2.0'; assert 'gorti' in available_rtis(); print(version('pyjevsim'))"
```

## 3. Publish the source release

1. Push `main` and wait for all required GitHub Actions checks to pass.
2. Create an annotated tag from the tested commit:

   ```bash
   git tag -a v2.2.0 -m "pyjevsim 2.2.0"
   git push origin v2.2.0
   ```

3. Create the GitHub release from that tag and use the corresponding
   `CHANGELOG.md` section as the release notes.
4. Do not move or recreate the tag after publication. Correct a released
   defect with a new version.
5. If this version is also published on PyPI, upload the checked artifacts and
   verify the published metadata:

   ```bash
   python -m twine upload \
     dist/2.2.0/pyjevsim-2.2.0.tar.gz \
     dist/2.2.0/pyjevsim-2.2.0-py3-none-any.whl
   python -m pip install --no-cache-dir pyjevsim==2.2.0
   python -c "from importlib.metadata import version; print(version('pyjevsim'))"
   ```

   PyPI publication changes external state and requires the maintainer's
   credentials; it is not required for Zenodo to archive the GitHub release.

## 4. Archive with Zenodo

- Before creating the GitHub release, confirm that Zenodo's GitHub integration
  is enabled for `eventsim/pyjevsim`.
- Wait for Zenodo to ingest the GitHub release and assign a new version DOI.
- Check that the archived source contains the HLA validation guide, AT/SIM
  example, reference files, and release metadata.
- Add the version DOI to the GitHub release notes and to publication material.
  The concept DOI `10.5281/zenodo.21002028` remains the identifier for all
  versions.
- If a version DOI must appear inside the tagged metadata, reserve it before
  tagging and use Zenodo's manual-deposit workflow instead of relying only on
  automatic GitHub ingestion.

## 5. Final checks

- Confirm that the Read the Docs tag version is active, its build succeeds,
  and the intended `latest`/`stable` aliases point to the correct version.
- Verify the GitHub source archive and Zenodo record against the tag commit.
- Update downstream publication or citation files with the new immutable tag
  and version DOI.
