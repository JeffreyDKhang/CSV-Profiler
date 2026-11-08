import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
import tempfile
from pathlib import Path

from Profiling.uniqueness import similarity
from Profiling.text_reports import render_uniqueness
from Profiling.terminal_sections import prompt_options
from Profiling.csv_input import parse_csv
from Tests.test_profiler import main


class UniquenessTests(unittest.TestCase):
    def test_cli_fuzzy_defaults_and_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.csv'
            source.write_text('name\nJohn\nJon\n', encoding='utf-8')
            for override in [False, True]:
                output = Path(directory) / f'{override}.txt'
                args = [str(source), '--header', 'yes', '--sections', '3', '--output', str(output)]
                if override:
                    args += ['--fuzzy-threshold', '70', '--fuzzy-limit', '0']
                with redirect_stdout(StringIO()), patch('builtins.input', side_effect=['1', '2', '', '']):
                    self.assertEqual(main(args), 0)
                report = output.read_text(encoding='utf-8')
                self.assertIn('70/100; limit: 0' if override else '85/100; limit: 100000', report)
                self.assertEqual('Fuzzy pair scan SKIPPED' in report, override)

    def report(self, text, **options):
        records, _, _ = parse_csv(text, ',')
        return render_uniqueness('sample', records, True, {'na', 'null'}, **options)

    def test_automatic_only_exact_raw_rows(self):
        report = self.report('id,x\nA,1\nA,1\na,1\n A,1\nA,1,extra\n\n\n')
        self.assertIn('Duplicate row groups: 2', report)
        self.assertIn('Records [2, 3]', report)
        self.assertIn('Records [7, 8]', report)
        self.assertIn('IDENTIFIER CHECKS: skipped', report)
        self.assertIn('Skipped (no composite key selected)', report)

    def test_independent_exact_columns_and_composite(self):
        report = self.report('id,company\n A ,X\na,x\na,Y\nNA,x\n,z\nx\n',
                             identifiers=[0, 1], methods=['exact'], composite=[0, 1])
        self.assertIn('Exact normalized duplicate groups: 1', report)
        self.assertIn('Duplicate composite-key groups: 1', report)
        self.assertIn('Excluded incomplete keys: 3', report)
        self.assertIn('"record": 2', report)
        self.assertNotIn('Fuzzy candidate pairs', report)

    def test_grouping_only_affects_fuzzy(self):
        report = self.report('name,company\nJohn Smith,A\nJohn  Smith,A\nJon Smith,A\nJohn Smith,B\nJon Smith,B\nJohn Smith,NA\n',
                             identifiers=[0], methods=['exact', 'fuzzy'], group=1, threshold=80)
        self.assertIn('Excluded incomplete grouping values: 1', report)
        self.assertIn('"record": 7', report)  # Global exact check retains this record.
        self.assertIn('Internal-whitespace equivalences:', report)
        self.assertIn('Distinct fuzzy value-pair comparisons: 2', report)
        self.assertIn('Fuzzy candidate pairs: 2', report)

    def test_guard_skips_entire_scan_keeps_other_findings(self):
        report = self.report('v\na b\na  b\nab\nac\na b\n', identifiers=[0],
                             methods=['exact', 'fuzzy'], limit=2, threshold=0)
        self.assertIn('Distinct fuzzy value-pair comparisons: 3', report)
        self.assertIn('Fuzzy pair scan SKIPPED', report)
        self.assertIn('Exact normalized duplicate groups: 1', report)
        self.assertIn('Internal-whitespace equivalences:', report)
        self.assertNotIn('  Candidate ', report)
        report = self.report('v\na\nb\nc\n', identifiers=[0], methods=['fuzzy'], limit=3, threshold=0)
        self.assertIn('Fuzzy candidate pairs: 3', report)

    def test_score_preservation_and_empty(self):
        self.assertAlmostEqual(similarity('tide', 'diet'), 37.5)
        report = self.report('v\n001\n1\na-b\nab\na b\na  b\n', identifiers=[0], methods=['exact'])
        self.assertIn('Exact normalized duplicate groups: 0', report)
        self.assertIn('Duplicate row groups: 0', render_uniqueness('x', [], False, set()))
        records, _, _ = parse_csv('a\na\n', ',')
        self.assertIn('Records [1, 2]', render_uniqueness('x', records, False, set()))

    def test_prompt_skip_and_validation(self):
        records, _, _ = parse_csv('a,b\nx,y\n', ',')
        with redirect_stdout(StringIO()), patch('builtins.input', side_effect=['', '']):
            self.assertEqual(prompt_options(records, True), {'identifiers': [], 'composite': []})
        answers = ['9', '1', 'invalid', '3', '2', '1', '1,2']
        with redirect_stdout(StringIO()), patch('builtins.input', side_effect=answers):
            options = prompt_options(records, True)
        self.assertEqual(options['group'], 1)
        self.assertEqual(options['composite'], [0, 1])
        self.assertNotIn('limit', options)
        self.assertNotIn('threshold', options)

    def test_cli_auto_and_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'x.csv'
            original = b'id,company\n A ,X\na,x\n'
            source.write_bytes(original)
            for auto in [True, False]:
                output = Path(directory) / f'{auto}.txt'
                args = [str(source), '--header', 'yes', '--sections', '3', '--output', str(output)]
                if auto:
                    args.append('--uniqueness-auto-only')
                with redirect_stdout(StringIO()), patch('builtins.input', side_effect=[] if auto else ['1', '1', '1,2']):
                    self.assertEqual(main(args), 0)
                report = output.read_text(encoding='utf-8')
                self.assertIn('SECTION 3:', report)
                self.assertNotIn('SECTION 1:', report)
                self.assertEqual('Exact normalized duplicate groups: 1' in report, not auto)
            self.assertEqual(source.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
