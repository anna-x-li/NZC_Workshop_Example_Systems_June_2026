"""Choropleth map of CO2 pipeline export capacity by source province.

CO2 pipelines connect provinces to named offshore/geological storage sites
(e.g. BohaiOnshore, Erlian, Hehuai) rather than province-to-province — this
aggregates each source province's total outgoing pipeline capacity.
"""

import re
import pandas as pd
from .plot_choropleth import plot_choropleth_series

_SRC_RE         = re.compile(r'(Region\d+.+?)_to_')
_REGION_NAME_RE = re.compile(r'Region\d+(.+)')

# Mt/yr conversion: model capacity is in T/hr
_THR_TO_MTYR = 8760 / 1e6


def _co2_export_by_province(cap_df, cap_col='capacity'):
    rows = cap_df[cap_df['resource_type'] == 'OneWayTransmissionLink{CO2Captured}'].copy()
    if rows.empty:
        return pd.Series(dtype=float)

    def _src(rid):
        m = _SRC_RE.search(str(rid))
        if not m:
            return None
        mm = _REGION_NAME_RE.match(m.group(1))
        return mm.group(1) if mm else None

    rows['province'] = rows['resource_id'].apply(_src)
    return rows.dropna(subset=['province']).groupby('province')[cap_col].sum() * _THR_TO_MTYR


def plot_co2_export_map(all_cap, period_labels, gdf, gdf_outline=None,
                        cap_col='capacity', cmap_name='YlOrRd', unit='Mt/yr'):
    """Draw a choropleth of total CO2 pipeline export capacity per source province, one map per period."""
    prov_data = {lbl: _co2_export_by_province(all_cap.get(lbl, pd.DataFrame()), cap_col)
                for lbl in period_labels}

    plot_choropleth_series(
        prov_data, period_labels, gdf, gdf_outline, cmap_name=cmap_name,
        suptitle=f'CO₂ Pipeline Export Capacity by Province ({unit})\n'
                '(pipelines connect provinces to offshore/geological storage sites)',
        cbar_label=f'CO₂ Export Capacity ({unit})',
        warn_context='CO2 export map',
    )
