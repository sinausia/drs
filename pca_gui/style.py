"""Figure style (Nature-type journals) and colour palettes.

Change the colours here and every figure follows.
"""
import functools
import logging

import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

# Font fallback warnings (e.g. Arial missing on Linux) are noise for users
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

# ---- Nature style ----
# Single column ~89 mm, double column ~183 mm. Sans-serif, ~7 pt body text.
MM = 1 / 25.4
W_SINGLE = 89 * MM
W_DOUBLE = 183 * MM

INK = '#222222'
MUTED = '#6b6b6b'

NATURE_RC = {
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 7,
    'axes.labelsize': 8,
    'axes.titlesize': 8,
    'axes.titleweight': 'normal',
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 6.5,
    'axes.linewidth': 0.75,
    'axes.edgecolor': INK,
    'axes.labelcolor': INK,
    'xtick.color': INK,
    'ytick.color': INK,
    'text.color': INK,
    'lines.linewidth': 1.0,
    'lines.markersize': 3,
    'xtick.direction': 'out',
    'ytick.direction': 'out',
    'xtick.major.size': 3,
    'ytick.major.size': 3,
    'xtick.major.width': 0.75,
    'ytick.major.width': 0.75,
    'xtick.minor.size': 1.5,
    'ytick.minor.size': 1.5,
    'xtick.minor.width': 0.6,
    'ytick.minor.width': 0.6,
    'legend.frameon': False,
    'legend.handlelength': 1.2,
    'legend.handletextpad': 0.5,
    'legend.columnspacing': 1.0,
    'legend.labelspacing': 0.3,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'svg.fonttype': 'none',   # keep text editable in SVG
    'pdf.fonttype': 42,       # embed TrueType, editable in Illustrator
}


def nature_style(func):
    """Decorator: build the figure inside the Nature rc settings (global settings untouched)."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with mpl.rc_context(NATURE_RC):
            return func(*args, **kwargs)
    return wrapper


# ---- Palettes ----

# "Sunset" ramp for PC lines: plum -> orchid -> rose -> coral -> apricot.
# Lightness increases monotonically, so the PC order is readable from the colour;
# the lightest step still has >= 2:1 contrast on white.
SUNSET = ['#4b2a7b', '#7b3fa0', '#b04fa6', '#d9608f', '#ec7a6e', '#ee9a4d']

# Sequential map for intensities (dark plum -> cream), same family as SUNSET.
SUNSET_SEQ = LinearSegmentedColormap.from_list(
    'sunset_seq', ['#1f1035', '#4b2a7b', '#93449f', '#d65c8c', '#f28a72', '#f8bb8a', '#fdf1e4'])

# Diverging map for signed data (blueberry <- neutral grey -> raspberry).
BERRY_DIV = LinearSegmentedColormap.from_list(
    'berry_div', ['#2f4b8f', '#5b7ec4', '#a9bde3', '#eeeceb', '#eeb0c4', '#d0628f', '#8f2860'])

_PC_RAMP = LinearSegmentedColormap.from_list('sunset_lines', SUNSET)


def ramp_colors(n):
    """n colours evenly spaced along the sunset ramp (e.g. spectra over time)."""
    if n == 1:
        return [_PC_RAMP(0.0)]
    return [_PC_RAMP(i / (n - 1)) for i in range(n)]
