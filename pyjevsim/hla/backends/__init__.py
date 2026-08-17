"""RTI backend implementations.

Importing this package registers the always-available ``inprocess`` backend
and the optional ``pitch`` / ``portico`` backends. The optional ones
self-register but import their heavy dependency (JPype + an IEEE 1516-2010
Java RTI) lazily, so importing this package never fails even when JPype /
Java / an RTI are absent — the error surfaces only when
``create_rti("pitch", ...)`` / ``create_rti("portico", ...)`` actually tries
to boot the JVM.
"""

from . import inprocess  # noqa: F401  registers "inprocess"
from . import pitch      # noqa: F401  registers "pitch" (lazy deps)
from . import portico    # noqa: F401  registers "portico" (lazy deps)
