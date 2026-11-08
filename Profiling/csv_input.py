"""Shared CSV decoding and parsing; no analysis or terminal interaction."""

import codecs
import csv
from io import StringIO


def decode_csv(raw, override=None):
    """Return decoded text, encoding label, and detection caveats."""
    if override:
        return raw.decode(override), override, ['Encoding manually selected.']
    for bom, encoding in [(codecs.BOM_UTF32_LE, 'utf-32'),
                          (codecs.BOM_UTF32_BE, 'utf-32'),
                          (codecs.BOM_UTF8, 'utf-8-sig'),
                          (codecs.BOM_UTF16_LE, 'utf-16'),
                          (codecs.BOM_UTF16_BE, 'utf-16')]:
        if raw.startswith(bom):
            return raw.decode(encoding), encoding, []
    sample = raw[:8192]
    if len(sample) >= 4:
        even = sample[0::2].count(0) / len(sample[0::2])
        odd = sample[1::2].count(0) / len(sample[1::2])
        encoding = ('utf-16-le' if odd > .4 and even < .1 else
                    'utf-16-be' if even > .4 and odd < .1 else None)
        if encoding:
            try:
                return raw.decode(encoding), encoding, ['UTF-16 inferred without BOM; verify preview.']
            except UnicodeDecodeError:
                pass
    try:
        return raw.decode('utf-8'), 'utf-8', ['No BOM; valid UTF-8, but encoding cannot be proven.']
    except UnicodeDecodeError:
        return raw.decode('cp1252'), 'cp1252', ['Windows-1252 fallback; encoding is uncertain.']


def parse_csv(text, delimiter=None):
    """Parse logical records with physical line spans; fail on malformed quotes."""
    notes = []
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:65536], delimiters=',;\t|').delimiter
            notes.append('Delimiter inferred from sample; verify preview.')
        except csv.Error:
            delimiter = ','
            notes.append('Delimiter uncertain: defaulted to comma. Override if needed.')
    reader = csv.reader(StringIO(text, newline=''), delimiter=delimiter, strict=True)
    records = []
    previous = 0
    try:
        for number, values in enumerate(reader, 1):
            records.append((number, previous + 1, reader.line_num, values))
            previous = reader.line_num
    except csv.Error as error:
        raise ValueError(f'CSV parsing failed near physical line {reader.line_num}: {error}') from error
    return records, delimiter, notes
