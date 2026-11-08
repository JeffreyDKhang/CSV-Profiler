"""Shared placeholder policy and safe report value formatting."""

import json


DEFAULT_PLACEHOLDERS = frozenset({
    'n/a', 'na', 'none', 'null', 'empty', '(empty)', 'missing',
    'unknown', 'unk', 'not known', 'undefined', 'not provided',
    'not specified', 'not available', 'not applicable', '-', '--', '?', '\u2014',
})


def quoted(value):
    return json.dumps(value, ensure_ascii=True)


def placeholder_markers(placeholders=(), use_defaults=True):
    markers = {p.strip().casefold() for p in placeholders if p.strip()}
    return markers | DEFAULT_PLACEHOLDERS if use_defaults else markers
