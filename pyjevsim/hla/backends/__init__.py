"""Built-in RTI backend registrations.

The in-process backend is always available. Pitch and Portico import their
Java dependencies only when a connector is created.
"""

from . import inprocess  # noqa: F401  registers "inprocess"
from . import pitch      # noqa: F401  registers "pitch" (lazy deps)
from . import portico    # noqa: F401  registers "portico" (lazy deps)
