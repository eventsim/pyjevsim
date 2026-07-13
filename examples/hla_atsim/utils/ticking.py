"""Tick-boundary bookkeeping that makes the physics deterministic.

The copied atsim models mutate shared physics objects inside ``output()``.
Under DEVS cascades the *order* in which imminent models fire at one instant
is decided by ``ScheduleQueue.pop()`` set-iteration (object-id based), and
some models fire a variable number of times per tick. That makes the raw
models nondeterministic run-to-run and standalone != HLA.

We remove every intra-tick ordering dependency with two rules, applied
uniformly to both builds:

  * **Once-per-tick integration** — each Manuever / decoy integrates its
    physics exactly once per tick (guarded by ``ctx.tick``), so the number
    and order of ``output()`` calls within a tick no longer matters.

  * **Tick-boundary decision commit** — cross-model decisions that mutate a
    peer's physics object (CommandControl's heading change, TorpedoControl's
    pursuit target) are *staged* as ``pending_*`` during a tick and
    *committed* to the live object at the next tick boundary. Motion in tick
    ``t`` therefore reads decisions frozen at the end of tick ``t-1`` — the
    same 1-tick-delay discipline the detector snapshot already uses.

Both builds run identical models over identical frozen inputs, so the
trajectories are bit-for-bit equal and reproducible.
"""


def commit_tick(ctx, t):
    """Commit staged decisions from tick ``t-1`` and arm the tick counter.

    Call once per federate at the tick boundary, *before* ``step(t)``.
    """
    for o in ctx.items:
        pending_h = getattr(o, "pending_heading", None)
        if pending_h is not None:
            o.heading = pending_h
        o.pending_heading = None

        # committed_target reflects the *previous* tick's pursuit decision
        # (None when there was none); pending is then cleared.
        o.committed_target = getattr(o, "pending_target", None)
        o.pending_target = None

    ctx.tick = t
