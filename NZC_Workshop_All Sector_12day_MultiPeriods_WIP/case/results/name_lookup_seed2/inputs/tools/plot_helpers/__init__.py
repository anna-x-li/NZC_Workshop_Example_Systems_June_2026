"""
plot_helpers — reusable plotting and data-extraction utilities for MacroEnergy results.

Import this package from any notebook by adding the tools/ directory to sys.path:

    import sys
    from pathlib import Path
    _repo = next(p for p in [Path().resolve()] + list(Path().resolve().parents)
                 if (p / 'tools' / 'plot_helpers').exists())
    sys.path.insert(0, str(_repo / 'tools'))
    from plot_helpers import *

Quick reference
---------------
load_geodata.py         load_gdf()               — province + outline GeoDataFrames
load_data.py            load_period_data()       — capacity.csv + flows.csv
extract_capacity.py     extract_capacity()       — province × subtype pivot from capacity.csv
                        build_sector_style()     — shared colours/ordering across scenarios
extract_co2.py          extract_co2_emissions()  — national CO2 totals from flows.csv, split into
                                                   separate gross-emission and CCS/BECCS-capture
                                                   totals per key (never netted together)
plot_province_pies.py   plot_province_pies()     — draw pie-chart map for one scenario
plot_sector_maps.py     plot_sector_maps()       — orchestrate maps for all scenarios in a sector
plot_capacity_bars.py   plot_capacity_bars()     — stacked capacity bar chart
plot_co2_bar.py         plot_co2_bar()           — stacked CO2 emissions bar chart (gross emissions
                                                   up, CCS/BECCS capture down, as separate segments)
plot_numberline.py      plot_sector_numberline() — uniform pies ordered by capacity
plot_transport_flows.py plot_transport_series()  — inter-province transport arrows (any commodity)
plot_choropleth.py      plot_choropleth_series() — shared per-province choropleth map drawer
plot_co2_injection.py   plot_co2_injection_map() — CO2 injection capacity choropleth by province
plot_co2_export.py      plot_co2_export_map()    — CO2 pipeline export capacity choropleth by province
formatting.py           format_quantity()        — shared legend/label number formatting
                        round_2sf()              — round a legend reference value to 2 sig figs
validation.py           warn_unmatched_provinces() — flag data province names absent from the map
                        require_non_negative()     — guard against values that can't size a wedge/circle

All pie/circle sizes below scale radius by sqrt(value), so *area* — not
radius — is proportional to the plotted quantity (otherwise a 2x value
would look 4x bigger).

Adapting to a different model or region
-----------------------------------------
Everything here is generic to MacroEnergy.jl's capacity.csv / flows.csv output
format and its "Region<N><Name>_..." resource_id convention without code changes. 
Places to edit for different regions:
  - load_geodata.py's GEOJSON_RENAME / EXCLUDE_REGIONS (only needed if your
    geojson's region names don't already match your model's region names).
  - The GEOJSON / OUTLINE_GEOJSON paths, SECTORS, SUBTYPE_STYLE, and
    CO2_EDGE_MAP dicts, which live in the notebook itself (not in this
    package) — those are the per-model config a new run should edit.
"""

from .load_geodata          import load_gdf
from .load_data             import load_period_data
from .extract_capacity      import extract_capacity, build_sector_style
from .extract_co2           import extract_co2_emissions
from .plot_province_pies    import plot_province_pies
from .plot_sector_maps      import plot_sector_maps
from .plot_capacity_bars    import plot_capacity_bars
from .plot_co2_bar          import plot_co2_bar
from .plot_numberline       import plot_sector_numberline
from .plot_transport_flows  import plot_transport_series
from .plot_choropleth       import plot_choropleth_series
from .plot_co2_injection    import plot_co2_injection_map
from .plot_co2_export       import plot_co2_export_map

__all__ = [
    'load_gdf',
    'load_period_data',
    'extract_capacity',
    'build_sector_style',
    'extract_co2_emissions',
    'plot_province_pies',
    'plot_sector_maps',
    'plot_capacity_bars',
    'plot_co2_bar',
    'plot_sector_numberline',
    'plot_transport_series',
    'plot_choropleth_series',
    'plot_co2_injection_map',
    'plot_co2_export_map',
]
