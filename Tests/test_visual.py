"""Optional Streamlit workflow checks; standard-library terminal tests still run alone."""

import importlib.util
import unittest
from pathlib import Path

from Profiling.application import dataset_from_bytes, run_analysis, format_text
from Visual.session import file_identity, fingerprint, reset_file_state, results_current


class VisualSessionTests(unittest.TestCase):
    def test_file_replacement_and_stale_results(self):
        identity = file_identity('x.csv', b'a\n1')
        state = {'upload': 'widget', 'file_identity': identity, 'cfg_section_1': True,
                 'loaded_dataset': object(), 'result_data': {}, 'result_signature': 'old'}
        reset_file_state(state, identity)
        self.assertIn('loaded_dataset', state)
        self.assertFalse(results_current(state, 'new'))
        reset_file_state(state, file_identity('x.csv', b'a\n2'))
        self.assertNotIn('loaded_dataset', state)
        self.assertNotIn('result_data', state)
        self.assertEqual(state['upload'], 'widget')
        self.assertNotEqual(fingerprint({'sections': [1]}), fingerprint({'sections': [2]}))


@unittest.skipUnless(importlib.util.find_spec('streamlit'), 'Install requirements-visual.txt for visual workflow tests')
class VisualWorkflowTests(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self.raw = b'name,company,salary\n A ,X,1\na,x,2\nNA,,3\nx,y,4\n'
        self.app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'visual_app.py'), default_timeout=30).run()
        self.app.file_uploader[0].set_value(('sample.csv', self.raw, 'text/csv')).run()

    def review(self):
        self.app.selectbox(key='parse_header').select('Yes — column labels').run()
        self.app.button(key='continue').click().run()

    def test_no_automatic_analysis_and_backend_parity(self):
        self.assertFalse(self.app.exception)
        self.assertNotIn('result_data', self.app.session_state)
        self.review()
        self.app.checkbox(key='cfg_section_1').check().run()
        self.app.checkbox(key='cfg_section_2').check().run()
        self.assertNotIn('result_data', self.app.session_state)
        self.app.button(key='run').click().run()
        self.assertFalse(self.app.exception)
        expected = run_analysis(dataset_from_bytes('sample.csv', self.raw), True, [1, 2])
        self.assertEqual(self.app.session_state['result_report'], format_text(expected))
        self.app.checkbox(key='cfg_section_1').uncheck().run()
        self.assertTrue(any('Settings changed' in item.value for item in self.app.warning))

    def test_uniqueness_and_distribution_are_opt_in(self):
        self.review()
        self.app.checkbox(key='cfg_section_3').check().run()
        self.app.checkbox(key='cfg_section_4').check().run()
        self.app.button(key='run').click().run()
        results = self.app.session_state['result_data']
        self.assertFalse(results[3]['identifiers_selected'])
        self.assertEqual(results[4]['columns'], [])
        self.app.multiselect(key='cfg_identifiers').set_value([0]).run()
        self.assertTrue(self.app.button(key='run').disabled)
        self.app.radio(key='cfg_method').set_value('Both').run()
        self.app.multiselect(key='cfg_distribution_columns').set_value([2]).run()
        self.app.multiselect(key='cfg_groups_2').set_value(['Central Tendency', 'Overall Distribution Shape']).run()
        self.app.button(key='run').click().run()
        self.assertFalse(self.app.exception)
        results = self.app.session_state['result_data']
        self.assertEqual(len(results[3]['identifiers'][0]['exact']), 1)
        stats = results[4]['columns'][0]['statistics']
        self.assertEqual(set(stats), {'mean', 'median', 'mode', 'shape'})
        self.assertEqual(stats['mean'], 2.5)
        expected = run_analysis(dataset_from_bytes('sample.csv', self.raw), True, [3, 4],
            uniqueness={'identifiers': [0], 'methods': ['exact', 'fuzzy'], 'group': None, 'composite': [], 'threshold': 85, 'limit': 100000},
            distribution={2: ['mean', 'median', 'mode', 'shape']})
        self.assertEqual(self.app.session_state['result_report'], format_text(expected))

    def test_numeric_gate_composite_validation_and_parse_changes(self):
        self.review()
        self.app.checkbox(key='cfg_section_3').check().run()
        self.app.multiselect(key='cfg_composite').set_value([0]).run()
        self.assertTrue(self.app.button(key='run').disabled)
        self.app.multiselect(key='cfg_composite').set_value([]).run()
        self.app.checkbox(key='cfg_section_4').check().run()
        self.app.multiselect(key='cfg_distribution_columns').set_value([0]).run()
        self.app.multiselect(key='cfg_groups_0').set_value(['Central Tendency']).run()
        self.app.button(key='run').click().run()
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.session_state['result_data'][4]['columns'][0]['applicable'])
        self.app.selectbox(key='parse_delimiter').select('Pipe (|)').run()
        self.assertTrue(any('Previous results are hidden' in item.value for item in self.app.warning))
        self.app.button(key='continue').click().run()
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.checkbox(key='cfg_section_3').value)

    def test_replacement_header_change_and_invalid_file(self):
        self.review()
        self.app.checkbox(key='cfg_section_1').check().run()
        self.app.button(key='run').click().run()
        self.app.selectbox(key='parse_header').select('No — data starts immediately').run()
        self.assertTrue(any('Previous results are hidden' in item.value for item in self.app.warning))
        self.raw = b'new\n9\n'
        self.app.file_uploader[0].set_value(('sample.csv', self.raw, 'text/csv')).run()
        self.assertNotIn('result_data', self.app.session_state)
        self.assertIsNone(self.app.selectbox(key='parse_header').value)
        self.raw = b'a,b\n"unterminated'
        self.app.file_uploader[0].set_value(('sample.csv', self.raw, 'text/csv')).run()
        self.assertTrue(self.app.error)
        self.assertFalse(self.app.exception)


if __name__ == '__main__':
    unittest.main()
