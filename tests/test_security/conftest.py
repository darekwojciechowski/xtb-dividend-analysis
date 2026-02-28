"""conftest.py for test_security — makes scripts/ importable.

Adds the project's ``scripts/`` directory to ``sys.path`` so that
``bandit_to_sarif`` and ``security_summary`` can be imported without
needing a ``sys.path.insert`` inside every test module.
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ is two levels up from this file (tests/test_security/ -> tests/ -> project root)
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
