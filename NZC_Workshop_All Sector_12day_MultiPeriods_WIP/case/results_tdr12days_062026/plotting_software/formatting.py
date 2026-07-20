"""Number formatting and color-assignment helpers shared by the map plots."""

from __future__ import annotations

from math import floor, log10


def format_map_quantity(value: float) -> str:
    value = float(value)
    if abs(value) >= 100:
        return f"{value:,.0f}"
    if abs(value) >= 10:
        return f"{value:,.1f}"
    return f"{value:,.2f}"


def round_2sf(x: float) -> float:
    """Round x to 2 significant figures."""
    if x <= 0:
        return x
    d = floor(log10(x))
    return round(x, -int(d) + 1)


def legend_values(max_value: float | None, fractions=(0.25, 0.5, 1.0)) -> list[float]:
    if max_value is None or max_value <= 0:
        return []
    return [max_value * f for f in fractions]


def assign_colors(categories, cmap_name: str = "tab20", plt=None) -> dict:
    """Assign a stable color to each category using a matplotlib colormap."""
    if plt is None:
        import matplotlib.pyplot as plt
    cmap = plt.get_cmap(cmap_name)
    return {cat: cmap(i % cmap.N) for i, cat in enumerate(categories)}
