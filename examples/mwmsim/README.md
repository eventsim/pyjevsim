# Municipal Waste Management Simulation Example

This example models households, local waste bins, a collection vehicle, and a
simple collection policy. It shows agent-style DEVS composition and
snapshot/restore over longer virtual-time scenarios.

## Model behavior

- Residents follow daily leave-and-return schedules and discard waste when
  leaving home.
- A full local bin increases the resident's dissatisfaction measure.
- The collection vehicle visits bins on a configured schedule and returns to
  base when its capacity is exhausted.
- Scenario files describe household composition and building layout.

## Run

From `examples/mwmsim`, run one named scenario without the `.txt` extension:

```bash
cd examples/mwmsim
python exp.py 910sbh_N100_seed0
```

To run every file under `scenario/`, use:

```bash
python experiment.py
```

Simulation duration, bin and vehicle capacity, random seed, and output options
are defined in `config.py`. The `exp_snapshot.py` and `exp_restore.py` scripts
provide the snapshot examples.

## Scope

The household behavior and collection policy are simplified examples for
software demonstration. Results are not calibrated forecasts of a particular
municipality.

## Reference

- C.-H. Lyoo et al., “Modeling and simulation of a municipal solid waste
  management system based on discrete event system specification,”
  *Proceedings of the 11th Annual Symposium on Simulation for Architecture and
  Urban Design*, 2020.
