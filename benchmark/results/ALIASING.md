# Multi-Subscriber Output Aliasing

## Question

If a producer emits one mutable value (e.g. `[1, 2, 3]`) on an output port
that has **multiple downstream subscribers**, can subscriber A mutate the
value and have subscriber B observe the mutation?

## Empirical answer (`benchmark/aliasing_test.py`)

Setup: producer emits `[1, 2, 3]`; subscriber A appends `'A'`; subscriber B
appends `'B'`; we inspect the producer's reference to the original list
after both have run.

```
  pyjevsim  prod_final = [1, 2, 3, 'A', 'B']    -> ALIASED
     xdevs  prod_final = [1, 2, 3, 'A', 'B']    -> ALIASED
   pypdevs  prod_final = [1, 2, 3, 'A', 'B']    -> ALIASED
 reference  prod_final = [1, 2, 3, 'A', 'B']    -> ALIASED
```

**All four engines share the same value reference across receivers.**
None deep-copies on propagation. This is the prevailing Python-DEVS
convention — outputs are conceptually immutable; modelers who need
isolation copy on the receiver side or emit immutable types
(tuple, frozen dataclass, int).

## Why each engine looks the way it does

### xdevs (`xdevs/models.py:193-200`)
```python
def propagate(self):
    if self.host:
        ...                         # remote/RPC path: pickles values
    else:
        self.port_to.add_to_bag(self.port_from)   # adds the SOURCE port to dst's bag
```
`add_to_bag` appends the source port reference; the receiver iterates
through `port_to.values` which yields directly from the source port's
list. No copying for in-process couplings.

### pypdevs minimal (`pypdevs/minimal.py:211-215`)
```python
for outport in outbag:
    p = outbag[outport]
    for inport in outport.routing_outline:
        inport.host_DEVS.my_input.setdefault(inport, []).extend(p)
```
`extend(p)` adds value references; the per-receiver list differs but the
values inside are the same Python objects.

### Reference engine (`benchmark/engines/reference/engine.py`)
```python
for src, out in outputs:
    for dst in couplings.get(id(src), ()):
        dst._inputs.extend(out)
```
Same shape as pypdevs — by design, since the reference engine was meant to
mirror the prevailing convention.

### pyjevsim (`pyjevsim/system_executor.py:328-343`)
```python
def output_handling(self, obj, msg_deliver):
    if msg_deliver.has_contents():
        for msg in msg_deliver.get_contents():
            if isinstance(msg, list):
                for ith_msg in msg:
                    pair = (obj, ith_msg)
                    self.single_output_handling(obj, copy.deepcopy(pair))
            else:
                self.single_output_handling(obj, msg)
```

The non-list branch shares references just like the others.

The list branch *looks* like it tries to deepcopy for safety, but it is
**dead code that crashes when exercised**:

1. `pair = (obj, ith_msg)` is a tuple containing the source MODEL.
2. `copy.deepcopy(pair)` walks into the model, then through `parent` to the
   SysExecutor, which holds a `threading.Condition` (RLock).
   `TypeError: cannot pickle '_thread.RLock' object`.
3. Even if the deepcopy succeeded, `single_output_handling` calls
   `msg.get_dst()` — but `msg` would be the deepcopied **tuple**, not a
   `SysMessage`. `AttributeError`.

Confirmed empirically: feeding a list-shaped `MessageDeliverer` payload into
the engine raises `TypeError` immediately.

## Consequences for pyjevsim

- The aliasing hazard is **the same** as every other Python DEVS engine in
  the comparison set. Any model that already worked under those engines
  works the same way under pyjevsim.
- The `copy.deepcopy(pair)` call in `output_handling` provides **no safety**
  (it cannot run successfully) and **measurable cost** in the profiler when
  list-shaped outputs are eventually fixed. This satisfies plan item
  **T1.3 (Remove `copy.deepcopy` on every list-typed output)** in
  `docs/p_plan.md` — drop the call, do not replace it.

## Recommended modeler convention

Document in the README and base-class docstrings:

> Outputs are shared by reference between subscribers. Treat received
> values as immutable. If your model needs to mutate a received value,
> copy it first (`payload = list(received)` for lists, `dict(received)`
> for dicts, `dataclasses.replace(received, ...)` for dataclasses).

Same wording fits xdevs, pypdevs, and the reference engine — this is the
ecosystem convention, not a pyjevsim-specific rule.
