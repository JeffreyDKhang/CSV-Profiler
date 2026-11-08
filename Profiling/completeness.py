"""Read-only completeness counts for parsed CSV records."""

from collections import Counter


def analyze_completeness(path, records, header, markers, notes=()):
    """Return Section 2 counters and structured field-count mismatches; exclude headers."""
    width = len(records[0][3]) if records else 0
    names = records[0][3] if header and records else [f'Column {i + 1}' for i in range(width)]
    data = records[1:] if header else records
    markers = {m.strip().casefold() for m in markers if m.strip()}
    columns = [Counter() for _ in range(max([width] + [len(r[3]) for r in data]))]
    totals = Counter()
    affected_rows = Counter()
    mismatches = []
    for number, start, end, values in data:
        counts = Counter()
        for index, value in enumerate(values):
            kind = ('empty' if not value.strip() else
                    'placeholder' if value.strip().casefold() in markers else 'present')
            counts[kind] += 1
            columns[index][kind] += 1
        counts['absent'] = max(width - len(values), 0)
        counts['extra'] = max(len(values) - width, 0)
        counts['blank'] = int(not any(v.strip() for v in values))
        totals.update(counts)
        for kind in ('empty', 'placeholder', 'absent', 'extra'):
            affected_rows[kind] += int(counts[kind] > 0)
        if len(values) != width:
            mismatches.append(dict(record=number, start=start, end=end, actual=len(values),
                                   expected=width, missing=counts['absent'], extra=counts['extra']))
    return dict(path=path, data_row_count=len(data), width=width, names=names, markers=markers, notes=list(notes),
                columns=columns, totals=totals, affected_rows=affected_rows, mismatches=mismatches)
