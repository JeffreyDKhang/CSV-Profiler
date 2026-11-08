"""Section 3: exact duplicates and explicitly selected identifier comparisons."""

from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations


def normalize(value):
    return value.strip().casefold()


def similarity(left, right):
    return 50 * (SequenceMatcher(None, left, right).ratio()
                 + SequenceMatcher(None, right, left).ratio())


def analyze_uniqueness(path, records, header, markers, identifiers=(), methods=(),
                      group=None, composite=(), threshold=85, limit=100000):
    """Return structured duplicate groups and candidates; column indices are zero-based."""
    width = len(records[0][3]) if records else 0
    if not 0 <= threshold <= 100 or limit < 0:
        raise ValueError('Threshold must be 0-100; comparison limit must be nonnegative.')
    selected = list(identifiers) + list(composite) + ([] if group is None else [group])
    if any(not 0 <= i < width for i in selected):
        raise ValueError('Selected column is outside the first-record columns.')
    if composite and len(set(composite)) < 2:
        raise ValueError('Composite keys require at least two distinct columns.')
    if set(methods) - {'exact', 'fuzzy'}:
        raise ValueError('Unknown identifier comparison method.')
    data = records[1:] if header else records
    names = records[0][3] if header and records else [f'Column {i+1}' for i in range(width)]
    markers = {normalize(v) for v in markers}

    def field(record, index):
        return record[3][index] if index < len(record[3]) else ''

    def complete(value):
        return bool(normalize(value)) and normalize(value) not in markers

    def entries(items):
        return [{'record': r[0], 'value': value} for r, value in items]

    whole = defaultdict(list)
    for record in data:
        whole[tuple(record[3])].append(record[0])
    result = dict(path=path, markers=markers, whole_rows=[dict(values=list(key), records=numbers)
                  for key, numbers in whole.items() if len(numbers)>1], identifiers=[],
                  identifiers_selected=bool(identifiers and methods), composite=None)
    for index in identifiers if methods else ():
        eligible = [r for r in data if complete(field(r, index))]
        finding = dict(index=index, name=names[index], excluded=len(data)-len(eligible), exact=None, fuzzy=None)
        exact = defaultdict(list)
        for record in eligible:
            exact[normalize(field(record, index))].append((record, field(record, index)))
        if 'exact' in methods:
            finding['exact'] = [entries(items) for items in exact.values() if len(items)>1]
        if 'fuzzy' in methods:
            buckets = defaultdict(lambda: defaultdict(list))
            excluded_group = 0
            for record in eligible:
                if group is not None and not complete(field(record, group)):
                    excluded_group += 1
                    continue
                bucket = normalize(field(record, group)) if group is not None else '(all records)'
                collapsed = ' '.join(normalize(field(record, index)).split())
                buckets[bucket][collapsed].append((record, field(record, index)))
            equivalents = [dict(group=bucket, entries=entries(items)) for bucket, values in buckets.items()
                           for items in values.values() if len({normalize(v) for _, v in items})>1]
            comparisons = sum(len(values)*(len(values)-1)//2 for values in buckets.values())
            candidates = []
            if comparisons <= limit:
                for bucket, values in buckets.items():
                    for left, right in combinations(values, 2):
                        score = similarity(left, right)
                        if score >= threshold:
                            candidates.append(dict(score=score, group=bucket, left=entries(values[left]), right=entries(values[right])))
            finding['fuzzy'] = dict(threshold=threshold, limit=limit, group=group, excluded_group=excluded_group,
                                    equivalents=equivalents, comparisons=comparisons, skipped=comparisons>limit,
                                    candidates=candidates)
        result['identifiers'].append(finding)
    if composite:
        keys = defaultdict(list)
        excluded = 0
        for record in data:
            values = [field(record, i) for i in composite]
            if not all(complete(v) for v in values):
                excluded += 1
                continue
            keys[tuple(normalize(v) for v in values)].append((record, values))
        result['composite'] = dict(columns=list(composite), excluded=excluded,
                                  duplicates=[dict(key=list(key), entries=entries(items))
                                              for key, items in keys.items() if len(items)>1])
    return result
