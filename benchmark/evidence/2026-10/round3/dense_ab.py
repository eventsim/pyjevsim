"""Interleaved main/cand dense DEVStone comparison (fresh process per run)."""
import re, subprocess, sys, statistics, json
S = sys.argv[1]; rounds = int(sys.argv[2]); repeat = sys.argv[3]
configs = [c.split(":") for c in sys.argv[4:]]  # VARIANT:D:W
PY = S + "/venv/Scripts/python.exe"
res = {}
for r in range(rounds):
    for var, d, w in configs:
        for lab in (("main", "cand") if r % 2 == 0 else ("cand", "main")):
            out = subprocess.run([PY, "-m", "benchmark.run_compare", "--engines", "pyjevsim", "pypdevs",
                                  "--events", "100", "--period", "1.0", "--repeat", repeat,
                                  "--variant", var, "--depth", d, "--width", w],
                                 cwd=f"{S}/perf3/{lab}", capture_output=True, text=True).stdout
            row = {}
            for line in out.splitlines():
                m = re.match(r"\s*(pyjevsim|pypdevs)\s+\w+.*\s([\d,]+)\s*$", line)
                if m:
                    row[m.group(1)] = float(m.group(2).replace(",", ""))
            res.setdefault(f"{var}{d}x{w}", {}).setdefault(lab, []).append(row)
for cfg, d in res.items():
    out = {}
    for lab, rows in d.items():
        pj = [x["pyjevsim"] for x in rows]; pd = [x["pypdevs"] for x in rows]
        ratios = [x["pyjevsim"] / x["pypdevs"] for x in rows]
        out[lab] = dict(pyj_med=statistics.median(pj), pyj_max=max(pj), pyp_med=statistics.median(pd),
                        ratio_med=statistics.median(ratios))
    c, m = out["cand"], out["main"]
    print(f"{cfg}: main pyj {m['pyj_med']:,.0f} pyp {m['pyp_med']:,.0f} ratio {m['ratio_med']:.3f} | "
          f"cand pyj {c['pyj_med']:,.0f} pyp {c['pyp_med']:,.0f} ratio {c['ratio_med']:.3f} | "
          f"cand/main pyj(med) {c['pyj_med']/m['pyj_med']:.3f} ratio-of-ratios {c['ratio_med']/m['ratio_med']:.3f}")
json.dump(res, open(f"{S}/perf3/dense_ab_{'_'.join(a for a in sys.argv[4:]).replace(':','')}.json", "w"))
