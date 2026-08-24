"""
chip_paused.py — exit 0 if the dashboard has paused/stopped the pipeline, 1 if not.

A batch-friendly shim so chip_auto.bat can honour the Pause button without
knowing anything about the run-state format.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chip_runstate as rs  # noqa: E402

sys.exit(0 if rs.control() in ("pause", "stop") else 1)
