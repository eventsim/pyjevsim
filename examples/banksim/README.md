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

- `gen_num`: initial number of customer generators.
- `queue_size`: maximum queue capacity; arrivals are dropped while full.
- `proc_num`: number of accountant service models.
- `max_user`: number of completed customers that ends the run.
- `wiq_time`: virtual time at which the generator count changes.
- `wiq_gen_num`: generator count after `wiq_time`.

## Run one variant

The individual scripts take `wiq_time` and `wiq_gen_num`:

```bash
cd examples/banksim
python banksim_classic.py 100 20
```

Available variants are `banksim_classic.py`, `banksim_model_snapshot.py`,
`banksim_model_restore.py`, `banksim_snapshot.py`, and `banksim_restore.py`.
The model-level scripts save or restore individual models; the other snapshot
scripts operate on the simulation state.

## Run the comparison set

`banksim.py` takes one `wiq_time` value and runs all variants with three
generator-count cases:

```bash
cd examples/banksim
python banksim.py 100
```

Logs and CSV summaries are written below `output/<wiq_time>/`.
