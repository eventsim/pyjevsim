"""Opt a process out of Windows power throttling (EcoQoS).

Windows 11 may put a process that has run for a few seconds without user
interaction into EcoQoS: the scheduler prefers the efficient cores and
lowers the clock for it.  In the 2026-10 replication study a long
sequential run slowed down 4-5x after about 3 s, while a freshly spawned
process ran at full speed.  ``disable_power_throttling`` asks Windows to
leave execution speed alone for one process::

    SetProcessInformation(hProcess, ProcessPowerThrottling,
                          &PROCESS_POWER_THROTTLING_STATE{
                              Version=1,
                              ControlMask=PROCESS_POWER_THROTTLING_EXECUTION_SPEED,
                              StateMask=0},
                          sizeof(PROCESS_POWER_THROTTLING_STATE))

It never raises: on other platforms, and on Windows versions without the
information class (before Windows 10 1709), it returns ``False``.  The
module uses only the standard library, so ``benchmark/workloads/child.py``
can call it before it imports anything under test.
"""

import sys

# PROCESS_INFORMATION_CLASS value (processthreadsapi.h).
PROCESS_POWER_THROTTLING = 4
PROCESS_POWER_THROTTLING_CURRENT_VERSION = 1
PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1


def disable_power_throttling(process=None):
    """Turn off execution-speed throttling (EcoQoS) for a process.

    ``process`` is ``None`` (this process) or a ``subprocess.Popen`` child.
    Returns ``True`` when Windows accepted the request and ``False``
    otherwise (not Windows, a Windows without the information class, or
    the call failed); never raises.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class _State(ctypes.Structure):
            _fields_ = [("Version", wintypes.ULONG),
                        ("ControlMask", wintypes.ULONG),
                        ("StateMask", wintypes.ULONG)]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        fn = getattr(k32, "SetProcessInformation", None)
        if fn is None:          # Windows 7 and older
            return False
        fn.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                       wintypes.DWORD)
        fn.restype = wintypes.BOOL
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        handle = (k32.GetCurrentProcess() if process is None
                  else int(process._handle))
        state = _State(PROCESS_POWER_THROTTLING_CURRENT_VERSION,
                       PROCESS_POWER_THROTTLING_EXECUTION_SPEED, 0)
        return bool(fn(handle, PROCESS_POWER_THROTTLING,
                       ctypes.byref(state), ctypes.sizeof(state)))
    except Exception:           # noqa: BLE001 - best effort by design
        return False
