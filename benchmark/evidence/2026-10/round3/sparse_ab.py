"""Interleaved main/cand run_sparse comparison (fresh process per run, min sim_s)."""
import re, subprocess, sys
S = sys.argv[1]; rounds = int(sys.argv[2]); count = sys.argv[3]; periods = sys.argv[4:]
PY = S + "/venv/Scripts/python.exe"
best = {}
for r in range(rounds):
    for lab in (("main", "cand") if r % 2 == 0 else ("cand", "main")):
        out = subprocess.run([PY, "-m", "benchmark.run_sparse", "--engines", "pyjevsim", "pypdevs",
                              "--count", count, "--repeat", "5", "--periods", *periods],
                             cwd=f"{S}/perf3/{lab}", capture_output=True, text=True).stdout
        for line in out.splitlines():
            m = re.match(r"\s*(pyjevsim|pypdevs)\s+(\d+)\s+(\d+)\s+\d+\s+[\d.]+\s+([\d,]+)\s*$", line)
            if m:
                k = (lab, m.group(1), m.group(2))
                best[k] = min(best.get(k, 1e9), 2 * int(m.group(3)) / float(m.group(4).replace(",", "")))
for p in periods:
    mj, cj = best[("main", "pyjevsim", p)], best[("cand", "pyjevsim", p)]
    mp, cp = best[("main", "pypdevs", p)], best[("cand", "pypdevs", p)]
    print(f"period {p:>5} count {count}: pyjevsim sim_s main {mj:.5f} cand {cj:.5f} cand/main {cj/mj:.3f} | "
          f"pypdevs main {mp:.5f} cand {cp:.5f} | ratio vs pypdevs (tr/s) main {mp/mj:.3f} cand {cp/cj:.3f}")
