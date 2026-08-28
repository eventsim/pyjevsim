# Sparse-time benchmark record

This benchmark uses a two-model topology (one generator and one sink) with
100 events. Only the simulated interval between events changes. A simulator
that advances directly to its next scheduled event should take approximately
the same wall-clock time at each interval.

The table below was captured on 2026-05-05 after virtual-time event jumping
was implemented. Each value is the best of three runs.

| Period | pyjevsim tr/s | xdevs tr/s | pypdevs tr/s | reference tr/s |
|---:|---:|---:|---:|---:|
| 1 | 393 k | 449 k | 760 k | 1.71 M |
| 10 | 410 k | 462 k | 811 k | 1.69 M |
| 100 | 412 k | 455 k | 802 k | 1.72 M |
| 1000 | 396 k | 460 k | 785 k | 1.63 M |

| Period | pyjevsim | xdevs | pypdevs | reference |
|---:|---:|---:|---:|---:|
| 1 | 0.5 ms | 0.4 ms | 0.3 ms | 0.1 ms |
| 10 | 0.5 ms | 0.4 ms | 0.2 ms | 0.1 ms |
| 100 | 0.5 ms | 0.4 ms | 0.3 ms | 0.1 ms |
| 1000 | 0.5 ms | 0.4 ms | 0.3 ms | 0.1 ms |

In this capture, pyjevsim stayed between 393 k and 412 k transitions per
second and reported 0.5 ms for each tested period. The measurement supports
only the expected absence of a period-dependent loop in these four cases. It
does not establish general performance, and sub-millisecond timings are
sensitive to host load and timer resolution.

The generated CSV was not retained in the repository. Run the benchmark again
to obtain results for the current source and environment:

```bash
python -m benchmark.run_sparse \
  --periods 1 10 100 1000 --count 100 --repeat 3 \
  --output benchmark/results/sparse.csv
```

The CSV contains the transition count, elapsed simulation time, throughput,
and any adapter error for each row. Record the pyjevsim commit, Python and
engine versions, operating system, CPU, and raw CSV before citing a new run.
