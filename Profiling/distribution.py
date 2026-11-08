"""Explicitly selected numerical distribution analyses, with Decimal arithmetic."""

from collections import Counter
from decimal import Decimal, localcontext, DecimalException
from math import isqrt
import re


OPTIONS = ('mean', 'median', 'mode', 'minimum', 'maximum', 'range', 'quartiles',
           'iqr', 'population_variance', 'population_stddev', 'sample_variance',
           'sample_stddev', 'skewness', 'kurtosis', 'outliers', 'shape')
GROUPS = {
    'Central Tendency': ('mean', 'median', 'mode'),
    'Spread and Variability': ('minimum', 'maximum', 'range', 'quartiles', 'iqr',
                               'population_variance', 'population_stddev', 'sample_variance', 'sample_stddev'),
    'Skewness and Symmetry': ('skewness',),
    'Tail Weight and Outliers': ('kurtosis', 'outliers'),
    'Overall Distribution Shape': ('shape',),
}

NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', re.ASCII)


def quantile(values, fraction):
    """Linear interpolation on sorted values at (n-1)*fraction."""
    position = (len(values) - 1) * fraction
    lower = int(position)
    return values[lower] + (values[min(lower + 1, len(values)-1)] - values[lower]) * (position-lower)


def analyze_values(values, selected):
    """Return only selected results for nonempty (record, original, Decimal) tuples."""
    with localcontext() as context:
        context.prec = 50
        ordered = sorted(v for _, _, v in values)
        n = len(ordered)
        if not n:
            return {}
        count = Decimal(n)
        mean = sum(ordered) / count
        deviations = [v - mean for v in ordered]
        m2 = sum(v*v for v in deviations) / count
        std = m2.sqrt()
        sample = m2 * count / (n-1) if n > 1 else None
        q1, q2, q3 = [quantile(ordered, Decimal(p)) for p in ('.25', '.5', '.75')]
        iqr = q3-q1
        results = {'mean': mean, 'median': q2, 'minimum': ordered[0], 'maximum': ordered[-1],
                   'range': ordered[-1]-ordered[0], 'quartiles': {'q1': q1, 'q2': q2, 'q3': q3},
                   'iqr': iqr, 'population_variance': m2, 'population_stddev': std,
                   'sample_variance': sample,
                   'sample_stddev': sample.sqrt() if sample is not None else None}
        findings = {}
        for option in selected:
            if option in results:
                findings[option] = results[option]
            elif option == 'mode':
                frequencies = Counter(ordered)
                highest = max(frequencies.values())
                modes = [v for v, frequency in frequencies.items() if frequency == highest]
                findings['mode'] = dict(values=modes if highest > 1 else [], frequency=highest)
            elif option == 'skewness':
                if n < 3 or not m2:
                    findings['skewness'] = dict(value=None, reason='requires three nonconstant observations')
                else:
                    m3 = sum(v**3 for v in deviations) / count
                    skew = (count*(n-1)).sqrt() / (n-2) * m3 / (m2*std)
                    label = ('Right/positive skew' if skew > Decimal('.5') else
                             'Left/negative skew' if skew < Decimal('-.5') else 'Low measured skew')
                    findings['skewness'] = dict(value=skew, classification=label)
            elif option == 'kurtosis':
                if n < 4 or not m2:
                    findings['kurtosis'] = dict(value=None, reason='requires four nonconstant observations')
                else:
                    m4 = sum(v**4 for v in deviations) / count
                    excess = Decimal(n-1) / ((n-2)*(n-3)) * ((n+1)*(m4/(m2*m2)-3)+6)
                    label = ('Leptokurtic' if excess > 0 else 'Platykurtic' if excess < 0 else 'Zero excess kurtosis')
                    findings['kurtosis'] = dict(value=excess, classification=label)
            elif option == 'outliers':
                lower, upper = q1-Decimal('1.5')*iqr, q3+Decimal('1.5')*iqr
                candidates = []
                for record, original, value in values:
                    reasons = []
                    if value < q1-Decimal('1.5')*iqr or value > q3+Decimal('1.5')*iqr:
                        reasons.append('IQR')
                    if std and abs((value-mean)/std) > 3:
                        reasons.append('population Z-score')
                    if reasons:
                        candidates.append(dict(record=record, original=original, value=value, criteria=reasons))
                findings['outliers'] = dict(lower=lower, upper=upper, candidates=candidates)
            elif option == 'shape':
                bins = min(20, max(1, isqrt(n)))
                low, high = ordered[0], ordered[-1]
                shape = dict(minimum_frequency=ordered.count(low), maximum_frequency=ordered.count(high),
                             small_dataset=n<30, constant=low==high, bins=[], classification=None)
                findings['shape'] = shape
                if low == high:
                    shape['bins'] = [dict(lower=low, upper=high, count=n, inclusive=True)]
                    continue
                step = (high-low)/bins
                counts = [0]*bins
                for value in ordered:
                    counts[min(bins-1, int((value-low)/step))] += 1
                for i, frequency in enumerate(counts):
                    end = high if i == bins-1 else low+step*(i+1)
                    shape['bins'].append(dict(lower=low+step*i, upper=end, count=frequency, inclusive=i==bins-1))
                if len(set(counts)) == 1:
                    shape['classification'] = 'Uniform'
                else:
                    # Collapse adjacent equal-height bins before counting local peaks.
                    runs = []
                    for frequency in counts:
                        if not runs or runs[-1] != frequency:
                            runs.append(frequency)
                    peaks = sum(v > 0 and (i == 0 or v > runs[i-1]) and
                                (i == len(runs)-1 or v > runs[i+1]) for i, v in enumerate(runs))
                    shape['classification'] = 'Unimodal' if peaks == 1 else 'Bimodal' if peaks == 2 else 'Multimodal'
        return findings




def analyze_distribution(path, records, header, markers, selections):
    """selections maps zero-based columns to explicitly selected option names."""
    width = len(records[0][3]) if records else 0
    if any(not 0 <= i < width for i in selections):
        raise ValueError('Distribution column outside first-record columns.')
    if any(set(options)-set(OPTIONS) for options in selections.values()):
        raise ValueError('Unknown distribution option.')
    names = records[0][3] if header and records else [f'Column {i+1}' for i in range(width)]
    data = records[1:] if header else records
    markers = {v.strip().casefold() for v in markers}
    columns = []
    for index, options in selections.items():
        if not options:
            continue
        column = dict(index=index, name=names[index], options=list(options), statistics={}, error=None)
        columns.append(column)
        valid, invalid = [], []
        incomplete = 0
        for record in data:
            raw = record[3][index] if index < len(record[3]) else ''
            value = raw.strip()
            if not value or value.casefold() in markers:
                incomplete += 1
            elif NUMBER.fullmatch(value):
                try:
                    number = Decimal(value)
                    if not number.is_finite():
                        raise ValueError()
                    valid.append((record[0], raw, number))
                except (DecimalException, ValueError):
                    invalid.append((record[0], raw))
            else:
                invalid.append((record[0], raw))
        total = len(valid) + len(invalid)
        column.update(valid_count=len(valid), invalid=[dict(record=r, value=v) for r, v in invalid],
                      incomplete_count=incomplete, eligible_count=total,
                      applicable=bool(total and len(valid)*100 >= total*95))
        if not column['applicable']:
            continue
        try:
            column['statistics'] = analyze_values(valid, list(dict.fromkeys(options)))
        except DecimalException as error:
            column['error'] = type(error).__name__
    return dict(path=path, markers=markers, columns=columns)
