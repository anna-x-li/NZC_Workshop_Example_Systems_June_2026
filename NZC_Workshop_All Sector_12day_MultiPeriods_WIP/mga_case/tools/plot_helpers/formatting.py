"""Number-formatting helpers shared by legend/label drawing code."""

from math import floor, log10


def format_quantity(value):
    """Format a legend/label number: fewer decimals at larger magnitudes."""
    value = float(value)
    if abs(value) >= 100:
        return f'{value:,.0f}'
    if abs(value) >= 10:
        return f'{value:,.1f}'
    if abs(value) >= 1:
        return f'{value:,.2f}'
    return f'{value:.2g}'


def round_2sf(x):
    """Round x to 2 significant figures (used to pick clean legend reference values)."""
    if x <= 0:
        return x
    d = floor(log10(x))
    return round(x, -int(d) + 1)
