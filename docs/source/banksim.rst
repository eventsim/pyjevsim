Bank Queue Simulation Example
=============================

BankSim is a queueing example with customer generators, a bounded queue,
service models, and a result collector. It demonstrates coupled models,
snapshot/restore, and a what-if change to the number of generators during a
run.

Prerequisites
-------------

Install pyjevsim and PyYAML from the repository root:

.. code-block:: console

   $ python -m pip install -e .
   $ python -m pip install "PyYAML>=6.0"

Parameters
----------

- ``gen_num``: initial number of customer generators.
- ``queue_size``: maximum queue capacity; arrivals are dropped while full.
- ``proc_num``: number of accountant service models.
- ``max_user``: number of completed customers that ends the run.
- ``wiq_time``: virtual time at which the generator count changes.
- ``wiq_gen_num``: generator count after ``wiq_time``.

Run
---

From ``examples/banksim``, run an individual variant with ``wiq_time`` and
``wiq_gen_num``:

.. code-block:: console

   $ python banksim_classic.py 100 20

The unified runner executes all snapshot and restore variants with three
generator-count cases:

.. code-block:: console

   $ python banksim.py 100

Model API
---------

.. toctree::
   :maxdepth: 4

   banksim_model

Simulation API
--------------

.. toctree::
   :maxdepth: 4

   banksim_sim
