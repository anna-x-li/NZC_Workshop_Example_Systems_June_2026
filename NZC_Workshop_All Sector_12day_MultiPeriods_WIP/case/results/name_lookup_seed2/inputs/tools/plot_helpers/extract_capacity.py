"""Extract and reshape capacity data into province × subtype pivot tables."""

import re
import pandas as pd
import matplotlib.pyplot as plt

_PROVINCE_PATTERN = re.compile(r'Region\d+')  # finds Region<N> anywhere
_REQUIRED_COLS     = {'commodity', 'resource_type', 'resource_id'}


def _province_from_resource_id(resource_id):
    """Return province name from resource_id (handles both standard and prefixed formats)."""
    s = str(resource_id)
    m = _PROVINCE_PATTERN.search(s)
    if not m:
        return s.split('_')[0]
    return s[m.end():].split('_')[0]


def _get_subtype(row):
    """
    Return the internal technology subtype key for one row.

    VRE, CementPlant, Steelmaking, and DRIMaking all encode their real subtype
    in the resource_id suffix rather than resource_type.
    """
    rt = row['resource_type']
    if rt == 'VRE' or rt.startswith('CementPlant') or rt in ('Steelmaking', 'DRIMaking'):
        # Strip "Region<N><Province>_" using the province name already computed
        # for this row, so this always agrees with _province_from_resource_id.
        s = str(row['resource_id'])
        m = _PROVINCE_PATTERN.search(s)
        if not m:
            return s
        prefix_len = m.end() + len(row['province']) + 1  # +1 for the separating underscore
        return s[prefix_len:]
    return rt


def extract_capacity(cap_df, commodities, cap_col='capacity',
                     exclude_resource_types=None, component_filters=None):
    """Return province × subtype pivot for the given commodities. Empty DF on any failure.

    exclude_resource_types: list of resource_type values to drop before pivoting.

    component_filters: {resource_type: substring} — for a given resource_type, only keep
                       rows whose component_id contains the substring.
                       e.g. {'Battery': 'discharge_edge'} shows only discharge capacity.
    """
    if cap_df.empty:
        return pd.DataFrame()
    if _REQUIRED_COLS - set(cap_df.columns):
        return pd.DataFrame()
    if cap_col not in cap_df.columns:
        return pd.DataFrame()

    if isinstance(commodities, str):
        commodities = [commodities]

    sub = cap_df[cap_df['commodity'].isin(commodities)].copy()
    sub = sub[~sub['resource_type'].str.contains('Transmission', na=False)]

    if exclude_resource_types:
        sub = sub[~sub['resource_type'].isin(exclude_resource_types)]

    if component_filters and 'component_id' in sub.columns:
        for rt, required_str in component_filters.items():
            is_rt   = sub['resource_type'] == rt
            matches = sub['component_id'].str.contains(required_str, na=False)
            sub = sub[~is_rt | matches]

    if sub.empty:
        return pd.DataFrame()

    sub['province'] = sub['resource_id'].apply(_province_from_resource_id)
    sub['subtype']  = sub.apply(_get_subtype, axis=1)
    return sub.groupby(['province', 'subtype'])[cap_col].sum().unstack(fill_value=0)


def build_sector_style(raw_dfs, subtype_style):
    """
    Compute shared colour palette and column ordering across all scenarios.

    Returns (categories, colors, renamed_dfs) where every DataFrame has the
    same columns in the same order — enabling a consistent legend across maps.
    """
    all_keys_ordered = [
        k for k in subtype_style
        if any(
            k in df.columns and df[k].sum() > 0
            for df in raw_dfs.values()
            if not df.empty
        )
    ]
    unknown = sorted({
        col
        for df in raw_dfs.values() if not df.empty
        for col in df.columns
        if col not in subtype_style and df[col].sum() > 0
    })
    all_keys = all_keys_ordered + unknown

    rename = {}
    colors = {}
    cmap   = plt.cm.tab20
    for i, key in enumerate(all_keys):
        if key in subtype_style:
            display, color = subtype_style[key]
        else:
            display = key
            color   = cmap(i % 20)
        rename[key]     = display
        colors[display] = color

    categories = [rename[k] for k in all_keys]

    renamed = {}
    for label, df in raw_dfs.items():
        if df.empty:
            renamed[label] = pd.DataFrame(columns=categories)
            continue
        aligned        = df.reindex(columns=all_keys, fill_value=0)
        renamed[label] = aligned.rename(columns=rename)

    return categories, colors, renamed
