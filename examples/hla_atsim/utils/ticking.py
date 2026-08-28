"""Tick-boundary updates for shared AT/SIM physics objects.

The copied atsim models mutate shared physics objects inside ``output()``.
Within a DEVS cascade, imminent models can run in set-iteration order and some
models may fire more than once per tick. Direct mutation would make later
models in that tick observe a different state.

Both the standalone and HLA drivers apply two rules:

  * Each Manuever or decoy integrates physics once per ``ctx.tick``.

  * Heading and pursuit-target changes are staged as ``pending_*`` values and
    committed at the next tick boundary. Motion during tick ``t`` therefore
    uses decisions from tick ``t-1``.

The trajectory comparison script checks the resulting application-state rows.
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

        # Apply the previous tick's pursuit decision, then clear it.
        o.committed_target = getattr(o, "pending_target", None)
        o.pending_target = None

    ctx.tick = t
