Simulation semantics
====================

This page describes what a model can observe while ``SysExecutor`` runs it:
the order of calls within a simulated instant, which time a model sees, and
when a run stops. It documents the current behaviour, including parts that
are known to be unsatisfactory, so that a change to any of them is a
deliberate, recorded decision.

The repository's trace oracle (``tools/oracle/``) checks this behaviour on
every pull request. A change that alters it goes in its own pull request
with a golden-ledger entry; see ``CONTRIBUTING.md``.

Instants
--------

The engine advances from one *instant* to the next. In virtual time
(``ExecutionType.V_TIME``) one instant is processed per ``schedule()``
call:

1. Models whose creation time has arrived are activated.
2. Every model whose request time is due (at or before the current time)
   is *imminent*.
3. The instant is processed in four phases (below).
4. ``global_time`` jumps to the earliest of the next request time, the next
   queued external event, the next model creation and the ``simulate()``
   horizon. When more events are due at the same time (for example after a
   zero time advance) the clock does not move, and the next ``schedule()``
   call processes them as a new instant at the same time.
5. Models whose destruction time is at or before the new clock value are
   removed, together with their couplings, before the next instant runs.

In real time (``ExecutionType.R_TIME``) step 4 instead adds
``time_resolution`` to the clock and sleeps for the rest of that wall-clock
interval. In ``ExecutionType.HLA_TIME`` the federate calls
``step(granted_time)``, which processes every instant up to and including
``granted_time`` with the same four phases and then sets the clock to
``granted_time``.

The four phases
---------------

A. **Output.** ``output()`` is called on every imminent model. Each model's
   messages are collected separately.

B. **Routing.** Each receiving model gets a *bag*: a list of
   ``(port, message)`` pairs. External events due at or before the instant
   are put into the bags first, in the order of their scheduled time and,
   for equal times, the order in which they were inserted. The messages
   collected in phase A are then appended according to the couplings.
   Messages to the top-level executor go to the output event queue (and
   the output callback, if one is set). Messages to a model that is no
   longer active are dropped. Every receiver of a message gets the same
   ``SysMessage`` object; a receiver that changes a payload must copy it
   first.

C. **Transitions.** Every affected model makes exactly one transition:

   - imminent and with a non-empty bag: ``con_trans(bag)``;
   - imminent only: ``int_trans()``;
   - receiving only: ``ext_trans(port, message)``, once per bag entry, in
     bag order.

D. **Rescheduling.** Each affected model's next request time becomes the
   instant plus the time advance of its new state (``Infinite`` makes it
   passive). If the model called ``cancel_rescheduling()`` during the
   transition, the earlier of its previous request time and that new time
   is kept instead, so a stream of inputs does not postpone its deadline.

Confluent transitions
---------------------

The default ``BehaviorModel.con_trans`` runs ``int_trans()`` and then
``ext_trans(port, message)`` for every bag entry, in bag order. A model
can override ``con_trans`` to use another order or to skip either part.

Same-time order
---------------

Within an instant, the order in which imminent models produce output, the
order of messages from different senders in a bag, and the order in which
affected models make their transitions all follow set iteration over the
models' executors. That order depends on object identity: it is not
guaranteed to be the same between runs, between Python versions or between
pyjevsim versions, and engine changes that leave every result unchanged can
change it.

A model whose results depend on that order is not reproducible. Typical
causes are several models drawing from one shared random number generator
in the same instant, or a model that treats its bag as a first-come queue.
Give each model its own generator and make a bag's effect independent of
its order (for example by sorting it) if exact reproduction matters.

The time a model sees
---------------------

``BehaviorModel.global_time`` is updated in phase D. While ``output()``,
``int_trans()``, ``ext_trans()`` or ``con_trans()`` runs, it therefore
holds the time of the model's *previous* activation (the start time for a
model that has not been activated yet), not the current instant. A model
that needs the current time should read ``SysExecutor.global_time``
(``get_global_time()``) through a reference to the executor.

This is the current behaviour and is scheduled to change in 2.4.0, when the
model-visible time will become the current instant.

When ``simulate()`` stops
-------------------------

``simulate(t)`` sets a horizon ``t`` after the current time and runs
instants while the clock is before it. The clock stops at the horizon:
events scheduled exactly at the horizon are processed by the next
``simulate()`` call, not this one.

``simulate()`` without a horizon (``Infinite``) in virtual time stops, and
marks the simulation terminated, as soon as no model is waiting to be
created and no active model has a finite request time. Queued external
events are not taken into account: they remain queued and are not
delivered, although the clock may already have moved to the first of them.
A later ``simulate()`` call with a finite horizon delivers them.

Pausing (``pause_sim``/``resume_sim``) and ``terminate_simulation`` are
checked between instants.

Uncaught messages
-----------------

Every ``SysExecutor`` registers a ``DefaultMessageCatcher`` model named
``dc``; it is always active and never schedules an event of its own.

- With ``track_uncaught=False`` (the default) a message sent on an output
  port that has no coupling is dropped.
- With ``track_uncaught=True`` such a message is routed to the
  ``DefaultMessageCatcher``'s ``uncaught`` port, where it takes part in
  the instant like any other message (the catcher's ``ext_trans`` receives
  and discards it). This is meant for debugging models whose output goes
  nowhere.
