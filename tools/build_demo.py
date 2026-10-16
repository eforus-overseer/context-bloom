"""Render the public demo from explicitly synthetic inputs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/context-bloom/scripts'))
from visual import html_report

report = json.loads((ROOT / 'examples/bloom.json').read_text())
report['context']['source'] = 'synthetic demonstration · not your session'
report['advice'] = 'Synthetic demo: at 72% context usage, prepare a handoff before the next task boundary.'
page = html_report(report).replace('LOCAL FIRST · AGENT SKILL', 'SYNTHETIC DEMO · 72% EXAMPLE')
page = page.replace('Report snapshot · ', 'Synthetic demo snapshot · ')
page = page.replace('Context Bloom · formerly Text-Word-Counter', '<a href="https://github.com/eforus-overseer/context-bloom" style="color:#bcf2a1">Install Context Bloom on GitHub</a> · formerly Text-Word-Counter')
(ROOT / 'docs/index.html').write_text(page)
(ROOT / 'docs/.nojekyll').touch()
