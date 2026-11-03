#!/usr/bin/env python3
"""LaunchAgent entry for Augur (com.mandrake.augur): puts augur/ on sys.path and runs the producer."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from augur.main import main  # noqa: E402

sys.exit(main(sys.argv[1:]))
