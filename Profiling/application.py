"""UI-independent coordination of loading, analysis, and report export."""

from dataclasses import dataclass
from pathlib import Path

from .csv_input import decode_csv, parse_csv
from .profiling_common import placeholder_markers, quoted
from .structure import analyze_structure
from .completeness import analyze_completeness
from .uniqueness import analyze_uniqueness
from .distribution import analyze_distribution
from .text_reports import format_structure, format_completeness, format_uniqueness, format_distribution


@dataclass
class Dataset:
    """Loaded CSV snapshot; header interpretation is supplied separately by the UI."""
    path: Path
    size: int
    encoding: str
    delimiter: str
    records: list
    notes: list


def load_dataset(path, encoding=None, delimiter=None):
    path = Path(path).resolve()
    return dataset_from_bytes(path, path.read_bytes(), encoding, delimiter)


def dataset_from_bytes(path, raw, encoding=None, delimiter=None):
    text, encoding, notes = decode_csv(raw, encoding)
    records, delimiter, parsing_notes = parse_csv(text, delimiter)
    return Dataset(Path(path), len(raw), encoding, delimiter, records, notes + parsing_notes)


def run_analysis(dataset, header, sections, placeholders=(), use_defaults=True,
                 uniqueness=None, distribution=None):
    """Return keyed structured results for selected sections; never prompt or export.

    Columns are zero-based. distribution maps columns to statistic options;
    uniqueness is a dictionary of analyze_uniqueness options. Missing optional
    selections run only automatic whole-row matching and skip distribution.
    """
    selected = set(sections)
    if not selected or selected - {1, 2, 3, 4}:
        raise ValueError('Select one or more sections from 1 to 4.')
    header = bool(header and dataset.records)
    markers = placeholder_markers(placeholders, use_defaults)
    results = {}
    if 1 in selected:
        results[1] = analyze_structure(dataset.path, dataset.size, dataset.encoding, dataset.delimiter,
                                       dataset.records, header, dataset.notes, placeholders, use_defaults)
    if 2 in selected:
        notes = [f'Encoding: {dataset.encoding}; delimiter: {quoted(dataset.delimiter)}'] + dataset.notes
        results[2] = analyze_completeness(dataset.path, dataset.records, header, markers, notes)
    if 3 in selected:
        results[3] = analyze_uniqueness(dataset.path, dataset.records, header, markers, **(uniqueness or {}))
    if 4 in selected:
        results[4] = analyze_distribution(dataset.path, dataset.records, header, markers, distribution or {})
    return results


def format_text(results):
    formatters = {1: format_structure, 2: format_completeness, 3: format_uniqueness, 4: format_distribution}
    return '\n'.join(formatters[section](result) for section, result in sorted(results.items()))


def save_report(text, output, source, numbered=False):
    """Write exclusively; optionally try numbered names. Never overwrite the source."""
    output, source = Path(output), Path(source)
    if output.resolve() == source.resolve():
        raise ValueError('Report output must differ from the source file.')
    base, number = output, 2
    while True:
        try:
            with output.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(text)
            return output
        except FileExistsError:
            if not numbered:
                raise
            output = base.with_name(f'{base.stem}.{number}{base.suffix}')
            number += 1
