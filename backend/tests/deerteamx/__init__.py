"""DeerTeamX test package."""

import sys
from pathlib import Path

# Ensure backend root is in Python path
backend_root = str(Path(__file__).resolve().parents[2])
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)
