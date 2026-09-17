"""Reusable helpers for plotting per-province asset data on a province map.

Input CSVs are expected in the same shape as ``co2emissions.csv``: one row
per asset/category, one column per province, values are quantities. The
asset represented doesn't matter (CO2 emissions, capacity, demand, ...) as
long as the table is shaped that way.

Typical usage::

    from province_asset_plots import plot_asset_map

    plot_asset_map("co2emissions.csv", output_path="co2_emissions_by_asset.png",
                   title="CO2 Emissions by Asset", unit_label="tonnes")

``plot_asset_map`` inspects how many assets (rows) are nonzero anywhere in
the table: with more than one, it draws a pie chart per province; with
exactly one, it draws a single-color quantity map instead.
"""

from .geodata import load_province_geodata
from .io_utils import active_assets, load_asset_table
from .maps import plot_asset_map, plot_pie_map, plot_quantity_map

__all__ = [
    "load_asset_table",
    "load_province_geodata",
    "active_assets",
    "plot_asset_map",
    "plot_pie_map",
    "plot_quantity_map",
]
