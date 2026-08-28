# Multi-subscriber output references

`benchmark/aliasing_test.py` checks what happens when one producer sends a
mutable list to two subscribers and each subscriber changes that list. The
runner includes adapters for pyjevsim, xdevs, PythonPDEVS, and the repository's
reference engine; an adapter reports an error when its optional dependency is
not installed.

Run it from the repository root:

```bash
python -m benchmark.aliasing_test
```

For pyjevsim, both subscribers receive the same message value object. Output
propagation does not create a copy for each coupling, so a change made by one
receiver can be visible to another receiver. Subscriber order is not part of
the test: the two tags may appear as either `A, B` or `B, A`.

Treat received values as immutable. If a model must change a payload, copy the
value first, for example:

```python
payload = list(msg.retrieve()[0])
```

The external-engine adapters are comparison aids, not a statement about every
version of those projects. Record their package versions and the complete
output when retaining a cross-engine result.
