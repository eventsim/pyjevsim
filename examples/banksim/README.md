# Bank Queue Simulation Example

BankSim is a queueing example with customer generators, a bounded queue,
service models, and a result collector. It demonstrates coupled models,
snapshot/restore, and a what-if change to the number of generators during a
run.

## Prerequisites

Install pyjevsim and PyYAML from the repository root before running the
example:

```bash
python -m pip install -e .
python -m pip install "PyYAML>=6.0"
```

## Parameters

`scenario.yaml`:

- `gen_num`: initial number of customer generators.
- `queue_size`: maximum queue capacity; arrivals are dropped while full.
- `proc_num`: number of accountant service models.
- `max_user`: number of served customers that ends the run.
- `max_simtime`: not used by the scripts.
- `seed` (optional, commented out by default): run seed, see below.

Command line:

- `wiq_time`: number of `simulate(1)` steps after which the generator count
  changes.
- `wiq_gen_num`: number of running generators after `wiq_time`. Fewer than
  `gen_num`: `gen{wiq_gen_num}` ... `gen{gen_num-1}` are stopped through
  their `stop` port. More: `gen{gen_num}` ... `gen{wiq_gen_num-1}` are added
  and started; the running generators keep their schedules.
- `--seed N`: run seed (overrides `seed` in `scenario.yaml`).
- `--max-user N`: overrides `max_user`, for short runs.
- `--config FILE`: another configuration file.

## Run one variant

The individual scripts take `wiq_time` and `wiq_gen_num`:

```bash
cd examples/banksim
python banksim_classic.py 100 20
python banksim_classic.py 100 10 --seed 1 --max-user 20000
```

Available variants are `banksim_classic.py`, `banksim_model_snapshot.py`,
`banksim_model_restore.py`, `banksim_snapshot.py`, and `banksim_restore.py`.
The model-level scripts save or restore individual models; the other snapshot
scripts operate on the simulation state. `banksim_structural.py [--seed N]`
builds a smaller bank as one structural model and runs it for ten steps.

A run ends when `max_user` customers have been served: the result model
writes its report (counts, then every served and dropped customer) to
standard output, flushes it, and ends the process with `os._exit(0)`.

## Seeding

Without a seed the runs are unseeded, as they have always been: every
generator draws from the module-level `random`, and the queue and result
models react to each message as the engine delivers it. The engine delivers
the messages of one instant in an order that follows set iteration over the
executors, whose hashes come from object identity, so seeding the global
`random` alone does not make a run repeatable: the order, and with it the
outcome, can change between processes and between two simulations built in
one process.

With `--seed N` (or `seed: N` in `scenario.yaml`):

- every generator gets its own `random.Random`, derived from the seed and
  the generator's name (`seeding.model_rng`); adding a generator does not
  change the streams of the others;
- the runs use `OrderedBankQueue` and `OrderedBankResult`, which collect the
  messages of an instant and apply them in a fixed order (by port, then by
  customer ID or accountant name) in a zero-duration step.

The same seed then gives a byte-identical report in every process.
`BankUserGenerator(name, rng=None)` and the `Banksim(name, seed=None)`
structural model take the same opt-in arguments; their defaults keep the
original behaviour.

## Which variants are the same simulation

With the same arguments and seed:

| Variants | Same report? |
|---|---|
| a variant run twice | yes |
| `banksim_classic.py` and `banksim_snapshot.py` + `banksim_restore.py` | no. The snapshot holds the same model states as the classic run at `wiq_time`, and both apply the same what-if change, but a simulation snapshot does not record the clock or the scheduled event times: the restored run starts at time 0 with every model rescheduled from its saved state. |
| `banksim_classic.py` and `banksim_model_snapshot.py` + `banksim_model_restore.py` | no, by design: the model restore builds a new simulation from saved generators, queue and result (new accountants, every generator restarted, added generators copied from `gen0`). |

## Run the comparison set

`banksim.py` takes one `wiq_time` value and runs all variants with three
generator-count cases:

```bash
cd examples/banksim
python banksim.py 100            # unseeded
python banksim.py 100 --seed 1   # every variant seeded with 1
```

Logs and CSV summaries are written below `output/<wiq_time>/`.
