"""Section 1: UI-independent structured data structure findings."""

from collections import Counter, defaultdict
from datetime import date, datetime
import re

from .profiling_common import placeholder_markers


NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', re.ASCII)


def value_type(value):
    value = value.strip()
    if not value:
        return 'Empty/whitespace'
    if value.casefold() in ('true', 'false'):
        return 'Boolean'
    if NUMBER.fullmatch(value):
        return 'Numeric'
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        try:
            date.fromisoformat(value)
            return 'ISO date'
        except ValueError:
            pass
    if re.match(r'^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}', value):
        try:
            datetime.fromisoformat(value.replace('t', 'T'))
            return 'ISO datetime'
        except ValueError:
            pass
    return 'Text'


def analyze_structure(path, size, encoding, delimiter, records, header, notes,
                      placeholders=(), use_default_placeholders=True):
    """Return structured Section 1 findings; field values remain original strings."""
    names = records[0][3] if header and records else [f'Column {i+1}' for i in range(len(records[0][3]) if records else 0)]
    data = records[1:] if header else records
    markers = placeholder_markers(placeholders, use_default_placeholders)
    groups = defaultdict(list)
    if header:
        for index, name in enumerate(names, 1):
            groups[name.casefold()].append(index)
    columns = []
    for index, name in enumerate(names):
        values = [r[3][index] for r in data if index < len(r[3])]
        types = Counter(value_type(v) for v in values)
        eligible = [v for v in values if v.strip() and v.strip().casefold() not in markers]
        counts = Counter(eligible)
        columns.append(dict(index=index, name=name, types=types, present_types=set(types)-{'Empty/whitespace'},
                            eligible=eligible, counts=counts, distinct_count=len(counts),
                            cardinality=(len(counts)/len(eligible) if eligible else None)))
    return dict(path=path, size=size, encoding=encoding, delimiter=delimiter, first_record=records[0][3] if records else None, record_count=len(records), data_row_count=len(data),
                header=header, notes=list(notes), names=names, width=len(names), has_extra_fields=any(len(r[3])>len(names) for r in data),
                markers=markers, duplicate_headers=[v for v in groups.values() if len(v)>1], columns=columns)
