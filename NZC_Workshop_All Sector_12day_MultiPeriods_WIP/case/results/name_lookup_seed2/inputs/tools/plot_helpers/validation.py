"""Validation helpers for per-province plotting data.

Both checks exist because a silent left-join/fillna(0) would otherwise mask
a real bug (a typo'd province name, or a value that shouldn't be negative)
as an innocuous-looking zero on the map.
"""


def warn_unmatched_provinces(data_provinces, known_provinces, context=''):
    """Print a warning for any data province name absent from the map.

    Without this, a name mismatch (typo, different romanization, a province
    added to the model but not to GEOJSON_RENAME) silently plots as zero —
    identical to an actual zero value, with no way to tell them apart.
    """
    unmatched = sorted(set(data_provinces) - set(known_provinces))
    if unmatched:
        label = f' ({context})' if context else ''
        print(f'  WARNING{label}: {len(unmatched)} province name(s) not found on the map '
              f'and will be plotted as zero: {unmatched}')


def require_non_negative(values_by_label, context='value'):
    """Raise with the offending labels if any value is negative.

    A pie wedge or circle radius can't represent a negative amount, so a
    negative value here means a genuine upstream bug (e.g. an unnetted CCS
    edge), not something to silently clip to zero.
    """
    negative = [label for label, value in values_by_label.items() if value < 0]
    if negative:
        raise ValueError(f"Negative {context}s aren't supported (can't size a "
                         f"wedge/circle by a negative amount): {negative}")
