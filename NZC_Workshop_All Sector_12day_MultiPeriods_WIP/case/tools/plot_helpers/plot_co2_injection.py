"""
Choropleth map of CO2 injection (geological storage) capacity by province.

CO2 transport between provinces is NOT modelled as a transmission link in this
model — captured CO2 is injected into per-province geological storage nodes
(CO2Injection resource_type, CO2Captured commodity). This map shows the
injection capacity of each province as a filled choropleth, which is the closest
equivalent to a "CO2 pipeline" visualization available in this model.
"""

import re
import pandas as pd
from .plot_choropleth import plot_choropleth_series

_REGION_RE = re.compile(r'Region\d+(.+?)_CO2Injection$')

# Mt/yr conversion: model capacity is in T/hr
_THR_TO_MTYR = 8760 / 1e6


def _extract_co2_injection(cap_df, cap_col='capacity'):
    """Return province → CO2 injection capacity (T/hr) from capacity DataFrame."""
    inj = cap_df[cap_df['resource_type'] == 'CO2Injection'].copy()
    if inj.empty:
        return pd.Series(dtype=float)
    def _prov(rid):
        m = _REGION_RE.search(str(rid))
        return m.group(1) if m else None
    inj['province'] = inj['resource_id'].apply(_prov)
    inj = inj.dropna(subset=['province'])
    return inj.groupby('province')[cap_col].sum()


def plot_co2_injection_map(all_cap, period_labels, gdf, gdf_outline=None,
                           cap_col='capacity', cmap_name='YlOrRd', unit='Mt/yr'):
    """
    Draw a choropleth map of CO2 geological injection capacity for each period.
    Series layout: all periods in one row, one shared title + colorbar.

    Note: interprovincial CO2 pipeline transport is not modelled — this map
    shows provincial-level CO2 storage capacity as a proxy.
    """
    prov_data = {}
    for label in period_labels:
        cap_df = all_cap.get(label, pd.DataFrame())
        if cap_df.empty or cap_col not in cap_df.columns:
            prov_data[label] = pd.Series(dtype=float)
        else:
            raw = _extract_co2_injection(cap_df, cap_col)
            prov_data[label] = raw * _THR_TO_MTYR   # convert to Mt/yr for display

    plot_choropleth_series(
        prov_data, period_labels, gdf, gdf_outline, cmap_name=cmap_name,
        suptitle='CO₂ Geological Storage Capacity by Province\n'
                '(no interprovincial CO₂ pipelines in this model)',
        cbar_label=f'CO₂ Injection Capacity ({unit})',
        warn_context='CO2 injection map',
    )
