"""RTI backend implementations.

Importing this package registers the always-available ``inprocess`` backend
and the optional ``pitch`` backend. ``pitch`` self-registers but imports its
heavy dependency (JPype + prti1516e) lazily, so importing this package never
fails even when JPype / Java / pRTI are absent — the error surfaces only when
``create_rti("pitch", ...)`` actually tries to boot the JVM.
"""

from . import inprocess  # noqa: F401  registers "inprocess"
from . import pitch      # noqa: F401  registers "pitch" (lazy deps)
