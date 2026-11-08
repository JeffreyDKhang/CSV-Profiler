"""Section-specific terminal configuration; analysis modules have no prompts."""

import json
from .terminal_input import select
from .distribution import GROUPS



def prompt_options(records, header):
    """Collect optional Section 3 choices; blank selections skip optional checks."""
    width = len(records[0][3]) if records else 0
    names = records[0][3] if header and records else [f'Column {i+1}' for i in range(width)]
    for i, name in enumerate(names, 1):
        print(f'  {i}: {json.dumps(name)}')
    if not width:
        return {}

    print('IDENTIFIER CHECKS (optional): selected columns are checked independently.')
    identifiers = select('Identifier columns > ', width)
    options = {'identifiers': identifiers}
    if identifiers:
        print('Selected identifiers: ' + ', '.join(names[i] for i in identifiers))
        print('COMPARISON METHOD\n  1. Exact - ignores capitalization and surrounding whitespace\n  2. Fuzzy - finds similar values\n  3. Both')
        method = select('Method > ', 3, single=True)
        options['methods'] = [(), ('exact',), ('fuzzy',), ('exact', 'fuzzy')][method[0]+1] if method else ()
        if 'fuzzy' in options['methods']:
            print('FUZZY GROUPING (optional): choose ONE column to compare only within matching groups.')
            print('Press Enter for no grouping: compare across all eligible records.')
            grouping = select('Grouping column > ', width, single=True)
            options['group'] = grouping[0] if grouping else None
    print('COMPOSITE KEY (optional): columns are compared together as one key, not independently.')
    print('Choose at least two distinct columns; example: 1,4 combines Name and Company if those are their column numbers.')
    options['composite'] = select('Composite-key columns > ', width, minimum=2)
    return options


def prompt_distribution(records, header):
    """Select columns, then separate sets of options for each column; blanks skip."""
    width = len(records[0][3]) if records else 0
    names = records[0][3] if header and records else [f'Column {i+1}' for i in range(width)]
    if not width:
        return {}
    print('Select measurable quantities; numeric identifiers may not be meaningful for statistics.')
    for i, name in enumerate(names, 1):
        print(f'  {i}: {json.dumps(name)}')

    columns = select('Section 4 columns > ', width)
    if not columns:
        return {}
    descriptions = ('mean, median, mode', 'range, quartiles, variance, standard deviation',
                    'skewness and interpretation', 'kurtosis and outlier candidates', 'histogram and shape candidates')
    selections = {}
    for column in columns:
        print(f'ANALYSIS GROUPS FOR [{column+1}] {names[column]}')
        for i, (title, description) in enumerate(zip(GROUPS, descriptions), 1):
            print(f'  {i}. {title} - {description}')
        selected = select('Groups > ', len(GROUPS), allow_all=True)
        if selected:
            selections[column] = [option for i in selected for option in list(GROUPS.values())[i]]
            print('Selected groups: ' + ', '.join(list(GROUPS)[i] for i in selected))
    return selections
