"""Plain-text presentation of structured profiling results. No analysis or prompts."""

import json
from .profiling_common import quoted


def format_statistics(findings):
    lines = []
    for option, value in findings.items():
        if option == 'quartiles':
            lines.append(f'quartiles: Q1={value["q1"]}; Q2={value["q2"]}; Q3={value["q3"]}')
        elif option == 'mode':
            lines.append('mode: ' + (', '.join(str(v) for v in value['values']) + f' (frequency {value["frequency"]})'
                                     if value['values'] else 'No distinguished mode (all values occur once).'))
        elif option in ('skewness', 'kurtosis'):
            if value['value'] is None:
                lines.append(f'{option}: N/A ({value["reason"]})')
            else:
                suffix = ' relative to normal' if option == 'kurtosis' else ''
                lines.append(f'{option}: {value["value"]}; {value["classification"]}{suffix}')
                if option == 'skewness':
                    lines.append('Low skewness does not establish symmetry or normality.')
        elif option == 'outliers':
            lines += ['outliers: investigation candidates, not necessarily errors.',
                      f'IQR fences: {value["lower"]} to {value["upper"]}; population |Z| > 3']
            for candidate in value['candidates']:
                lines.append(f'  Record {candidate["record"]}: {json.dumps(candidate["original"])}; criteria: {", ".join(candidate["criteria"])}')
            lines.append(f'Outlier candidates: {len(value["candidates"])}')
        elif option == 'shape':
            lines += ['shape: exploratory histogram; bin count=floor(sqrt(n)), capped at 20.',
                      f'Exact minimum frequency: {value["minimum_frequency"]}; exact maximum frequency: {value["maximum_frequency"]}']
            if value['small_dataset']:
                lines.append('Small dataset (n < 30): shape estimates may be unstable.')
            largest = max(b['count'] for b in value['bins'])
            for bucket in value['bins']:
                bars = min(bucket['count'], 40) if value['constant'] else bucket['count']*40//largest
                lines.append(f'  [{bucket["lower"]}, {bucket["upper"]}{"]" if bucket["inclusive"] else ")"}: {bucket["count"]} ' + '#' * bars)
            if value['constant']:
                lines.append('Constant distribution; peak classification unavailable.')
            elif value['classification'] == 'Uniform':
                lines.append('Uniform candidate (equal bin counts).')
            else:
                lines.append(value['classification'] + ' candidate (local histogram peaks; bin-dependent).')
        elif value is None:
            lines.append(f'{option}: N/A (requires two observations)')
        else:
            lines.append(f'{option}: {value}')
    return lines


def format_distribution(result):
    from .distribution import GROUPS
    lines = ['='*76, 'SECTION 4: VALUE DISTRIBUTION', '='*76, f'Source: {result["path"]}',
             'Only explicitly selected columns/options are analyzed. Original values are preserved.',
             'Numerical calculations: Decimal, 50 significant digits; quartiles: linear interpolation.',
             'Header, absent/empty/whitespace values and configured placeholders are excluded.',
             'Placeholder markers: ' + json.dumps(sorted(result['markers']), ensure_ascii=True)]
    if not result['columns']:
        lines.append('Skipped (no column/options selected).')
    for column in result['columns']:
        lines += ['', f'[{column["index"]+1}] {json.dumps(column["name"])}', 'Selected options: ' + ', '.join(column['options']),
                  f'Valid numbers: {column["valid_count"]}; invalid: {len(column["invalid"])}; incomplete excluded: {column["incomplete_count"]}',
                  f'Applicability: {column["valid_count"]}/{column["eligible_count"]} non-incomplete values numeric (requires >=95%).']
        lines.extend(f'  Invalid record {item["record"]}: {json.dumps(item["value"])}' for item in column['invalid'])
        if not column['applicable']:
            lines.append('Statistics skipped: numeric applicability check failed.')
            continue
        for title, members in GROUPS.items():
            chosen = {option: column['statistics'][option] for option in members if option in column['statistics']}
            if chosen:
                lines += ['', title.upper(), '-'*76] + format_statistics(chosen)
        if column['error']:
            lines.append(f'Numerical analysis unavailable: Decimal arithmetic limit ({column["error"]}).')
    return '\n'.join(lines)+'\n'


def format_uniqueness(result):
    lines = ['=' * 76, 'SECTION 3: UNIQUENESS', '=' * 76, f'Source: {result["path"]}',
             'Header excluded when present. Record numbers include the header.',
             'Whole rows compare original fields exactly, including blanks and extra fields.',
             'Identifier/key checks exclude absent, empty/whitespace, and configured placeholders.',
             'Placeholder markers: ' + json.dumps(sorted(result['markers']), ensure_ascii=True),
             'Fuzzy grouping excludes incomplete group values; exact identifiers remain global.',
             'Original values are preserved. Fuzzy matches are candidates, not confirmed duplicates.',
             '', 'EXACT WHOLE-ROW DUPLICATES (AUTOMATIC)', '-' * 76,
             f'Duplicate row groups: {len(result["whole_rows"])}']
    for duplicate in result['whole_rows']:
        lines.append(f'  Records {duplicate["records"]}: {json.dumps(duplicate["values"], ensure_ascii=True)}')
    if not result['identifiers_selected']:
        lines += ['', 'IDENTIFIER CHECKS: skipped (no columns or methods selected).']
    for finding in result['identifiers']:
        lines += ['', f'IDENTIFIER [{finding["index"]+1}] {json.dumps(finding["name"])}', '-' * 76,
                  f'Excluded incomplete identifiers: {finding["excluded"]}']
        if finding['exact'] is not None:
            lines.append(f'Exact normalized duplicate groups: {len(finding["exact"])}')
            lines.extend('  ' + json.dumps(entries, ensure_ascii=True) for entries in finding['exact'])
        fuzzy = finding['fuzzy']
        if fuzzy is None:
            continue
        lines += [f'Fuzzy minimum similarity: {fuzzy["threshold"]}/100; limit: {fuzzy["limit"]}',
                  f'Grouping column: {fuzzy["group"]+1 if fuzzy["group"] is not None else "None"}',
                  f'Excluded incomplete grouping values: {fuzzy["excluded_group"]}',
                  'Internal-whitespace equivalences:']
        for equivalent in fuzzy['equivalents']:
            lines.append(f'  Group {json.dumps(equivalent["group"])}: {json.dumps(equivalent["entries"], ensure_ascii=True)}')
        if not fuzzy['equivalents']:
            lines.append('  None.')
        lines.append(f'Distinct fuzzy value-pair comparisons: {fuzzy["comparisons"]}')
        if fuzzy['skipped']:
            lines.append('Fuzzy pair scan SKIPPED: comparison limit exceeded. Increase limit or select grouping.')
            continue
        for candidate in fuzzy['candidates']:
            lines.append(f'  Candidate {candidate["score"]:.2f}/100, group {json.dumps(candidate["group"])}: '
                         f'{json.dumps(candidate["left"], ensure_ascii=True)} <-> {json.dumps(candidate["right"], ensure_ascii=True)}')
        lines.append(f'Fuzzy candidate pairs: {len(fuzzy["candidates"])}')
    lines += ['', 'COMPOSITE-KEY DUPLICATES', '-' * 76]
    composite = result['composite']
    if composite is None:
        lines.append('Skipped (no composite key selected).')
    else:
        lines += [f'Selected columns: {[i+1 for i in composite["columns"]]}',
                  f'Excluded incomplete keys: {composite["excluded"]}',
                  f'Duplicate composite-key groups: {len(composite["duplicates"])}']
        for duplicate in composite['duplicates']:
            lines.append(f'  Key {json.dumps(duplicate["key"])}: {json.dumps(duplicate["entries"], ensure_ascii=True)}')
    return '\n'.join(lines) + '\n'


def format_structure(result):
    path, size, encoding, delimiter = (result[k] for k in ('path', 'size', 'encoding', 'delimiter'))
    header, notes = result['header'], result['notes']
    names, width, markers = (result[k] for k in ('names', 'width', 'markers'))
    lines = ['=' * 76, 'SECTION 1: DATA STRUCTURE', '=' * 76,
             f'Source: {path}', '', 'FILE STRUCTURE', '-' * 76,
             f'Encoding: {encoding}', f'Delimiter: {quoted(delimiter)}',
             f'Header: {"Yes" if header else "No"}',
             'First record: ' + (quoted(result['first_record']) if result['first_record'] is not None else '(none)'),
             'Placeholder exclusions: ' + (', '.join(quoted(p) for p in sorted(markers)) or
                                         'None configured.'),
             'Placeholder matching: whole field, case-insensitive, surrounding whitespace ignored.',
             'Placeholder exclusions affect distinct counts/cardinality; raw type inference includes them.',
             'Empty and whitespace-only values are excluded from distinct counts.',
             'Distinct values compare original text exactly; no cleaning is performed.']
    lines.extend('Note: ' + note for note in notes)
    lines += ['', 'DATASET SIZE', '-' * 76, f'File size: {size:,} bytes',
              f'Columns (first record): {width}', f'Total CSV records: {result["record_count"]:,}',
              f'Data rows: {result["data_row_count"]:,}']
    lines += ['', 'COLUMN STRUCTURE', '-' * 76]
    duplicates = result['duplicate_headers']
    lines.append(f'Duplicate header groups (case-insensitive, whitespace preserved): {len(duplicates)}')
    for positions in duplicates:
        lines.append('  ' + ', '.join(f'{i}: {quoted(names[i - 1])}' for i in positions))
    if result['has_extra_fields']:
        lines.append('Note: Column profiles cover first-record columns only; extra fields are not profiled.')
    for column in result['columns']:
        index, name, types, present_types, eligible, counts = (column[k] for k in ('index', 'name', 'types', 'present_types', 'eligible', 'counts'))
        lines += ['', f'[{index + 1}] {quoted(name)}',
                  '  Types: ' + (', '.join(f'{t}={n}' for t, n in sorted(types.items())) or '(no values)'),
                  f'  Mixed nonempty types: {"YES - investigate" if len(present_types) > 1 else "No"}',
                  f'  Eligible values: {len(eligible)}']
        if eligible:
            lines.append(f'  Cardinality proportion: {len(counts)}/{len(eligible)} = {len(counts) / len(eligible):.6f}')
        else:
            lines.append('  Cardinality proportion: N/A (no eligible values)')
        if len(counts) > 25:
            lines.append('  More than 25 distinct values')
        else:
            lines += [f'  Distinct values: {len(counts)}', '  Frequency | Value', '  ----------+----------------------------------------']
            lines.extend(f'  {count:9} | {quoted(value)}' for value, count in counts.items())
    return '\n'.join(lines) + '\n'


def format_completeness(result):
    path, data_row_count, width, names, markers, notes, columns, totals, affected_rows = (result[k] for k in
        ('path', 'data_row_count', 'width', 'names', 'markers', 'notes', 'columns', 'totals', 'affected_rows'))
    mismatches = [f'  Record {m["record"]}, physical lines {m["start"]}-{m["end"]}: {m["actual"]} fields; expected {m["expected"]}; missing={m["missing"]}, extra={m["extra"]}' for m in result['mismatches']]
    lines = ['=' * 76, 'SECTION 2: COMPLETENESS', '=' * 76, f'Source: {path}',
             f'Data rows evaluated: {data_row_count} (header excluded when present)',
             f'Expected fields per record (first record): {width}',
             'Blank record: no fields, or all fields empty/whitespace-only.',
             'Empty counts cover existing cells only; absent fields are separate.',
             'Rows with absent fields have fewer fields than expected; rows with extra fields have more.',
             'Field-count differences do not identify which column was omitted.',
             'Totals include extra cells; extra columns are listed separately.',
             'Placeholder matching: whole field, case-insensitive, surrounding whitespace ignored.',
             'Placeholder markers: ' + json.dumps(sorted(markers), ensure_ascii=True),
             'Original values are preserved; no cleaning is performed.']
    lines.extend('Note: ' + note for note in notes)
    lines += ['', 'DATASET TOTALS', '-' * 76,
              f'Blank records: {totals["blank"]}',
              f'Empty/whitespace fields: {totals["empty"]}',
              f'Missing-value placeholders: {totals["placeholder"]}',
              f'Records with missing/extra fields: {len(mismatches)}',
              '', 'COLUMN COMPLETENESS', '-' * 76]
    labels = [f'[{index + 1}] {json.dumps(names[index] if index < width else f"Extra field {index + 1} (no header)", ensure_ascii=True)}'
              for index in range(len(columns))]
    for kind, title in [('empty', 'EMPTY/WHITESPACE FIELDS'),
                        ('placeholder', 'MISSING-VALUE PLACEHOLDERS')]:
        lines += ['', title, 'Columns containing this category:']
        affected = [f'  {label}: {counts[kind]}' for label, counts in zip(labels, columns) if counts[kind]]
        lines.extend(affected or ['  None.'])
        unaffected = [label for label, counts in zip(labels, columns) if not counts[kind]]
        lines.append('Columns without this category: ' + ('; '.join(unaffected) or 'None.'))
    lines += ['', 'ROW COMPLETENESS SUMMARY', '-' * 76,
              f'Rows containing empty/whitespace fields: {affected_rows["empty"]}',
              f'Rows containing missing-value placeholders: {affected_rows["placeholder"]}',
              f'Rows with absent fields: {affected_rows["absent"]}',
              f'Rows with extra fields: {affected_rows["extra"]}',
              'Row categories can overlap; absent fields are not counted as empty cells.']
    lines += ['', 'RECORDS WITH MISSING/EXTRA FIELDS', '-' * 76] + (mismatches or ['  None.'])
    return '\n'.join(lines) + '\n'


# Convenience adapters for callers that want one section directly as text.
# All calculations still happen in the structured analysis functions.
def render_report(*args, **kwargs):
    from .structure import analyze_structure
    return format_structure(analyze_structure(*args, **kwargs))


def render_completeness(*args, **kwargs):
    from .completeness import analyze_completeness
    return format_completeness(analyze_completeness(*args, **kwargs))


def render_uniqueness(*args, **kwargs):
    from .uniqueness import analyze_uniqueness
    return format_uniqueness(analyze_uniqueness(*args, **kwargs))


def render_distribution(*args, **kwargs):
    from .distribution import analyze_distribution
    return format_distribution(analyze_distribution(*args, **kwargs))


def statistics_text(values, selected):
    from .distribution import analyze_values
    return format_statistics(analyze_values(values, selected))
