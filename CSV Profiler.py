"""Terminal interface for read-only CSV profiling."""

import argparse
from Profiling.terminal_input import answer, select, parse_selection, BackToMenu, QuitSession
from pathlib import Path
import sys

from Profiling.profiling_common import quoted
from Profiling.terminal_sections import prompt_options, prompt_distribution
from Profiling.application import dataset_from_bytes, run_analysis, format_text, save_report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path', nargs='?', help='CSV path; prompts when omitted')
    parser.add_argument('--delimiter', choices=[',', ';', '|', 'tab'], help='Override detection')
    parser.add_argument('--encoding', help='Python encoding name, e.g. utf-8 or cp1252')
    parser.add_argument('--header', choices=['yes', 'no'], help='Skip interactive header confirmation')
    parser.add_argument('--sections', metavar='NUMBERS', help='Comma-separated section numbers, e.g. "1,3" (1-4)')
    parser.add_argument('--uniqueness-auto-only', action='store_true',
                        help='Section 3: only whole-row duplicates; skip optional configuration prompts')
    parser.add_argument('--fuzzy-threshold', type=int, default=85, help='Minimum fuzzy similarity, 0-100 (default: 85)')
    parser.add_argument('--fuzzy-limit', type=int, default=100000, help='Maximum fuzzy pairs per identifier (default: 100000)')
    parser.add_argument('--placeholder', action='append', default=[], help='Explicit missing marker; repeatable')
    parser.add_argument('--no-default-placeholders', action='store_true',
                        help='Disable standard placeholder exclusions; keep explicit --placeholder markers')
    parser.add_argument('--output', type=Path, help='New report path (existing files are never overwritten)')
    args = parser.parse_args(argv)
    if not 0 <= args.fuzzy_threshold <= 100:
        parser.error('--fuzzy-threshold must be between 0 and 100')
    if args.fuzzy_limit < 0:
        parser.error('--fuzzy-limit must be nonnegative')
    if args.sections is not None:
        try:
            args.sections = ','.join(str(i+1) for i in parse_selection(args.sections, 4))
        except ValueError as error:
            parser.error(str(error))
    try:
        print('CSV PROFILER - original data is preserved. Reports are saved in Input Data/Outputs unless --output is supplied.')
        print('Navigation: q = quit; back = section menu (during section configuration).')
        while True:
            try:
                if args.csv_path:
                    entered = args.csv_path
                else:
                    print('Enter a full file path or a path relative to this terminal folder.')
                    print('Example: Input Data\\messy_leads.csv (matching surrounding single or double quotes are accepted).')
                    entered = answer('CSV file path > ')
                entered = entered.strip()
                if len(entered) >= 2 and entered[0] == entered[-1] and entered[0] in ('"', "'"):
                    entered = entered[1:-1]
                if not entered:
                    print('Enter a CSV file path; it cannot be blank.')
                    continue
                path = Path(entered)
                raw = path.read_bytes()
                break
            except BackToMenu:
                print('Load a CSV first; then the section menu is available.')
            except OSError as error:
                if args.csv_path:
                    raise
                print(f'Could not open file: {error}. Check the path and try again.')
        dataset = dataset_from_bytes(path.resolve(), raw, args.encoding, '\t' if args.delimiter == 'tab' else args.delimiter)
        encoding, delimiter, notes, records = dataset.encoding, dataset.delimiter, dataset.notes, dataset.records
        print(f'Encoding: {encoding}; delimiter: {quoted(delimiter)}')
        for note in notes:
            print('Note: ' + note)
        print('First CSV record:', quoted(records[0][3]) if records else '(empty file)')
        header = args.header == 'yes'
        if records and args.header is None:
            response = ''
            print('Headers are column labels such as Name or Email. Enter y/yes or n/no; there is no default.')
            while response not in ('y', 'yes', 'n', 'no'):
                try:
                    response = answer('Does the first record contain headers? > ').lower()
                except BackToMenu:
                    print('Confirm headers first; then the section menu is available.')
                    continue
                if response not in ('y', 'yes', 'n', 'no'):
                    print('Enter y or n. Pressing Enter alone does not select an answer.')
            header = response in ('y', 'yes')
        if not records:
            header = False
            notes.append('Empty input: no records or headers.')
        while True:
            try:
                sections = args.sections
                if sections is None:
                    print('\nSECTION MENU\n  1. Data Structure\n  2. Completeness\n  3. Uniqueness\n  4. Value Distribution')
                    selected = select('Sections > ', 4, optional=False)
                    sections = ','.join(str(i+1) for i in selected)
                print('Running selected sections: ' + sections)
                options, selections = {}, {}
                if '3' in sections and not args.uniqueness_auto_only:
                    options = prompt_options(records, header)
                options.update(threshold=args.fuzzy_threshold, limit=args.fuzzy_limit)
                if '4' in sections:
                    selections = prompt_distribution(records, header)
                results = run_analysis(dataset, header, [int(v) for v in sections.split(',')],
                                       args.placeholder, not args.no_default_placeholders,
                                       uniqueness=options, distribution=selections)
                report = format_text(results)
                suffix = {'1': 'structure', '2': 'completeness', '3': 'uniqueness', '4': 'distribution'}.get(sections, 'profile')
                if args.output is None:
                    report_directory = Path(__file__).resolve().parent / 'Input Data' / 'Outputs'
                    report_directory.mkdir(parents=True, exist_ok=True)
                    output = report_directory / f'{path.stem}.{suffix}.txt'
                else:
                    output = args.output
                output = save_report(report, output, path, numbered=args.sections is None)
            except BackToMenu:
                print('Unfinished selections discarded. Returning to section menu.')
                args.sections = None
                continue
            print(f'Report saved: {output.resolve()}')
            if args.sections is not None:
                return 0
            print('Returning to section menu. Choose another section or q to quit.')
    except QuitSession:
        print('Goodbye.')
        return 0
    except (OSError, ValueError, LookupError, EOFError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nCancelled.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
