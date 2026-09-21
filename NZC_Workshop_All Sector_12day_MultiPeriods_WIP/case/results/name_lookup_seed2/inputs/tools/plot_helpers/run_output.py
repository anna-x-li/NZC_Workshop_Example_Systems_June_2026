"""Resolve how a figure should be emitted (shown inline, saved to disk, or both).

Kept generic and decoupled from any specific config file's schema — callers
(a notebook, a CLI script) pass plain values in, not a config object, so this
has no dependency on how a particular project's config.py is laid out.
"""

import os
import re


def safe_filename(name):
    """Replace characters that aren't safe in a filename (e.g. "DRI / Iron" -> "DRI_Iron")."""
    return re.sub(r'[^\w\-.]+', '_', str(name)).strip('_')


def resolve_run_output(output_mode, output_dir, quality_presets, quality):
    """
    output_mode: 'notebook' (inline only), 'files' (saved only), or 'both'.
    output_dir:  directory figures are saved into when output_mode is 'files'/'both'.
    quality_presets: {quality_name: {'dpi': int, 'format': str}}.
    quality: key into quality_presets.

    Returns (show, save_dir, dpi, file_format) — save_dir is None when nothing
    should be saved, which every plot_helpers function treats as "don't save".
    """
    if output_mode not in ('notebook', 'files', 'both'):
        raise ValueError(f"output_mode must be 'notebook', 'files', or 'both', got {output_mode!r}")

    show = output_mode in ('notebook', 'both')
    save_dir = None
    if output_mode in ('files', 'both'):
        save_dir = output_dir
        os.makedirs(save_dir, exist_ok=True)

    preset = quality_presets[quality]
    return show, save_dir, preset['dpi'], preset['format']


def save_and_or_show(fig, name, show, save_dir, dpi, file_format='png'):
    """Save fig to `{save_dir}/{name}.{file_format}` if save_dir is given, show it if
    `show`, then close it — always closing prevents unshown figures from piling
    up in memory across a large batch run.
    """
    import matplotlib.pyplot as plt

    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f'{safe_filename(name)}.{file_format}')
        fig.savefig(path, dpi=dpi, bbox_inches='tight')
        print(f'  Saved: {path}')
    if show:
        plt.show()
    plt.close(fig)
