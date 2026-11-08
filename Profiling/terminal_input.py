"""Consistent terminal selection rules and navigation."""


class BackToMenu(Exception):
    """Discard unfinished choices and return to the section menu."""


class QuitSession(Exception):
    """Exit at the user's request."""


def answer(prompt):
    value = input(prompt).strip()
    if value.lower() == 'q':
        raise QuitSession()
    if value.lower() == 'back':
        raise BackToMenu()
    return value


def parse_selection(value, maximum, minimum=1, single=False, allow_all=False):
    if allow_all and value.lower() == 'all':
        return list(range(maximum))
    if not value:
        raise ValueError('Enter a selection; this choice is required.')
    parts = value.split(',')
    if any(not part.strip().isascii() or not part.strip().isdigit() for part in parts):
        raise ValueError('Use numbers separated by commas, for example 1,3. Spaces around commas are allowed.')
    numbers = sorted(set(int(part.strip()) for part in parts))
    if any(not 1 <= number <= maximum for number in numbers):
        raise ValueError(f'Choose numbers from 1 to {maximum}.')
    if single and len(numbers) != 1:
        raise ValueError('Choose exactly one number.')
    if len(numbers) < minimum:
        raise ValueError(f'Choose at least {minimum} distinct numbers.')
    return [number-1 for number in numbers]


def select(prompt, maximum, minimum=1, single=False, allow_all=False, optional=True):
    print('Enter ' + ('one number.' if single else 'numbers separated by commas (example: 1,3). Spaces around commas are allowed.'))
    if allow_all:
        print('Enter all to select every item.')
    print('Press Enter to skip.' if optional else 'A selection is required.')
    print('Navigation: back = section menu; q = quit.')
    while True:
        value = answer(prompt)
        if not value and optional:
            return []
        try:
            return parse_selection(value, maximum, minimum, single, allow_all)
        except ValueError as error:
            print(f'Invalid selection: {error}')
