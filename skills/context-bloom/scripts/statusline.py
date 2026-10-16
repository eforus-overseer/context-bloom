"""Fast, dependency-free Claude Code status line. Reads only supplied stdin JSON."""
import argparse
import json
import math
import sys


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def pressure(percentage, prepare=65, compact=80):
    if not (0 < prepare < compact <= 100):
        raise ValueError('thresholds must satisfy 0 < prepare < compact <= 100')
    if percentage is None:
        return 'unknown'
    if not number(percentage):
        raise ValueError('percentage must be a finite nonnegative number')
    return 'compact' if percentage >= compact else 'prepare' if percentage >= prepare else 'room'


def context_usage(payload):
    """Use host percentage first; fallback includes both input cache categories."""
    context = payload.get('context_window', {}) if isinstance(payload, dict) else {}
    if not isinstance(context, dict):
        return None
    pct = context.get('used_percentage')
    if number(pct):
        return pct
    usage, limit = context.get('current_usage'), context.get('context_window_size')
    if isinstance(usage, dict) and number(limit) and limit > 0:
        values = [usage.get(k) for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')]
        if all(number(v) for v in values):
            return 100 * sum(values) / limit
    return None


def render(percentage, prepare=65, compact=80, ascii_only=False):
    state = pressure(percentage, prepare, compact)
    if state == 'unknown':
        return 'Context Bloom (?) context unavailable'
    ratio = min(percentage, 100) / 100
    glyphs = ['.', 'o', 'O', '(O)', '((O))'] if ascii_only else ['·', '○', '◉', '●', '⬤']
    bubble = glyphs[min(4, int(ratio * 5))]
    filled = min(10, int(ratio * 10))
    bar = ('#' if ascii_only else '━') * filled + ('-' if ascii_only else '─') * (10 - filled)
    action = {'room': 'room to work', 'prepare': 'prepare handoff', 'compact': 'compact at next safe boundary'}[state]
    separator = '|' if ascii_only else '·'
    return f'{bubble} Bloom [{bar}] {percentage:.0f}% {separator} {action}'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ascii', action='store_true')
    parser.add_argument('--prepare', type=float, default=65)
    parser.add_argument('--compact', type=float, default=80)
    args = parser.parse_args(argv)
    try:
        pressure(None, args.prepare, args.compact)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        payload = json.loads(sys.stdin.read(65537))
    except (ValueError, OSError):
        payload = {}
    print(render(context_usage(payload), args.prepare, args.compact, args.ascii))


if __name__ == '__main__':
    main()
