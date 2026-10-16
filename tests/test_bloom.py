import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/context-bloom/scripts'))
sys.path.insert(0, str(ROOT / 'tools'))
from analyze import NLP, analyze, handoff, load_input, main, sections
from statusline import context_usage, pressure, render
from visual import html_report
from install import install


class StatusTests(unittest.TestCase):
    def test_host_percentage_takes_priority(self):
        self.assertEqual(context_usage({'context_window': {'used_percentage': 72, 'current_usage': None}}), 72)

    def test_cache_counts_included_output_excluded(self):
        data = {'context_window': {'context_window_size': 1000, 'current_usage': {
            'input_tokens': 100, 'cache_creation_input_tokens': 200, 'cache_read_input_tokens': 300, 'output_tokens': 999}}}
        self.assertEqual(context_usage(data), 60)

    def test_missing_and_invalid_usage_is_unknown(self):
        for data in ({}, [], {'context_window': None}, {'context_window': {'used_percentage': True}},
                     {'context_window': {'used_percentage': float('nan')}},
                     {'context_window': {'used_percentage': None, 'current_usage': None}}):
            self.assertIsNone(context_usage(data))
        self.assertIn('unavailable', render(None))
        self.assertIn('0%', render(0))

    def test_bands_bubble_growth_and_over_capacity(self):
        self.assertEqual([pressure(n) for n in (0, 64, 65, 79, 80, 110)], ['room', 'room', 'prepare', 'prepare', 'compact', 'compact'])
        self.assertNotEqual(render(10)[0], render(90)[0])
        self.assertIn('110%', render(110))
        self.assertTrue(render(72, ascii_only=True).isascii())
        for args in ((0, 80), (80, 65), (65, 101), (float('nan'), 80)):
            with self.assertRaises(ValueError):
                pressure(50, *args)

    def test_malformed_stdin_gracefully_degrades(self):
        completed = subprocess.run([sys.executable, str(ROOT / 'skills/context-bloom/scripts/statusline.py')],
                                   input='not json', text=True, capture_output=True, check=True)
        self.assertIn('unavailable', completed.stdout)


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = NLP()

    def report(self):
        _, text, blocks = load_input(ROOT / 'examples/session.json', 'messages')
        return analyze(text, blocks, self.nlp, 144000, 200000)

    def test_lemmatization_stemming_stopwords_and_negation(self):
        data = self.nlp.normalize('The children are running and the dogs were playing. Do not remove files.')
        self.assertIn('child', data['lemmas'])
        self.assertIn('run', data['lemmas'])
        self.assertIn('play', data['stems'])
        self.assertNotIn('the', data['kept'])
        self.assertIn('not', data['kept'])
        self.assertIn('no', self.nlp.normalize('No cats here')['kept'])

    def test_literal_special_tokens_are_counted_as_text(self):
        self.assertGreater(self.nlp.count('<|endoftext|>'), 0)

    def test_normalized_counts_do_not_drive_context_pressure(self):
        report = self.report()
        self.assertLess(report['counts']['normalized_text_tokens'], report['counts']['raw_text_tokens'])
        self.assertEqual(report['context']['percentage'], 72)
        self.assertEqual(report['context']['state'], 'prepare')
        report = analyze('small text', sections('small text'), self.nlp)
        self.assertEqual(report['context']['state'], 'unknown')
        self.assertIsNone(report['context']['percentage'])

    def test_instructions_recent_work_and_constraints_are_protected(self):
        report = self.report()
        self.assertEqual([r['id'] for r in report['candidates']], [4, 3, 2])
        for i in (0, 4, 5, 6):
            self.assertFalse(report['blocks'][i]['candidate'])
            self.assertTrue(report['blocks'][i]['protected'])
        self.assertIn('worksheet', handoff(report))

    def test_code_blocks_keep_marker_and_line_locations(self):
        text = 'one\n\n```py\nx = 1\n\ny = 2\n```\n\n<!-- bloom:keep -->\n' + 'historical text ' * 100 + '\n\nrecent\n\nlatest'
        blocks = sections(text)
        self.assertEqual(blocks[1]['location'], 'lines 3–7')
        report = analyze(text, blocks, self.nlp)
        self.assertIn('fenced code; preserve exact syntax', report['blocks'][1]['protected'])
        self.assertIn('explicit keep marker', report['blocks'][2]['protected'])

    def test_invalid_parameters_rejected(self):
        for kwargs in ({'context_used': 3}, {'context_used': -1, 'context_limit': 4},
                       {'context_used': 1, 'context_limit': 0}, {'keep_recent': 0}):
            with self.assertRaises(ValueError):
                analyze('text', sections('text'), self.nlp, **kwargs)

    def test_html_escapes_derived_terms(self):
        report = self.report()
        report['top_stems'].append({'term': '<script>alert(1)</script>', 'count': 1})
        view = html_report(report)
        self.assertNotIn('<script>alert(1)</script>', view)
        self.assertIn('&lt;script&gt;', view)
        self.assertIn('no live session connection', view)

    def test_cli_writes_all_artifacts_without_changing_input(self):
        source = ROOT / 'examples/session.json'
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'result.json'
            with contextlib.redirect_stdout(io.StringIO()):
                main([str(source), '--format', 'messages', '--out', str(out)])
            report = json.loads(out.read_text())
            self.assertEqual(len(report['input_sha256']), 64)
            self.assertTrue(out.with_suffix('.html').exists())
            self.assertTrue(out.with_suffix('.handoff.md').exists())
        self.assertEqual(source.read_bytes(), original)

    def test_cli_rejects_input_overwrite_and_invalid_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.json'
            source.write_text('[{"role":"tool","content":[]} ]')
            with self.assertRaises(ValueError):
                load_input(source, 'messages')
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main([str(source), '--out', str(source)])
            self.assertIn('tool', source.read_text())

    def test_analysis_does_not_use_network(self):
        # Includes constructing a fresh NLP object, normalization and rendering.
        with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
            nlp = NLP('o200k_base')
            report = analyze('Children are playing.', sections('Children are playing.'), nlp)
            self.assertGreater(report['counts']['raw_text_tokens'], 0)


class InstallerTests(unittest.TestCase):
    def test_link_install_preserves_settings_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            settings = home / '.claude/settings.json'
            settings.parent.mkdir()
            settings.write_text('{"theme":"dark"}')
            with contextlib.redirect_stdout(io.StringIO()):
                install(home, ['codex', 'claude'], True)
                install(home, ['codex', 'claude'], True)
            self.assertEqual(json.loads(settings.read_text())['theme'], 'dark')
            self.assertTrue((home / '.agents/skills/context-bloom').is_symlink())
            self.assertTrue(list(settings.parent.glob('settings.context-bloom-backup-*.json')))

    def test_existing_statusline_prevents_any_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            settings = home / '.claude/settings.json'
            settings.parent.mkdir()
            original = '{"statusLine":{"command":"existing-command"}}'
            settings.write_text(original)
            with self.assertRaises(ValueError):
                install(home, ['codex', 'claude'], True)
            self.assertEqual(settings.read_text(), original)
            self.assertFalse((home / '.agents').exists())

    def test_existing_skill_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / '.agents/skills/context-bloom'
            destination.mkdir(parents=True)
            with self.assertRaises(ValueError):
                install(directory, ['codex'])


if __name__ == '__main__':
    unittest.main()
