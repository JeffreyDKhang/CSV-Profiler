import unittest
import tempfile
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from Profiling.terminal_input import parse_selection, answer, select, BackToMenu, QuitSession
from Tests.test_profiler import main


class TerminalInputTests(unittest.TestCase):
    def test_selection_rules(self):
        self.assertEqual(parse_selection('3, 1,1', 4), [0, 2])
        self.assertEqual(parse_selection('all', 4, allow_all=True), [0, 1, 2, 3])
        for value in ['1 3', '1;', '0', '5', '1,', '', 'all']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_selection(value, 4)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            parse_selection('1,2', 4, single=True)
        with self.assertRaisesRegex(ValueError, 'two|2'):
            parse_selection('1,1', 4, minimum=2)

    def test_navigation_and_retry(self):
        for text, exception in [('q', QuitSession), ('back', BackToMenu)]:
            with patch('builtins.input', return_value=text), self.assertRaises(exception):
                answer('> ')
        output = StringIO()
        with redirect_stdout(output), patch('builtins.input', side_effect=['1 2', '2, 1']):
            self.assertEqual(select('> ', 4), [0, 1])
        self.assertIn('commas', output.getvalue())

    def test_path_retry_back_and_quit(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.csv'
            source.write_text('a,b\n1,2\n', encoding='utf-8')
            output = Path(directory) / 'report.txt'
            responses = [str(source.with_name('missing.csv')), str(source), '', 'y', '3', 'back', '2', 'q']
            messages = StringIO()
            with redirect_stdout(messages), patch('builtins.input', side_effect=responses):
                self.assertEqual(main(['--output', str(output)]), 0)
            self.assertIn('Could not open file', messages.getvalue())
            self.assertIn('Unfinished selections discarded', messages.getvalue())
            self.assertIn('SECTION 2:', output.read_text(encoding='utf-8'))

    def test_cli_normalized_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.csv'
            source.write_text('a,b\n1,2\n', encoding='utf-8')
            output = Path(directory) / 'report.txt'
            with redirect_stdout(StringIO()):
                self.assertEqual(main([str(source), '--header', 'yes', '--sections', '2, 1,2', '--output', str(output)]), 0)
            text = output.read_text(encoding='utf-8')
            self.assertEqual(text.count('SECTION 1:'), 1)
            self.assertEqual(text.count('SECTION 2:'), 1)
