#!/bin/sh
# Legacy shim (intentional no-op). This guard's checks were consolidated
# into guard_bash.py, which the guard-destructive.sh shim already delegates
# to — delegating here too would run the same consolidated guard several
# times per Bash call in stale sessions. This file exists only so sessions
# started before the Python port stop erroring on a missing path.
exit 0
