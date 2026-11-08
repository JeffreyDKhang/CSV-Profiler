"""Local browser workflow. All calculations delegate to Profiling.application."""

import streamlit as st

from Profiling.application import dataset_from_bytes, run_analysis, format_text
from Visual.configuration import configure
from Visual.results import show_results
from Visual.session import file_identity, fingerprint, reset_file_state, results_current


def main():
    st.set_page_config(page_title='CSV Profiler', page_icon='📋', layout='wide')
    st.markdown('### CSV PROFILER')
    st.title('Understand your data before you clean it.')
    st.write('Inspect structure, completeness, duplicates and numerical distributions. Choose the checks that matter to you.')
    st.caption('LOCAL PROCESSING  ·  ORIGINAL FILES PRESERVED  ·  TEXT REPORT EXPORT')
    st.info('Files are processed by Python on this computer. No account or external upload service is used. '
            'Keep the launcher running while using this page; stop it with Ctrl+C when finished.')
    st.subheader('1. Select a CSV')
    uploaded = st.file_uploader('Drop your CSV here, or browse your files', type=['csv'], key='upload',
                                help='Up to 50 MB. Files are held in memory. Replace or clear the selection to start over.')
    if uploaded is None:
        reset_file_state(st.session_state, None)
        st.caption('Select a file to begin. No profiling checks run until you click Run selected analyses.')
        return
    raw = uploaded.getvalue()
    identity = file_identity(uploaded.name, raw)
    reset_file_state(st.session_state, identity)
    st.caption(f'{uploaded.name} · {len(raw):,} bytes · replace the file using the uploader above')
    st.subheader('2. Review the file settings')
    left, middle, right = st.columns(3)
    encodings = ['Automatic', 'utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'utf-32', 'cp1252']
    encoding = left.selectbox('Text encoding', encodings, key='parse_encoding')
    delimiters = {'Automatic': None, 'Comma (,)': ',', 'Semicolon (;)': ';', 'Tab': '\t', 'Pipe (|)': '|'}
    delimiter = middle.selectbox('Column separator', list(delimiters), key='parse_delimiter')
    header_choice = right.selectbox('Does the first record contain headers?', ['Yes — column labels', 'No — data starts immediately'],
                                    index=None, placeholder='Choose headers or no headers', key='parse_header')
    parse_key = fingerprint(identity, encoding, delimiter)
    if st.session_state.get('loaded_parse_key') != parse_key:
        for key in list(st.session_state):
            if key.startswith('cfg_'):
                del st.session_state[key]
        try:
            dataset = dataset_from_bytes(uploaded.name, raw, None if encoding == 'Automatic' else encoding, delimiters[delimiter])
        except (ValueError, LookupError) as error:
            st.error(f'Could not read this CSV: {error}. Try another encoding or separator, or replace the file.')
            return
        st.session_state['loaded_dataset'] = dataset
        st.session_state['loaded_parse_key'] = parse_key
    dataset = st.session_state['loaded_dataset']
    st.caption(f'Detected encoding: {dataset.encoding} · Separator: {dataset.delimiter!r} · Parsed records: {len(dataset.records):,}')
    for note in dataset.notes:
        st.warning(note)
    if not dataset.records:
        st.warning('This CSV has no records. Select another file to analyze.')
        return
    with st.expander('Preview — first 10 CSV records, including the first record', expanded=True):
        preview = dataset.records[:10]
        width = max(len(r[3]) for r in preview)
        st.dataframe([{'Record': r[0], **{f'Field {i+1}': r[3][i] if i < len(r[3]) else '(absent)' for i in range(width)}}
                      for r in preview], hide_index=True, width='stretch')
    review_key = fingerprint(parse_key, header_choice)
    if st.button('Continue to analysis options', disabled=header_choice is None, key='continue'):
        st.session_state['loaded_review_key'] = review_key
    if st.session_state.get('loaded_review_key') != review_key:
        if 'result_data' in st.session_state:
            st.warning('File settings changed. Previous results are hidden. Review the preview and continue to run again.')
        return
    header = header_choice == 'Yes — column labels'
    request, errors = configure(dataset, header)
    signature = fingerprint(review_key, request)
    for error in errors:
        st.error(error)
    if not request['sections']:
        st.caption('Select at least one section above to enable analysis.')
    if st.button('Run selected analyses', type='primary', disabled=not request['sections'] or bool(errors), key='run'):
        try:
            with st.spinner('Running your selected analyses…'):
                results = run_analysis(dataset, header, **request)
                report = format_text(results)
            st.session_state['result_data'] = results
            st.session_state['result_report'] = report
            st.session_state['result_signature'] = signature
        except (ValueError, LookupError, ArithmeticError) as error:
            st.session_state.pop('result_signature', None)
            st.error(f'Analysis could not finish: {error}. Check the settings and try again.')
    if results_current(st.session_state, signature):
        st.success('Analysis complete. Explore your results below, or change the settings and run again.')
        st.download_button('Download text report', st.session_state['result_report'],
                           file_name=uploaded.name.rsplit('.', 1)[0] + '.profile.txt', mime='text/plain', key='download')
        st.caption('The report follows your browser’s download settings. It is not automatically saved in the project Outputs folder.')
        show_results(st.session_state['result_data'])
    elif 'result_data' in st.session_state:
        st.warning('Settings changed. Previous results and download are hidden until you run the updated selection.')
