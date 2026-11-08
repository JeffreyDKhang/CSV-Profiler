"""Exercise the shared backend without a terminal or visual interface."""

import ast
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from Profiling.application import dataset_from_bytes, load_dataset, run_analysis, format_text, save_report
from Profiling.distribution import OPTIONS


class ApplicationTests(unittest.TestCase):
    def test_structured_results_without_terminal_or_mutation(self):
        dataset = dataset_from_bytes('leads.csv', b'name,company,salary\n A ,X,1\na,x,2\nNA,,3\nx\n')
        original = deepcopy(dataset)
        with patch('builtins.input', side_effect=AssertionError('Backend prompted')), patch('builtins.print', side_effect=AssertionError('Backend printed')):
            results = run_analysis(dataset, True, [1, 2, 3, 4],
                                   uniqueness={'identifiers': [0], 'methods': ['exact'], 'composite': [0, 1]},
                                   distribution={2: ['mean', 'quartiles']})
        self.assertEqual(dataset, original)
        self.assertEqual(results[1]['columns'][0]['distinct_count'], 3)
        self.assertEqual(results[2]['totals']['empty'], 1)
        self.assertEqual(results[2]['affected_rows']['absent'], 1)
        self.assertEqual(results[2]['mismatches'][0]['record'], 5)
        duplicate = results[3]['identifiers'][0]['exact'][0]
        self.assertEqual([entry['record'] for entry in duplicate], [2, 3])
        self.assertEqual(results[3]['composite']['excluded'], 2)
        statistics = results[4]['columns'][0]['statistics']
        self.assertEqual(statistics['mean'], Decimal(2))
        self.assertEqual(statistics['quartiles']['q1'], Decimal('1.5'))

    def test_section_selection_and_optional_defaults(self):
        dataset = dataset_from_bytes('x', b'v\n1\n1\n')
        results = run_analysis(dataset, True, [3, 4])
        self.assertEqual(set(results), {3, 4})
        self.assertEqual(results[3]['whole_rows'][0]['records'], [2, 3])
        self.assertFalse(results[3]['identifiers_selected'])
        self.assertEqual(results[4]['columns'], [])
        self.assertEqual(run_analysis(dataset, True, [2])[2]['data_row_count'], len(dataset.records)-1)
        for sections in [[], [5]]:
            with self.assertRaises(ValueError):
                run_analysis(dataset, True, sections)

    def test_structured_outliers_histogram_and_unavailable_statistics(self):
        dataset = dataset_from_bytes('x', ('v\n'+'\n'.join(['0']*10+['100'])).encode())
        column = run_analysis(dataset, True, [4], distribution={0: list(OPTIONS)})[4]['columns'][0]
        findings = column['statistics']
        candidate = findings['outliers']['candidates'][0]
        self.assertEqual(candidate['record'], 12)
        self.assertEqual(candidate['criteria'], ['IQR', 'population Z-score'])
        self.assertIsInstance(findings['skewness']['value'], Decimal)
        self.assertEqual(sum(bucket['count'] for bucket in findings['shape']['bins']), 11)
        single = dataset_from_bytes('x', b'v\n7\n')
        stats = run_analysis(single, True, [4], distribution={0: list(OPTIONS)})[4]['columns'][0]['statistics']
        self.assertIsNone(stats['sample_variance'])
        self.assertIsNone(stats['skewness']['value'])
        self.assertTrue(stats['shape']['constant'])

    def test_formatting_does_not_recalculate(self):
        dataset = dataset_from_bytes('x', b'v\n1\n2\n3\n4\n')
        results = run_analysis(dataset, True, [1, 2, 3, 4], distribution={0: list(OPTIONS)})
        with patch('Profiling.distribution.analyze_values', side_effect=AssertionError('Recalculated')):
            text = format_text(results)
        for section in [1, 2, 3, 4]:
            self.assertIn(f'SECTION {section}:', text)
        self.assertIn('mean: 2.5', text)

    def test_load_and_export_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'x.csv'
            raw = b'a,b\n1,2\n'
            source.write_bytes(raw)
            dataset = load_dataset(source)
            text = format_text(run_analysis(dataset, True, [1]))
            output = Path(directory) / 'report.txt'
            self.assertEqual(save_report(text, output, source), output)
            with self.assertRaises(FileExistsError):
                save_report(text, output, source)
            self.assertEqual(save_report(text, output, source, numbered=True).name, 'report.2.txt')
            with self.assertRaises(ValueError):
                save_report(text, source, source, numbered=True)
            self.assertEqual(source.read_bytes(), raw)

    def test_analysis_modules_do_not_depend_on_interfaces(self):
        root = Path(__file__).resolve().parents[1] / 'Profiling'
        for name in ['structure', 'completeness', 'uniqueness', 'distribution']:
            tree = ast.parse((root / f'{name}.py').read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module, {'text_reports', 'terminal_input', 'terminal_sections'})
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {'input', 'print'})
