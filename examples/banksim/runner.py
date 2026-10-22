"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Command line, configuration and the what-if change shared by the
``banksim_*.py`` scripts.
"""

import argparse

import yaml

from examples.banksim.model.model_queue import BankQueue, OrderedBankQueue
from examples.banksim.model.model_result import BankResult, OrderedBankResult
from examples.banksim.model.model_user_gen import BankUserGenerator
from examples.banksim.seeding import model_rng


def parse_args(description, argv=None):
    """Parse ``wiq_time wiq_gen_num [--seed N] [--max-user N] [--config FILE]``."""
    p = argparse.ArgumentParser(description=description)
    p.add_argument("wiq_time", type=int,
                   help="number of simulate(1) steps after which the generator count changes")
    p.add_argument("wiq_gen_num", type=int,
                   help="number of running generators after wiq_time")
    p.add_argument("--seed", type=int, default=None,
                   help="run seed: one independent random stream per generator, derived from "
                        "the seed and the generator's name. Default: the 'seed' key of the "
                        "configuration file if it has one, otherwise unseeded (all generators "
                        "share the module-level random, as before)")
    p.add_argument("--max-user", type=int, default=None,
                   help="override max_user from the configuration file")
    p.add_argument("--config", default="scenario.yaml",
                   help="configuration file (default: scenario.yaml)")
    return p.parse_args(argv)


def load_config(args):
    """Read the YAML configuration and apply the command-line overrides.

    Returns a dict with ``gen_num``, ``queue_size``, ``proc_num``,
    ``max_user``, ``max_simtime`` and ``seed`` (``None`` when unseeded).
    """
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)
    if args.max_user is not None:
        config["max_user"] = args.max_user
    seed = args.seed if args.seed is not None else config.get("seed")
    config["seed"] = None if seed is None else int(seed)
    return config


def bank_classes(seed):
    """Queue and result classes for a run: ``(queue_cls, result_cls)``.

    An unseeded run uses ``BankQueue`` and ``BankResult`` exactly as before.
    A seeded run uses ``OrderedBankQueue`` and ``OrderedBankResult``, which
    apply the messages of an instant in a fixed order: per-generator streams
    alone do not make a run reproducible, because the engine delivers
    same-instant messages in an order that changes from process to process.
    """
    if seed is None:
        return BankQueue, BankResult
    return OrderedBankQueue, OrderedBankResult


def apply_what_if(ss, gen_num, wiq_gen_num, que, seed):
    """Change the number of running generators from ``gen_num`` to ``wiq_gen_num``.

    Called between two ``simulate(1)`` steps; the change takes effect at the
    current instant.  Fewer generators: ``gen{wiq_gen_num}`` ...
    ``gen{gen_num-1}`` get an event on their ``stop`` port and passivate.
    More generators: ``gen{gen_num}`` ... ``gen{wiq_gen_num-1}`` are added,
    coupled to ``que`` and started through a ``start_added`` input port of
    the executor, so the running generators keep their schedules.
    ``banksim_classic.py`` and ``banksim_restore.py`` both apply the change
    through this function (the restored run still differs from the classic
    one; see ``banksim_restore.py``).
    """
    if wiq_gen_num < gen_num:
        ss.insert_input_port("stop")
        for i in range(wiq_gen_num, gen_num):
            ss.coupling_relation(None, "stop", ss.get_model(f"gen{i}"), "stop")
        ss.insert_external_event("stop", None)
    elif wiq_gen_num > gen_num:
        ss.insert_input_port("start_added")
        for i in range(gen_num, wiq_gen_num):
            name = f"gen{i}"
            gen = BankUserGenerator(name, rng=model_rng(seed, name))
            ss.register_entity(gen)
            ss.coupling_relation(None, "start_added", gen, "start")
            ss.coupling_relation(gen, "user_out", que, "user_in")
        ss.insert_external_event("start_added", None)
