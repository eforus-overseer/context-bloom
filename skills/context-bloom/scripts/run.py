"""Use the skill's own interpreter, independent of the caller's working directory."""
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
python = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
if not python.exists():
    raise SystemExit('Context Bloom needs one-time setup. See references/setup.md in the skill directory.')
os.execv(str(python), [str(python), str(root / 'scripts/analyze.py'), *sys.argv[1:]])
