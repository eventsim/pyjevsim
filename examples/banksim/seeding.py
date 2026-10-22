"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Opt-in deterministic seeding for the bank example.

Without a seed the bank models draw from the module-level ``random`` (one
global stream, unseeded unless the caller seeds it), which is how the
example has always behaved.  With a seed every random model gets its own
``random.Random`` derived from the seed and the model's name, so

* the same seed gives the same run, and
* a model's draws do not depend on the order in which the engine processes
  models that are active at the same instant, or on how many other models
  exist (adding a generator does not shift the streams of the others).
"""

import hashlib
import random


def stream_seed(seed, model_name):
    """Integer seed of ``model_name``'s stream for run seed ``seed``."""
    digest = hashlib.blake2b(f"{seed}/{model_name}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def model_rng(seed, model_name):
    """Independent random stream for one model, or ``None`` when ``seed`` is ``None``.

    ``None`` makes a model use the module-level ``random`` (the unseeded
    default).
    """
    if seed is None:
        return None
    return random.Random(stream_seed(seed, model_name))
