"""Figures for the PCA analysis, in a Nature-journal style (see style.py).

Every function returns a matplotlib Figure. pyplot is not used, so the figures
can be made safely from the GUI's background thread.
"""
import os

import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import AutoMinorLocator, MaxNLocator
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers the '3d' projection)

from style import BERRY_DIV, INK, MUTED, SUNSET, SUNSET_SEQ, W_DOUBLE, W_SINGLE, nature_style, ramp_colors

WN_LABEL = r'Wavenumber (cm$^{-1}$)'
TIME_LABEL = 'Time (s)'


def format_percent(value):
    """'49.3 %' for large values, '0.012 %' for small ones (never a misleading '0.0 %')."""
    return f'{value:.1f} %' if value >= 1 else f'{value:.2g} %'


def pcs_label(pcs):
    return ', '.join(str(pc) for pc in pcs)


@nature_style
def save_figure(fig, folder, name):
    """Save as PNG (600 dpi), SVG and PDF (vector, for submission).

    Saving runs inside the style too: tick labels are only created when drawing.
    """
    base = os.path.join(folder, name)
    kwargs = {'bbox_inches': 'tight', 'pad_inches': 0.02, 'transparent': True}
    fig.savefig(base + '.png', dpi=600, **kwargs)
    fig.savefig(base + '.svg', format='svg', **kwargs)
    fig.savefig(base + '.pdf', format='pdf', **kwargs)


def _minor_ticks(ax):
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())


def _set_wn_axis(ax, wavenumbers):
    ax.set_xlim(max(wavenumbers), min(wavenumbers))  # IR convention: high wavenumbers on the left
    ax.set_xlabel(WN_LABEL)


def _color_limits(values, signed):
    """Robust colour limits (ignores the most extreme 0.5 %); symmetric around 0 if signed."""
    finite = values[np.isfinite(values)]
    if signed:
        v = np.percentile(np.abs(finite), 99.5) or 1.0
        return -v, v
    lo, hi = np.percentile(finite, [0.5, 99.5])
    return lo, hi if hi > lo else lo + 1


# ---------- 2D / 3D maps ----------

@nature_style
def heatmap(wavenumbers, time, values, title, signed=False, cbar_label=None):
    """2D map: wavenumber on x, time on y, colour = intensity.

    signed=True for data centred on zero (mean-centred, residuals): diverging colours.
    """
    vmin, vmax = _color_limits(values, signed)
    fig = Figure(figsize=(W_SINGLE, W_SINGLE * 0.85))
    ax = fig.add_subplot()
    img = ax.imshow(values, cmap=BERRY_DIV if signed else SUNSET_SEQ, vmin=vmin, vmax=vmax,
                    aspect='auto', origin='lower', interpolation='nearest',
                    extent=[wavenumbers[0], wavenumbers[-1], time[0], time[-1]])
    _set_wn_axis(ax, wavenumbers)
    ax.set_ylabel(TIME_LABEL)
    ax.set_title(title, loc='left')
    _minor_ticks(ax)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(True)
    cbar = fig.colorbar(img, ax=ax, extend='both', fraction=0.05, pad=0.03)
    cbar.set_label(cbar_label or (r'$\Delta$Absorbance (a.u.)' if signed else 'Absorbance (a.u.)'))
    cbar.outline.set_linewidth(0.5)
    cbar.ax.tick_params(width=0.5, length=2)
    return fig


@nature_style
def surface_3d(wavenumbers, time, values, title, signed=False):
    """3D surface with a contour map projected underneath."""
    rows = slice(None, None, max(1, int(np.ceil(len(time) / 300))))
    cols = slice(None, None, max(1, int(np.ceil(len(wavenumbers) / 600))))
    X, Y = np.meshgrid(wavenumbers[cols], time[rows])
    Z = values[rows][:, cols]

    vmin, vmax = _color_limits(Z, signed)
    zmin, zmax = np.nanmin(Z), np.nanmax(Z)
    offset = zmin - 0.3 * (zmax - zmin)
    cmap = BERRY_DIV if signed else SUNSET_SEQ

    fig = Figure(figsize=(W_DOUBLE * 0.6, W_DOUBLE * 0.5))
    ax = fig.add_subplot(projection='3d')
    ax.plot_surface(X, Y, Z, cmap=cmap, vmin=vmin, vmax=vmax, edgecolor='none',
                    rcount=100, ccount=200, rasterized=True)
    ax.contourf(X, Y, Z, zdir='z', offset=offset, cmap=cmap, vmin=vmin, vmax=vmax,
                levels=50)
    ax.set_zlim(offset, zmax)
    ax.invert_xaxis()
    ax.set_xlabel(WN_LABEL, labelpad=4)
    ax.set_ylabel(TIME_LABEL, labelpad=4)
    ax.set_zticklabels([])
    ax.tick_params(pad=1)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        axis._axinfo['grid'].update(color='#d9d9d9', linewidth=0.4)
    ax.set_box_aspect([1.5, 1.2, 1], zoom=0.88)
    ax.view_init(elev=15, azim=-80)
    ax.set_title(title, loc='left')
    return fig


# ---------- Variance ----------

@nature_style
def cve_plot(result, n_show):
    """Cumulative variance explained, with an inset zoomed on PC 2 onwards."""
    n_show = min(n_show, result.n_pcs)
    pcs = np.arange(0, n_show + 1)
    cve = np.concatenate([[0], result.cumulative_variance[:n_show]])

    fig = Figure(figsize=(W_SINGLE, W_SINGLE * 0.78))
    ax = fig.add_subplot()
    ax.plot(pcs, cve, marker='o', markersize=3, linewidth=1.0, color=INK,
            markerfacecolor=INK, markeredgecolor='white', markeredgewidth=0.4)
    ax.set_xlabel('Principal component')
    ax.set_ylabel('Cumulative explained variance (%)')
    ax.set_xlim(0, n_show)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    _minor_ticks(ax)

    if n_show >= 4:
        inset = inset_axes(ax, width='55%', height='42%', loc='center right', borderpad=1.0)
        inset.plot(pcs[2:], cve[2:], marker='o', markersize=2.4, linewidth=0.9, color=SUNSET[1],
                   markerfacecolor=SUNSET[1], markeredgecolor='white', markeredgewidth=0.3)
        inset.set_xlim(2, n_show)
        inset.xaxis.set_major_locator(MaxNLocator(integer=True))
        inset.tick_params(labelsize=5.5, width=0.6, length=2)
        inset.set_title('From PC 2', fontsize=6, color=MUTED, loc='left', pad=2)
        for side in ('top', 'right'):
            inset.spines[side].set_visible(False)
        for side in ('left', 'bottom'):
            inset.spines[side].set_linewidth(0.6)
    return fig


# ---------- Scores and eigenspectra ----------

def _stacked(x, traces, xlabel, ylabel, gap=0.15):
    """Traces stacked vertically (first on top), each labelled 'PC n' at its right end.

    Colours run along the sunset ramp over the traces shown, so neighbours stay
    distinguishable; the labels carry the identity.

    traces: list of (pc, y). Each trace is placed just below the previous one,
    based on their actual extents, plus a gap (fraction of the largest span).
    Returns the figure and axes.
    """
    pad = gap * (max(np.ptp(y) for _, y in traces) or 1.0)
    shifts = [0.0]
    for (_, above), (_, below) in zip(traces, traces[1:]):
        shifts.append(shifts[-1] + above.min() - below.max() - pad)
    height = max(W_SINGLE * 0.78, 0.28 + 0.42 * len(traces))
    fig = Figure(figsize=(W_SINGLE, height))
    ax = fig.add_subplot()
    x_end = x[-1]
    colors = ramp_colors(len(traces))
    for i, ((pc, y), color) in enumerate(zip(traces, colors)):
        shift = shifts[i]
        ax.axhline(shift, color='#d9d9d9', linewidth=0.4, zorder=0)
        ax.plot(x, y + shift, color=color, linewidth=0.9)
        ax.annotate(f'PC {pc}', xy=(x_end, shift), xytext=(4, 0), textcoords='offset points',
                    va='center', ha='left', fontsize=6.5, color=INK, annotation_clip=False)
    ax.set_yticks([])
    ax.spines['left'].set_visible(False)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    return fig, ax


@nature_style
def scores_plot(time, result, pcs):
    if len(pcs) == 1:
        pc = pcs[0]
        fig = Figure(figsize=(W_SINGLE, W_SINGLE * 0.7))
        ax = fig.add_subplot()
        ax.plot(time, result.scores[:, pc - 1], color=SUNSET[0], linewidth=0.9)
        ax.set_ylabel(f'PC {pc} score (a.u.)')
        _minor_ticks(ax)
    else:
        # Scores of different PCs differ by orders of magnitude, so each one is
        # scaled to a maximum of 1 for stacking. Absolute values are in scores.csv.
        traces = []
        for pc in pcs:
            y = result.scores[:, pc - 1]
            traces.append((pc, y / (np.abs(y).max() or 1)))
        fig, ax = _stacked(time, traces, TIME_LABEL, 'Score (normalised, a.u.)')
    ax.set_xlabel(TIME_LABEL)
    ax.set_xlim(time[0], time[-1])
    return fig


@nature_style
def eigenspectra_plot(wavenumbers, result, pcs):
    order = np.argsort(wavenumbers)[::-1]   # plot from high to low wavenumber
    wn = wavenumbers[order]
    if len(pcs) == 1:
        pc = pcs[0]
        fig = Figure(figsize=(W_SINGLE, W_SINGLE * 0.7))
        ax = fig.add_subplot()
        ax.axhline(0, color='#d9d9d9', linewidth=0.4, zorder=0)
        ax.plot(wn, result.eigenvectors[order, pc - 1], color=SUNSET[0], linewidth=0.9)
        ax.set_ylabel(f'PC {pc} loading (a.u.)')
        _minor_ticks(ax)
    else:
        traces = [(pc, result.eigenvectors[order, pc - 1]) for pc in pcs]
        fig, ax = _stacked(wn, traces, WN_LABEL, 'Loading (a.u.)')
    _set_wn_axis(ax, wn)
    return fig


# ---------- Overview grid: one row per PC ----------

def draw_pc_grid(fig, wavenumbers, time, result, n_pcs, label_size=7):
    """Fill ``fig`` with one row per PC: eigenspectrum (left) and scores (right).

    Used both for the saved figure and for the GUI's results tab.
    """
    n_pcs = min(n_pcs, result.n_pcs)
    order = np.argsort(wavenumbers)[::-1]
    wn = wavenumbers[order]
    colors = ramp_colors(n_pcs)
    axes = fig.subplots(n_pcs, 2, squeeze=False, sharex='col',
                        gridspec_kw={'hspace': 0.15, 'wspace': 0.08})
    for i in range(n_pcs):
        ax_eig, ax_scr = axes[i]
        for ax, x, y in ((ax_eig, wn, result.eigenvectors[order, i]), (ax_scr, time, result.scores[:, i])):
            ax.axhline(0, color='#d9d9d9', linewidth=0.4, zorder=0)
            ax.plot(x, y, color=colors[i], linewidth=0.8)
            ax.set_yticks([])
            for side in ('left', 'top', 'right'):
                ax.spines[side].set_visible(False)
            if i < n_pcs - 1:
                ax.tick_params(axis='x', which='both', length=0, labelbottom=False)
                ax.spines['bottom'].set_visible(False)
        ax_eig.set_ylabel(f'PC {i + 1}\n{format_percent(result.explained_variance[i])}', rotation=0,
                          ha='right', va='center', fontsize=label_size, labelpad=4)
    axes[0, 0].set_title('Eigenspectra', loc='left', fontsize=label_size + 1)
    axes[0, 1].set_title('Scores', loc='left', fontsize=label_size + 1)
    axes[-1, 0].set_xlim(wn[0], wn[-1])
    axes[-1, 0].set_xlabel(WN_LABEL, fontsize=label_size + 1)
    axes[-1, 1].set_xlim(time[0], time[-1])
    axes[-1, 1].set_xlabel(TIME_LABEL, fontsize=label_size + 1)
    for ax in axes[-1]:
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.tick_params(labelsize=label_size)
    return axes


@nature_style
def pc_grid_figure(wavenumbers, time, result, n_pcs):
    n = min(n_pcs, result.n_pcs)
    fig = Figure(figsize=(W_DOUBLE, 0.4 + 0.42 * n))
    draw_pc_grid(fig, wavenumbers, time, result, n)
    return fig


# ---------- Correlation matrices ----------

@nature_style
def correlation_plot(vectors, title, log_scale=False):
    """Correlation matrix between columns of ``vectors`` (one column per PC)."""
    n = vectors.shape[1]
    corr = np.corrcoef(vectors, rowvar=False)

    fig = Figure(figsize=(W_SINGLE, W_SINGLE * 0.85))
    ax = fig.add_subplot()
    if log_scale:
        with np.errstate(divide='ignore'):
            values = np.log10(np.abs(corr))
        finite = values[np.isfinite(values)]
        img = ax.imshow(values, cmap=SUNSET_SEQ, vmin=finite.min(), vmax=0)
        label = r'log$_{10}$ |correlation|'
    else:
        img = ax.imshow(corr, cmap=BERRY_DIV, vmin=-1, vmax=1)
        label = 'Correlation'
    for side in ('top', 'right'):
        ax.spines[side].set_visible(True)
    ticks = np.arange(n)
    step = max(1, int(np.ceil(n / 10)))
    ax.set_xticks(ticks[::step], ticks[::step] + 1)
    ax.set_yticks(ticks[::step], ticks[::step] + 1)
    ax.set_xlabel('Principal component')
    ax.set_ylabel('Principal component')
    ax.set_title(title, loc='left')
    cbar = fig.colorbar(img, ax=ax, fraction=0.05, pad=0.03)
    cbar.set_label(label)
    cbar.outline.set_linewidth(0.5)
    cbar.ax.tick_params(width=0.5, length=2)
    return fig
