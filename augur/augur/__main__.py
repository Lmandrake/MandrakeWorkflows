"""python -m augur: run the producer in the foreground (the LaunchAgent runs bin/augurd.py)."""
import sys

from augur.main import main

sys.exit(main(sys.argv[1:]))
