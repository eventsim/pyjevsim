"""Built-in RTI backend registrations.

The in-process backend is always available. Pitch, Portico, and GORTI import
their optional runtime dependencies only when a connector is created.
"""

from . import inprocess  # noqa: F401  registers "inprocess"
from . import pitch      # noqa: F401  registers "pitch" (lazy deps)
from . import portico    # noqa: F401  registers "portico" (lazy deps)
from . import gorti      # noqa: F401  registers "gorti" (lazy deps)
