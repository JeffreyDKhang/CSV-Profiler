"""Clickable section configuration mapped to existing backend contracts."""

import streamlit as st

from Profiling.distribution import GROUPS
from Profiling.profiling_common import DEFAULT_PLACEHOLDERS


SECTION_NAMES = {1: 'Data Structure', 2: 'Completeness', 3: 'Uniqueness', 4: 'Value Distribution'}


def column_labels(dataset, header):
    width = len(dataset.records[0][3]) if dataset.records else 0
    names = dataset.records[0][3] if header else [f'Column {i+1}' for i in range(width)]
    return {i: f'[{i+1}] {name or "(empty header)"}' for i, name in enumerate(names)}


def configure(dataset, header):
    st.subheader('3. Choose what to inspect')
    sections = []
    descriptions = ['File dimensions, headers, types and distinct values.',
                    'Separate empty cells, placeholders and field-count problems.',
                    'Exact whole-row duplicates, plus optional identifier checks.',
                    'Choose measurable quantities and statistical groups.']
    for number, (column, description) in enumerate(zip(st.columns(4), descriptions), 1):
        with column:
            with st.container(border=True):
                if st.checkbox(f'{number}. {SECTION_NAMES[number]}', key=f'cfg_section_{number}'):
                    sections.append(number)
                st.caption(description)
    labels = column_labels(dataset, header)
    uniqueness, distribution = {}, {}
    if 3 in sections:
        with st.container(border=True):
            st.markdown('#### Uniqueness options')
            st.info('Exact whole-row matching runs automatically. Everything below is optional.')
            identifiers = st.multiselect('Identifier columns', list(labels), format_func=labels.get,
                                         key='cfg_identifiers', help='Each selected column is checked independently.')
            uniqueness['identifiers'] = identifiers
            if identifiers:
                method = st.radio('Comparison method', ['Exact', 'Fuzzy', 'Both'], index=None,
                                  key='cfg_method', help='Exact ignores case and surrounding whitespace. Fuzzy finds similar values.')
                uniqueness['methods'] = {'Exact': ['exact'], 'Fuzzy': ['fuzzy'], 'Both': ['exact', 'fuzzy'], None: []}[method]
                if method in ('Fuzzy', 'Both'):
                    uniqueness['group'] = st.selectbox('Optional fuzzy grouping column', [None] + list(labels),
                        format_func=lambda i: 'No grouping — compare across records' if i is None else labels[i], key='cfg_group')
            composite = st.multiselect('Composite-key columns', list(labels), format_func=labels.get,
                                       key='cfg_composite', help='Two or more columns compared together as one key. Leave empty to skip.')
            uniqueness['composite'] = composite
    if 4 in sections:
        with st.container(border=True):
            st.markdown('#### Distribution options')
            st.caption('Choose measurable quantities, such as salary. Numeric IDs and phone numbers are usually unsuitable.')
            columns = st.multiselect('Numerical columns to inspect', list(labels), format_func=labels.get, key='cfg_distribution_columns')
            for index in columns:
                groups = st.multiselect(f'Analysis groups for {labels[index]}', list(GROUPS), key=f'cfg_groups_{index}',
                                        help='Select multiple groups. Every statistic in each selected group runs together.')
                if groups:
                    distribution[index] = [option for group in groups for option in GROUPS[group]]
            if not distribution:
                st.info('Distribution will be skipped until you choose a column and at least one analysis group.')
    with st.expander('Advanced settings — placeholders and fuzzy matching'):
        use_defaults = st.checkbox('Use standard missing-value placeholders', value=True, key='cfg_defaults')
        st.caption('Matching uses the whole field, ignores case, and ignores surrounding whitespace. Original data is preserved.')
        st.code(', '.join(sorted(DEFAULT_PLACEHOLDERS)), language=None)
        custom = st.text_area('Custom placeholders — one per line', key='cfg_custom', placeholder='TBD\nPending\nNo Data')
        threshold = st.number_input('Minimum fuzzy similarity (0–100)', min_value=0, max_value=100, value=85, step=1, key='cfg_threshold')
        limit = st.number_input('Maximum fuzzy pair comparisons per identifier', min_value=0, value=100000, step=1000, key='cfg_limit',
                                help='Above this budget the entire fuzzy scan is skipped; exact and whitespace findings remain.')
    uniqueness.update(threshold=threshold, limit=limit)
    errors = []
    if len(uniqueness.get('composite', [])) == 1:
        errors.append('Choose at least two composite-key columns, or clear the selection to skip that check.')
    if uniqueness.get('identifiers') and not uniqueness.get('methods'):
        errors.append('Choose an identifier comparison method, or clear the identifier columns.')
    return dict(sections=sections, placeholders=[v for v in custom.splitlines() if v.strip()],
                use_defaults=use_defaults, uniqueness=uniqueness, distribution=distribution), errors
