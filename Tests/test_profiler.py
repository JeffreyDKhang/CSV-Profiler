import codecs
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import importlib.util
from Profiling.text_reports import render_completeness
from Profiling.csv_input import decode_csv, parse_csv
from Profiling.structure import value_type
from Profiling.text_reports import render_report
from Profiling.profiling_common import DEFAULT_PLACEHOLDERS

spec = importlib.util.spec_from_file_location('csv_profiler', Path(__file__).resolve().parents[1] / 'CSV Profiler.py')
profiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profiler)
main = profiler.main


class StructureTests(unittest.TestCase):
    def test_encodings(self):
        text = 'name,city\nAlice,Montréal\n'
        for encoding in ['utf-8-sig', 'utf-16', 'utf-32', 'utf-16-le', 'utf-16-be', 'cp1252']:
            with self.subTest(encoding=encoding):
                self.assertEqual(decode_csv(text.encode(encoding))[0], text)
        self.assertEqual(decode_csv(codecs.BOM_UTF8 + b'a,b')[1], 'utf-8-sig')

    def test_delimiters(self):
        for delimiter in [',', ';', '\t', '|']:
            records, detected, _ = parse_csv(f'a{delimiter}b\n1{delimiter}2\n')
            self.assertEqual(detected, delimiter)
            self.assertEqual(records[1][3], ['1', '2'])

    def test_types(self):
        cases = {'00123': 'Numeric', '-001': 'Numeric', '1.5e3': 'Numeric',
                 '0': 'Numeric', 'false': 'Boolean', '  ': 'Empty/whitespace',
                 '2024-02-29': 'ISO date', '2023-02-29': 'Text',
                 '2024-01-01T12:30:00Z': 'ISO datetime'}
        for value, expected in cases.items():
            self.assertEqual(value_type(value), expected)

    def test_messy_records_and_report(self):
        records, delimiter, notes = parse_csv('Name,name, name\n"A\nB",001,true\nx,2\n\n,,\nx,2,false,extra\n', ',')
        self.assertEqual(records[1][1:3], (2, 3))
        report = render_report('sample.csv', 100, 'utf-8', delimiter, records, True, notes)
        for expected in ['Total CSV records: 6', 'Data rows: 5',
                         'Duplicate header groups (case-insensitive, whitespace preserved): 1',
                         '1: "Name", 2: "name"', 'Mixed nonempty types: No']:
            self.assertIn(expected, report)
        for moved_check in ['Blank records', 'inconsistent column counts', 'Missing fields in short records']:
            self.assertNotIn(moved_check, report)
        mixed, _, _ = parse_csv('v\n12\nhello\n', ',')
        self.assertIn('Mixed nonempty types: YES',
                      render_report('x', 0, 'utf-8', ',', mixed, True, []))

    def test_standard_placeholder_policy(self):
        records, _, _ = parse_csv('v\n NA \nN/a\nNULL\nUnknown\nNot Provided\n-\n0\nfalse\nbanana\nTBD\n', ',')
        report = render_report('x', 0, 'utf-8', ',', records, True, [])
        self.assertIn('Cardinality proportion: 4/4 = 1.000000', report)
        self.assertIn('"TBD"', report)
        report = render_report('x', 0, 'utf-8', ',', records, True, [], ['TBD'])
        self.assertIn('Cardinality proportion: 3/3 = 1.000000', report)
        report = render_report('x', 0, 'utf-8', ',', records, True, [], [], False)
        self.assertIn('Eligible values: 10', report)

    def test_25_distinct_and_all_missing(self):
        records, _, _ = parse_csv('v\n' + '\n'.join(str(i) for i in range(25)), ',')
        report = render_report('x', 0, 'utf-8', ',', records, True, [])
        self.assertIn('Distinct values: 25', report)
        self.assertIn('Frequency | Value', report)
        records, _, _ = parse_csv('v\nNULL\n" "\n', ',')
        report = render_report('x', 0, 'utf-8', ',', records, True, [])
        self.assertIn('Cardinality proportion: N/A (no eligible values)', report)

    def test_distinct_threshold_and_placeholders(self):
        records, delimiter, notes = parse_csv('v\n' + '\n'.join(str(i) for i in range(26)), ',')
        report = render_report('x', 0, 'utf-8', delimiter, records, True, notes)
        self.assertIn('More than 25 distinct values', report)
        self.assertNotIn('Frequency | Value', report)
        records, _, _ = parse_csv('v\nNA\n na \n0\nfalse\n" "\n', ',')
        report = render_report('x', 0, 'utf-8', ',', records, True, [], ['NA'])
        self.assertIn('Cardinality proportion: 2/2 = 1.000000', report)

    def test_no_header_empty_and_malformed(self):
        records, _, _ = parse_csv('1,2\n3,4', ',')
        self.assertIn('[1] "Column 1"', render_report('x', 0, 'utf-8', ',', records, False, []))
        self.assertIn('Columns (first record): 0', render_report('x', 0, 'utf-8', ',', [], False, []))
        with self.assertRaises(ValueError):
            parse_csv('a,b\n"unterminated,x', ',')

    def test_cli_and_source_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'leads.csv'
            output = Path(directory) / 'report.txt'
            original = b'name,id\nAlice,001\n'
            source.write_bytes(original)
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()), patch('builtins.input', return_value='yes'):
                self.assertEqual(main([str(source), '--sections', '1', '--output', str(output)]), 0)
                self.assertEqual(main([str(source), '--sections', '1', '--header', 'yes', '--output', str(output)]), 1)
                self.assertEqual(main([str(source), '--sections', '1', '--header', 'yes', '--output', str(source)]), 1)
            self.assertEqual(source.read_bytes(), original)
            self.assertIn('SECTION 1: DATA STRUCTURE', output.read_text(encoding='utf-8'))


class CompletenessTests(unittest.TestCase):
    def test_counts_and_locations(self):
        records, _, _ = parse_csv('a,b,c\n,,\n\n x , NA ,\nx\nx,y,z,NULL\n"a\nb",0,false\n', ',')
        report = render_completeness('x', records, True, DEFAULT_PLACEHOLDERS)
        for expected in ['Data rows evaluated: 6', 'Blank records: 2',
                         'Empty/whitespace fields: 4', 'Missing-value placeholders: 2',
                         'Records with missing/extra fields: 3',
                         'Record 3, physical lines 3-3: 0 fields; expected 3',
                         '[4] "Extra field 4 (no header)"',
                         'Rows containing empty/whitespace fields: 2',
                         'Rows containing missing-value placeholders: 2',
                         'Rows with absent fields: 2', 'Rows with extra fields: 1']:
            self.assertIn(expected, report)
        self.assertNotIn('Record 7,', report)
        self.assertNotIn('Record 4,', report)
        empty_section = report.split('EMPTY/WHITESPACE FIELDS\n', 1)[1].split('MISSING-VALUE PLACEHOLDERS\n', 1)[0]
        placeholder_section = report.split('MISSING-VALUE PLACEHOLDERS\n', 1)[1].split('ROW COMPLETENESS SUMMARY\n', 1)[0]
        self.assertIn('[2] "b": 1', empty_section)
        self.assertIn('[2] "b": 1', placeholder_section)
        self.assertIn('[3] "c": 2', empty_section)
        self.assertNotIn('[3] "c":', placeholder_section)
        self.assertNotIn('Absent fields in short records', report)
        self.assertNotIn('ABSENT FIELDS IN SHORT RECORDS', report)
        column_section = report.split('COLUMN COMPLETENESS', 1)[1].split('ROW COMPLETENESS SUMMARY', 1)[0]
        self.assertNotIn('absent', column_section.lower())

    def test_policy_headerless_empty_and_clean(self):
        records, _, _ = parse_csv('TBD,NA\nbanana,false\n', ',')
        report = render_completeness('x', records, False, {'tbd'})
        self.assertIn('Missing-value placeholders: 1', report)
        self.assertIn('Columns without this category: [2] "Column 2"', report)
        self.assertIn('Data rows evaluated: 2', report)
        for records, header in [([], False), ([(1, 1, 1, ['a'])], True)]:
            report = render_completeness('x', records, header, set())
            self.assertIn('Data rows evaluated: 0', report)
            self.assertIn('Blank records: 0', report)
        records, _, _ = parse_csv('a,b\n"","\t"\n', ',')
        # A whitespace-only CSV cell is empty even when it is not a blank line.
        report = render_completeness('x', records, True, set())
        self.assertIn('Empty/whitespace fields: 2', report)
        self.assertIn('Blank records: 1', report)

    def test_compact_summary_with_overlapping_row_categories(self):
        records, _, _ = parse_csv('a,b\n,NA\n' + 'x,y\n' * 1000, ',')
        report = render_completeness('x', records, True, {'na'})
        self.assertIn('Rows containing empty/whitespace fields: 1', report)
        self.assertIn('Rows containing missing-value placeholders: 1', report)
        self.assertIn('Records with missing/extra fields: 0', report)
        self.assertNotIn('Record 2,', report)
        self.assertLess(len(report.splitlines()), 65)

    def test_cli_section_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'leads.csv'
            original = b'a,b\nNA,\n'
            source.write_bytes(original)
            for sections in ['1', '2', '1,2']:
                output = Path(directory) / f'{sections}.txt'
                with redirect_stdout(StringIO()), patch('builtins.input', side_effect=['invalid', sections, 'q']):
                    self.assertEqual(main([str(source), '--header', 'yes', '--output', str(output)]), 0)
                report = output.read_text(encoding='utf-8')
                self.assertEqual('SECTION 1:' in report, '1' in sections)
                self.assertEqual('SECTION 2:' in report, '2' in sections)
            self.assertEqual(source.read_bytes(), original)

    def test_menu_returns_and_preserves_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'leads.csv'
            source.write_text('a,b\nNA,\n', encoding='utf-8')
            output = Path(directory) / 'report.txt'
            with redirect_stdout(StringIO()), patch('builtins.input', side_effect=['1', '2', '1', 'q']):
                self.assertEqual(main([str(source), '--header', 'yes', '--output', str(output)]), 0)
            self.assertIn('SECTION 1:', output.read_text(encoding='utf-8'))
            self.assertIn('SECTION 2:', output.with_name('report.2.txt').read_text(encoding='utf-8'))
            self.assertIn('SECTION 1:', output.with_name('report.3.txt').read_text(encoding='utf-8'))

    def test_default_report_uses_project_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input.csv'
            source.write_text('a,b\n1,2\n', encoding='utf-8')
            with patch.object(profiler, '__file__', str(root / 'CSV Profiler.py')), redirect_stdout(StringIO()):
                self.assertEqual(main([str(source), '--header', 'yes', '--sections', '1']), 0)
            report = root / 'Input Data' / 'Outputs' / 'input.structure.txt'
            self.assertIn('SECTION 1:', report.read_text(encoding='utf-8'))
            self.assertFalse((root / 'input.structure.txt').exists())


if __name__ == '__main__':
    unittest.main()
