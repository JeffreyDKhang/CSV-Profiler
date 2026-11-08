"""Visual presentation of existing results. Does not run profiling calculations."""

from decimal import Decimal
import json

import streamlit as st

from Profiling.distribution import GROUPS
from Visual.configuration import SECTION_NAMES


def readable(value):
    if isinstance(value, Decimal):
        return str(value) if len(str(value)) < 24 else f'{value:.8g}'
    if isinstance(value, (list, dict, tuple, set)):
        return json.dumps(list(value) if isinstance(value, set) else value, default=str, ensure_ascii=False)
    return str(value) if value is not None else 'Unavailable'


def table(rows, key):
    """Bound rendering to 50 rows/page; full findings remain in the text export."""
    if not rows:
        st.caption('None found.')
        return
    pages = (len(rows)+49)//50
    page = st.selectbox(f'Page · {len(rows):,} findings', range(1, pages+1), key=f'result_page_{key}') if pages > 1 else 1
    st.dataframe([{k: readable(v) for k, v in row.items()} for row in rows[(page-1)*50:page*50]],
                 hide_index=True, width='stretch')


def structure(result):
    columns = st.columns(4)
    for col, label, value in zip(columns, ['File bytes', 'Columns', 'CSV records', 'Data rows'],
                                 [result['size'], result['width'], result['record_count'], result['data_row_count']]):
        col.metric(label, f'{value:,}')
    st.markdown('#### Column overview')
    table([{'Column': f'[{c["index"]+1}] {c["name"]}', 'Types': dict(c['types']),
            'Mixed types': len(c['present_types']) > 1,
            'Distinct values': c['distinct_count'] if c['distinct_count'] <= 25 else 'More than 25 distinct values',
            'Cardinality': c['cardinality']} for c in result['columns']], 'structure')
    if result['duplicate_headers']:
        st.warning('Repeated headers (case-insensitive; surrounding whitespace preserved).')
        table([{'Column positions': positions, 'Headers': [result['names'][i-1] for i in positions]}
               for positions in result['duplicate_headers']], 'headers')
    for c in result['columns']:
        with st.expander(f'[{c["index"]+1}] {c["name"]} — distinct-value frequencies'):
            if c['distinct_count'] > 25:
                st.info('More than 25 distinct values. Individual frequencies are not displayed.')
            else:
                table([{'Value': value, 'Frequency': count} for value, count in c['counts'].items()], f'frequencies_{c["index"]}')


def completeness(result):
    totals, rows = result['totals'], result['affected_rows']
    a, b, c = st.columns(3)
    a.metric('Blank records', totals['blank'])
    b.metric('Empty / whitespace cells', totals['empty'])
    c.metric('Missing-value placeholders', totals['placeholder'])
    st.caption('Empty cells and placeholders are separate. Absent fields are counted at row level only.')
    table([{'Category': label, 'Affected rows': rows[kind]} for kind, label in
           [('empty', 'Rows with empty / whitespace cells'), ('placeholder', 'Rows with placeholders'),
            ('absent', 'Rows with absent fields'), ('extra', 'Rows with extra fields')]], 'completeness_rows')
    st.caption('Row categories may overlap.')
    names = result['names']
    for kind, title in [('empty', 'Empty / whitespace cells'), ('placeholder', 'Missing-value placeholders')]:
        st.markdown(f'#### {title} by column')
        affected, unaffected = [], []
        for index, counts in enumerate(result['columns']):
            label = f'[{index+1}] ' + (names[index] if index < len(names) else 'Extra field (no header)')
            if counts[kind]:
                affected.append({'Column': label, 'Count': counts[kind]})
            else:
                unaffected.append(label)
        table(affected, f'complete_{kind}')
        with st.expander('Columns without this category'):
            st.write('; '.join(unaffected) or 'None.')
    st.markdown('#### Rows with absent or extra fields')
    table([{'Record': m['record'], 'Physical lines': f'{m["start"]}–{m["end"]}',
            'Expected fields': m['expected'], 'Actual fields': m['actual'],
            'Absent fields': m['missing'], 'Extra fields': m['extra']} for m in result['mismatches']], 'mismatches')


def uniqueness(result):
    st.markdown('#### Exact whole-row duplicates')
    st.metric('Duplicate row groups', len(result['whole_rows']))
    table([{'Record numbers': row['records'], 'Original fields': row['values']} for row in result['whole_rows']], 'whole')
    if not result['identifiers_selected']:
        st.info('Optional identifier checks were not selected.')
    for finding in result['identifiers']:
        st.markdown(f'#### [{finding["index"]+1}] {finding["name"]}')
        st.caption(f'Incomplete identifiers excluded: {finding["excluded"]}')
        if finding['exact'] is not None:
            st.markdown('**Exact normalized matches**')
            table([{'Matches': entries} for entries in finding['exact']], f'exact_{finding["index"]}')
        fuzzy = finding['fuzzy']
        if fuzzy is not None:
            st.caption(f'Similarity ≥ {fuzzy["threshold"]}/100 · {fuzzy["comparisons"]:,} pairs · limit {fuzzy["limit"]:,} · '
                       f'incomplete groups excluded: {fuzzy["excluded_group"]}')
            st.markdown('**Internal-whitespace equivalences**')
            table(fuzzy['equivalents'], f'equivalent_{finding["index"]}')
            if fuzzy['skipped']:
                st.warning('Fuzzy scan skipped: comparison limit exceeded. Increase the limit in Advanced settings or choose a grouping column.')
            else:
                st.markdown('**Fuzzy candidates — investigate before treating as duplicates**')
                table([{'Similarity': f'{c["score"]:.2f}/100', 'Group': c['group'], 'Left values / records': c['left'],
                        'Right values / records': c['right']} for c in fuzzy['candidates']], f'fuzzy_{finding["index"]}')
    st.markdown('#### Composite-key duplicates')
    composite = result['composite']
    if composite is None:
        st.caption('Not selected.')
    else:
        st.caption(f'Columns: {[i+1 for i in composite["columns"]]} · incomplete keys excluded: {composite["excluded"]}')
        table(composite['duplicates'], 'composite')


def statistic(option, value, key):
    if option in ('skewness', 'kurtosis'):
        if value['value'] is None:
            st.info(f'{option.title()}: unavailable — {value["reason"]}.')
        else:
            st.write(f'**{option.title()}:** {readable(value["value"])} · {value["classification"]}')
            if option == 'skewness':
                st.caption('Low skewness does not establish symmetry or normality.')
    elif option == 'outliers':
        st.caption(f'IQR fences: {readable(value["lower"])} to {readable(value["upper"])}; population |Z| > 3. Candidates are not necessarily errors.')
        table([{'Record': c['record'], 'Original value': c['original'], 'Criteria': c['criteria']}
               for c in value['candidates']], f'outliers_{key}')
    elif option == 'shape':
        import math
        st.write('**Shape:** ' + ('Constant distribution' if value['constant'] else f'{value["classification"]} candidate'))
        st.caption(f'Minimum frequency: {value["minimum_frequency"]} · Maximum frequency: {value["maximum_frequency"]}')
        if value['small_dataset']:
            st.warning('Small dataset (fewer than 30 values): shape estimates may be unstable.')
        st.caption('Histogram shape is exploratory and depends on binning. Chart coordinates are approximate; exact bin bounds are shown below.')
        bins = value['bins']
        coordinates = [(float(b['lower']), float(b['upper'])) for b in bins]
        if all(math.isfinite(low) and math.isfinite(high) for low, high in coordinates):
            import altair as alt
            import pandas as pd
            frame = pd.DataFrame([{'From': low, 'To': high, 'Count': b['count']} for b, (low, high) in zip(bins, coordinates)])
            chart = alt.Chart(frame).mark_bar(color='#176B60').encode(x=alt.X('From:Q', title='Value'), x2='To:Q',
                       y=alt.Y('Count:Q', title='Observations'), tooltip=['From', 'To', 'Count'])
            if value['constant']:
                st.bar_chart({'Count': [bins[0]['count']]})
            else:
                st.altair_chart(chart, width='stretch')
        else:
            st.info('Values exceed chart coordinate limits. Exact bins remain available in the table and text report.')
        table([{'From (inclusive)': str(b['lower']), 'To': str(b['upper']), 'Upper bound inclusive': b['inclusive'],
                'Count': b['count']} for b in bins], f'bins_{key}')
    elif option == 'mode':
        st.write('**Mode:** ' + (', '.join(readable(v) for v in value['values']) + f' (frequency {value["frequency"]})'
                               if value['values'] else 'No distinguished mode; every value occurs once.'))
    elif option == 'quartiles':
        table([{'Quartile': k.upper(), 'Value': readable(v)} for k, v in value.items()], f'quartiles_{key}')
    else:
        label = option.replace('_', ' ').title()
        st.write(f'**{label}:** {readable(value)}' + (' (requires at least two observations)' if value is None else ''))


def distribution(result):
    if not result['columns']:
        st.info('Skipped: no column and analysis groups were selected.')
    st.caption('On-screen long numbers are shortened for readability. Text downloads retain full Decimal precision.')
    for column in result['columns']:
        st.markdown(f'#### [{column["index"]+1}] {column["name"]}')
        st.caption(f'Valid numbers: {column["valid_count"]} / {column["eligible_count"]} non-incomplete values · '
                   f'incomplete excluded: {column["incomplete_count"]} · requires ≥95% numeric')
        if column['invalid']:
            with st.expander('Invalid numerical values and their record numbers'):
                table(column['invalid'], f'invalid_{column["index"]}')
        if not column['applicable']:
            st.warning('Statistics skipped: numeric applicability check failed.')
            continue
        if column['error']:
            st.error(f'Numerical arithmetic limit: {column["error"]}')
        for title, members in GROUPS.items():
            selected = [option for option in members if option in column['statistics']]
            if selected:
                with st.container(border=True):
                    st.markdown(f'##### {title}')
                    for option in selected:
                        statistic(option, column['statistics'][option], column['index'])


def show_results(results):
    st.subheader('4. Explore results')
    sections = sorted(results)
    tabs = st.tabs([SECTION_NAMES[i] for i in sections])
    renderers = {1: structure, 2: completeness, 3: uniqueness, 4: distribution}
    for section, tab in zip(sections, tabs):
        with tab:
            renderers[section](results[section])
