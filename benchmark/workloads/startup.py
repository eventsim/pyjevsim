"""W6: import time and process start-up, each in a bare fresh process.

The child is a plain ``python -E -c`` process that imports nothing but
``sys`` and ``time`` before ``import pyjevsim``, so the measured import
includes every module pyjevsim pulls in (a harness-driven child would
already have ``json``, ``argparse`` and friends loaded).  Three metrics:

``import_s``
    ``import pyjevsim`` (the package import only).
``startup_s``
    ``import pyjevsim`` + ``from pyjevsim.system_executor import
    SysExecutor`` + ``SysExecutor(1)``: what a script pays before its first
    model is registered.
``process_s``
    Wall time of the whole process as seen by the parent (interpreter
    start-up and teardown included); the noisiest of the three.

Run it on warm ``__pycache__`` directories (the suite's warm-up run does
that), otherwise the first run also pays byte-compilation.
"""

_CODE = (
    "import sys\n"
    "sys.path.insert(0, {repo!r})\n"
    "import time\n"
    "t0 = time.perf_counter()\n"
    "import pyjevsim\n"
    "t1 = time.perf_counter()\n"
    "from pyjevsim.system_executor import SysExecutor\n"
    "SysExecutor(1)\n"
    "t2 = time.perf_counter()\n"
    "import json, os\n"
    "print('@@SUITE@@ ' + json.dumps({{'import_s': t1 - t0, "
    "'startup_s': t2 - t0, 'file': os.path.abspath(pyjevsim.__file__)}}))\n"
)


def command(python, repo, params):
    return [python, "-E", "-c", _CODE.format(repo=repo)]


def result_from(payload, wall_s):
    return {
        "metrics": {"import_s": payload["import_s"],
                    "startup_s": payload["startup_s"],
                    "process_s": wall_s},
        "build_s": 0.0,
        "parity": {},
        "info": {},
        "pyjevsim_file": payload["file"],
    }
