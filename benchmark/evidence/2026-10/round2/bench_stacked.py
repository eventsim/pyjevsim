import subprocess, csv, io, sys, json
BASE = "D:/development/pyjevsim/.claude/worktrees/kind-bardeen-27583d"      # b447f6f
STK  = "D:/development/pyjevsim/.claude/worktrees/perf2-stacked"            # fb9bf10
cfgs = [("hi", 10, 10), ("hi", 6, 8), ("li", 48, 1)]
REPS = 7
def run(cwd, v, d, w):
    out = subprocess.run([sys.executable, "-m", "benchmark.run_devstone", "--variant", v, "--depth", str(d), "--width", str(w), "--events", "100", "--csv"], cwd=cwd, capture_output=True, text=True, check=True).stdout
    row = list(csv.DictReader(io.StringIO(out)))[-1]
    return float(row["sim_time_s"]), int(row["transitions"])
for v, d, w in cfgs:
    t = {"base": [], "base2": [], "stk": []}; tr = {}
    for _ in range(REPS):
        for k, cwd in (("base", BASE), ("stk", STK), ("base2", BASE)):
            s, n = run(cwd, v, d, w); t[k].append(s); tr[k] = n
    mb, mb2, ms = min(t["base"]), min(t["base2"]), min(t["stk"])
    print(f"{v} d{d} w{w}: stacked/base = {mb/ms:.3f}x   control base2/base = {mb/mb2:.3f}x   (min base {mb:.3f}s, stk {ms:.3f}s; transitions {tr['base']} vs {tr['stk']})")
