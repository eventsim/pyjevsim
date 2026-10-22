import json, subprocess, sys
S = sys.argv[1]; reps = int(sys.argv[2])
PY = S + "/../venv/Scripts/python.exe"
cases = {
    "idle10k_pairs5_ev100": [S + "/idle_driver.py", "--pairs", "5", "--events", "100"],
    "idle10k_pairs1_ev100": [S + "/idle_driver.py", "--pairs", "1", "--events", "100"],
    "idle10k_pairs5_ev5000": [S + "/idle_driver.py", "--pairs", "5", "--events", "5000"],
    "bank_seed1_3000": [S + "/../../perf2/oracle/bank_driver.py", "--ticks", "3000", "--seed", "1"],
}
best = {}
outs = {}
for r in range(reps):
    for name, cmd in cases.items():
        for lab in (("main", "cand") if r % 2 == 0 else ("cand", "main")):
            o = json.loads(subprocess.run([PY, *cmd, "--repo", f"{S}/{lab}"], capture_output=True, text=True).stdout)
            best[(name, lab)] = min(best.get((name, lab), 1e9), o["elapsed_s"])
            o.pop("elapsed_s"); outs.setdefault((name, lab), o)
for name in cases:
    m, c = best[(name, "main")], best[(name, "cand")]
    same = outs[(name, "main")] == outs[(name, "cand")]
    print(f"{name}: main {m*1e3:.2f} ms cand {c*1e3:.2f} ms cand/main {c/m:.3f} outcome-equal={same}")
