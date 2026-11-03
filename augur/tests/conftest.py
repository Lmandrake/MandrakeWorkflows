import os
import sys

AUGUR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if AUGUR_DIR not in sys.path:
    sys.path.insert(0, AUGUR_DIR)
# Run from the repo root, `augur` first resolves to the outer augur/ directory as a namespace
# package (importlib mode imports this conftest as augur.tests.conftest). Drop it so the real
# package augur/augur/ is found.
_m = sys.modules.get("augur")
if _m is not None and getattr(_m, "__file__", None) is None:
    for k in [k for k in sys.modules if k == "augur" or k.startswith("augur.")]:
        if k != __name__:
            del sys.modules[k]
