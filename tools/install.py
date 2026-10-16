"""Link this checkout as a personal skill; optionally configure Claude's indicator."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import sys

SOURCE = Path(__file__).resolve().parents[1] / 'skills/context-bloom'


def install(home, targets, statusline=False):
    home = Path(home).expanduser().resolve()
    destinations = [home / ('.agents' if target == 'codex' else '.claude') / 'skills/context-bloom' for target in targets]
    # Preflight all destinations before changing either host.
    for destination in destinations:
        if destination.is_symlink() and destination.resolve() == SOURCE:
            continue
        if destination.exists() or destination.is_symlink():
            raise ValueError(f'Existing skill left untouched: {destination}')
    settings_path = home / '.claude/settings.json'
    settings, command = None, None
    if statusline:
        settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        if not isinstance(settings, dict):
            raise ValueError('Claude settings must be an object')
        command = shlex.join([sys.executable, str(SOURCE / 'scripts/statusline.py')])
        current = settings.get('statusLine')
        if current and (not isinstance(current, dict) or current.get('command') != command):
            raise ValueError('An existing Claude status line was found. Preserve it and manually compose the new command using references/integrations.md.')
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.is_symlink():
            destination.symlink_to(SOURCE, target_is_directory=True)
        print(f'Linked {destination}')
    if statusline:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        if settings_path.exists():
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = settings_path.with_name(f'settings.context-bloom-backup-{timestamp}.json')
            backup.write_bytes(settings_path.read_bytes())
            backup.chmod(0o600)
        settings['statusLine'] = {'type': 'command', 'command': command, 'padding': 1}
        temporary = settings_path.with_name('.context-bloom-settings.tmp')
        # Exclusive creation avoids overwriting an unrelated in-progress file.
        with temporary.open('x', encoding='utf-8') as stream:
            os.chmod(temporary, 0o600)
            json.dump(settings, stream, indent=2)
            stream.write('\n')
        temporary.replace(settings_path)
        print('Configured Claude status line; other settings preserved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=['codex', 'claude', 'both'], default='both')
    parser.add_argument('--home', type=Path, default=Path.home(), help='alternate home for testing')
    parser.add_argument('--statusline', action='store_true', help='configure Claude status line, refusing to replace another one')
    args = parser.parse_args()
    if args.statusline and args.target == 'codex':
        parser.error('--statusline requires claude or both')
    try:
        install(args.home, ['codex', 'claude'] if args.target == 'both' else [args.target], args.statusline)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
