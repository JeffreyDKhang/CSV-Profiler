from decimal import Decimal, localcontext
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from Profiling.text_reports import statistics_text as analyze, render_distribution
from Profiling.terminal_sections import prompt_distribution
from Profiling.csv_input import parse_csv
from Tests.test_profiler import main


class DistributionTests(unittest.TestCase):
    def test_group_expansion_and_report_headings(self):
        from Profiling.distribution import OPTIONS
        records, _, _ = parse_csv('salary\n1\n2\n3\n4\n', ',')
        with redirect_stdout(StringIO()), patch('builtins.input', side_effect=['1', 'all']):
            selections = prompt_distribution(records, True)
        self.assertEqual(set(selections[0]), set(OPTIONS))
        with redirect_stdout(StringIO()), patch('builtins.input', side_effect=['1', '4']):
            selections = prompt_distribution(records, True)
        self.assertEqual(selections, {0: ['kurtosis', 'outliers']})
        report = render_distribution('x', records, True, set(), selections)
        self.assertIn('TAIL WEIGHT AND OUTLIERS', report)
        self.assertIn('kurtosis:', report)
        self.assertIn('outliers:', report)
        self.assertNotIn('CENTRAL TENDENCY', report)

    def analyze(self, values, options):
        return '\n'.join(analyze([(i+2, str(v), Decimal(str(v))) for i, v in enumerate(values)], options))

    def test_known_statistics(self):
        report = self.analyze([1, 2, 3, 4], ['mean', 'median', 'quartiles', 'iqr', 'population_variance', 'sample_variance', 'skewness', 'kurtosis'])
        for expected in ['mean: 2.5', 'median: 2.5', 'Q1=1.75; Q2=2.5; Q3=3.25',
                         'iqr: 1.50', 'population_variance: 1.25', 'sample_variance: 1.666666',
                         'Low measured skew', 'kurtosis: -1.2']:
            self.assertIn(expected, report)

    def test_precision_and_selection(self):
        with localcontext() as context:
            context.prec = 6
            report = self.analyze(['0.1', '0.2', '0.2'], ['mean'])
            self.assertEqual(context.prec, 6)
        self.assertIn('0.16666666666666666666666666666666666666666666666667', report)
        self.assertNotIn('median:', report)
        self.assertNotIn('shape:', report)

    def test_modes_small_and_constant(self):
        self.assertIn('1, 2 (frequency 2)', self.analyze([1, 1, 2, 2, 3], ['mode']))
        self.assertIn('No distinguished mode', self.analyze([1, 2, 3], ['mode']))
        report = self.analyze([7], ['sample_variance', 'sample_stddev', 'skewness', 'kurtosis', 'outliers', 'shape'])
        self.assertIn('requires two observations', report)
        self.assertIn('Outlier candidates: 0', report)
        self.assertIn('Constant distribution', report)
        self.assertIn('kurtosis: N/A', self.analyze([7]*5, ['kurtosis']))

    def test_numeric_gate_and_invalid_locations(self):
        records, _, _ = parse_csv('v\n'+'\n'.join(['+1.2e2']*19+['bad', 'NA', '" "']), ',')
        report = render_distribution('x', records, True, {'na'}, {0: ['mean']})
        self.assertIn('19/20', report)
        self.assertIn('Invalid record 21: "bad"', report)
        self.assertIn('mean: 120', report)
        records, _, _ = parse_csv('v\n'+'\n'.join(['1']*18+['NaN', 'Infinity']), ',')
        report = render_distribution('x', records, True, set(), {0: ['mean']})
        self.assertIn('Statistics skipped', report)
        self.assertNotIn('mean:', report)
        self.assertIn('invalid: 2', report)

    def test_outlier_criteria_and_skew(self):
        report = self.analyze([0]*10+[100], ['outliers', 'skewness'])
        self.assertIn('Record 12: "100"; criteria: IQR, population Z-score', report)
        self.assertIn('Right/positive skew', report)
        self.assertIn('Left/negative skew', self.analyze([0]*10+[-100], ['skewness']))

    def test_histogram(self):
        report = self.analyze(list(range(16)), ['shape'])
        self.assertIn('Uniform candidate', report)
        self.assertIn('Small dataset', report)
        self.assertIn('[11.25, 15]: 4', report)
        report = self.analyze([0]*8+[10]*8, ['shape'])
        self.assertIn('Bimodal candidate', report)
        report = self.analyze(list(range(900)), ['shape'])
        self.assertEqual(sum(line.startswith('  [') for line in report.splitlines()), 20)

    def test_empty_headerless_and_column_choices(self):
        self.assertIn('Skipped', render_distribution('x', [], False, set(), {}))
        records, _, _ = parse_csv('1,NA\n3,\n', ',')
        report = render_distribution('x', records, False, {'na'}, {0: ['mean'], 1: ['mode']})
        self.assertIn('mean: 2', report)
        self.assertIn('Statistics skipped', report)
        with self.assertRaises(ValueError):
            render_distribution('x', records, False, set(), {4: ['mean']})
        with redirect_stdout(StringIO()), patch('builtins.input', side_effect=['9', '1,2', '99', '1,3', '']):
            self.assertEqual(prompt_distribution(records, False), {0: ['mean', 'median', 'mode', 'skewness']})

    def test_cli_selection_and_skip(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.csv'
            raw = b'price,id\n1,001\n3,002\n'
            source.write_bytes(raw)
            for skip in [True, False]:
                output = Path(directory) / f'{skip}.txt'
                with redirect_stdout(StringIO()), patch('builtins.input', side_effect=[''] if skip else ['1', '1,2']):
                    self.assertEqual(main([str(source), '--sections', '4', '--header', 'yes', '--output', str(output)]), 0)
                report = output.read_text(encoding='utf-8')
                self.assertIn('SECTION 4:', report)
                self.assertNotIn('SECTION 1:', report)
                self.assertNotIn('[2] "id"', report)
                self.assertEqual('mean: 2' in report, not skip)
            self.assertEqual(source.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
