import sys
from pathlib import Path

# Ensure repository root is on sys.path for runner modules
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runner.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
