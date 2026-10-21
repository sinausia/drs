"""PCA workflow in two steps, saving CSV files and figures.

Step 1, run_pca_step:       select data, run PCA, save eigenspectra/scores/CVE.
Step 2, run_reconstruction: after inspecting step 1, rebuild the spectra from
                            the chosen PCs (saved in a subfolder of step 1).

This module has no GUI code, so it can also be used from other scripts:

    from analysis import PCASettings, run_pca_step, run_reconstruction
    run = run_pca_step(PCASettings(csv_path='data.csv', output_folder='out', wn_min=1000, wn_max=3000))
    run_reconstruction(run, [1, 3])
"""
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

import plots
from data_loader import SpectraData, load_spectra_csv, select_data, spectra_to_dataframe
from pca import PCAResult, parse_pc_list, reconstruct, run_pca


@dataclass
class PCASettings:
    csv_path: str
    output_folder: str
    first_spectrum: int = 1
    last_spectrum: Optional[int] = None    # None = up to the last spectrum in the file
    wn_min: Optional[float] = None         # None = lowest wavenumber in the file
    wn_max: Optional[float] = None         # None = highest wavenumber in the file
    time_per_spectrum: float = 1.1         # seconds it takes to record one spectrum
    n_pcs_to_show: int = 15                # PCs in the overview, CVE and correlation plots
    make_3d_plots: bool = True


@dataclass
class PCARun:
    """Everything step 2 needs from step 1."""
    settings: PCASettings
    selection: SpectraData
    result: PCAResult
    time: np.ndarray
    output_folder: str

    @property
    def n_show(self):
        return max(1, min(self.settings.n_pcs_to_show, self.result.n_pcs))


def _save_figures(figures, folder, log):
    for i, (name, make) in enumerate(figures, start=1):
        log(f"  [{i}/{len(figures)}] {name}")
        plots.save_figure(make(), folder, name)


def run_pca_step(settings, log=print, data=None):
    """Step 1. ``data`` can be passed if the CSV is already loaded. Returns a PCARun."""
    s = settings
    if data is None:
        log(f"Loading {s.csv_path}")
        data = load_spectra_csv(s.csv_path)

    sel, n_dropped = select_data(data, s.first_spectrum, s.last_spectrum, s.wn_min, s.wn_max)
    if n_dropped:
        log(f"Warning: {n_dropped} wavenumbers with missing values were left out.")
    wn = sel.wavenumbers
    time = sel.indices * s.time_per_spectrum
    log(f"Using spectra {s.first_spectrum}-{s.first_spectrum + sel.n_spectra - 1} "
        f"({sel.n_spectra} spectra) and {sel.n_wavenumbers} wavenumbers "
        f"({wn.min():.1f} to {wn.max():.1f} cm-1)")

    log("Running PCA...")
    result = run_pca(sel.spectra)
    run = PCARun(settings=s, selection=sel, result=result, time=time, output_folder=s.output_folder)
    n_show = run.n_show
    for pc in range(1, min(5, result.n_pcs) + 1):
        log(f"  PC {pc}: {result.explained_variance[pc - 1]:.2f} % of variance "
            f"(cumulative {result.cumulative_variance[pc - 1]:.2f} %)")

    out = s.output_folder
    os.makedirs(out, exist_ok=True)

    log("Saving CSV files...")
    pc_names = [f'PC{i}' for i in range(1, result.n_pcs + 1)]
    pd.DataFrame({
        'PC': np.arange(1, result.n_pcs + 1),
        'Eigenvalue': result.eigenvalues,
        'Variance explained (%)': result.explained_variance,
        'Cumulative variance explained (%)': result.cumulative_variance,
    }).to_csv(os.path.join(out, 'eigenvalues_and_cve.csv'), index=False)

    eigvec_df = pd.DataFrame(result.eigenvectors, columns=pc_names)
    eigvec_df.insert(0, 'Wavenumber', wn)
    eigvec_df.to_csv(os.path.join(out, 'eigenspectra.csv'), index=False)

    scores_df = pd.DataFrame(result.scores, columns=pc_names)
    scores_df.insert(0, 'Time (s)', time)
    scores_df.insert(0, 'Spectrum', sel.names)
    scores_df.to_csv(os.path.join(out, 'scores.csv'), index=False)

    pd.DataFrame({'Wavenumber': wn, 'Mean spectrum': result.mean}).to_csv(
        os.path.join(out, 'mean_spectrum.csv'), index=False)

    log("Making figures...")
    centered = sel.spectra - result.mean
    n_overview = min(n_show, 15)
    overview = list(range(1, n_overview + 1))
    figures = [
        (f'eigenspectra_and_scores_PCs1-{n_show}', lambda: plots.pc_grid_figure(wn, time, result, n_show)),
        ('cve', lambda: plots.cve_plot(result, n_show)),
        (f'scores_overview_PCs1-{n_overview}', lambda: plots.scores_plot(time, result, overview)),
        (f'eigenspectra_overview_PCs1-{n_overview}', lambda: plots.eigenspectra_plot(wn, result, overview)),
        ('loaded_data_2D', lambda: plots.heatmap(wn, time, sel.spectra, 'Loaded data')),
        ('mean_centered_data_2D', lambda: plots.heatmap(wn, time, centered, 'Mean-centred data', signed=True)),
    ]
    if n_show >= 2:
        eig = result.eigenvectors[:, :n_show]
        scr = result.scores[:, :n_show]
        figures += [
            ('eigenspectra_correlation_matrix', lambda: plots.correlation_plot(eig, 'Eigenspectra')),
            ('eigenspectra_log_correlation_matrix', lambda: plots.correlation_plot(
                eig, 'Eigenspectra', log_scale=True)),
            ('scores_correlation_matrix', lambda: plots.correlation_plot(scr, 'Scores')),
            ('scores_log_correlation_matrix', lambda: plots.correlation_plot(scr, 'Scores', log_scale=True)),
        ]
    if s.make_3d_plots:
        figures += [
            ('loaded_data_3D', lambda: plots.surface_3d(wn, time, sel.spectra, 'Loaded data')),
            ('mean_centered_data_3D', lambda: plots.surface_3d(
                wn, time, centered, 'Mean-centred data', signed=True)),
        ]
    _save_figures(figures, out, log)

    log(f"PCA done. Results saved in {out}")
    return run


def run_reconstruction(run, pcs, make_3d_plots=None, log=print):
    """Step 2: rebuild the spectra from the chosen PCs.

    pcs: list of PC numbers (1-based) or a string like '1, 3' or '2-4'.
    Results go to <PCA folder>/reconstruction_PCs<...>. Returns that folder.
    """
    if isinstance(pcs, str):
        pcs = parse_pc_list(pcs, run.result.n_pcs)
    else:
        pcs = parse_pc_list(','.join(map(str, pcs)), run.result.n_pcs)
    if make_3d_plots is None:
        make_3d_plots = run.settings.make_3d_plots

    sel, result, time, wn = run.selection, run.result, run.time, run.selection.wavenumbers
    pcs_tag = '_'.join(map(str, pcs))
    label = f'PC {plots.pcs_label(pcs)}' if len(pcs) == 1 else f'PCs {plots.pcs_label(pcs)}'
    out = os.path.join(run.output_folder, f'reconstruction_PCs{pcs_tag}')
    os.makedirs(out, exist_ok=True)
    log(f"Reconstructing with {label}...")

    recon_centered = reconstruct(result, pcs, add_mean=False)
    recon_full = recon_centered + result.mean
    residuals = sel.spectra - recon_full

    # Same layout as the input CSV, so these files can be loaded back into this tool
    for array, name in [
        (recon_centered, f'reconstructed_PCs{pcs_tag}_before_adding_mean.csv'),
        (recon_full, f'reconstructed_PCs{pcs_tag}_after_adding_mean.csv'),
        (residuals, f'residuals_PCs{pcs_tag}.csv'),
    ]:
        spectra_to_dataframe(wn, array, sel.names).to_csv(os.path.join(out, name), index=False)

    figures = [
        (f'scores_PCs{pcs_tag}', lambda: plots.scores_plot(time, result, pcs)),
        (f'eigenspectra_PCs{pcs_tag}', lambda: plots.eigenspectra_plot(wn, result, pcs)),
        (f'reconstructed_PCs{pcs_tag}_before_adding_mean_2D', lambda: plots.heatmap(
            wn, time, recon_centered, f'Reconstructed, {label} (mean-centred)', signed=True)),
        (f'reconstructed_PCs{pcs_tag}_after_adding_mean_2D', lambda: plots.heatmap(
            wn, time, recon_full, f'Reconstructed, {label} (+ mean)')),
        (f'residuals_PCs{pcs_tag}_2D', lambda: plots.heatmap(
            wn, time, residuals, f'Residuals, {label}', signed=True)),
    ]
    if make_3d_plots:
        figures += [
            (f'reconstructed_PCs{pcs_tag}_before_adding_mean_3D', lambda: plots.surface_3d(
                wn, time, recon_centered, f'Reconstructed, {label} (mean-centred)', signed=True)),
            (f'reconstructed_PCs{pcs_tag}_after_adding_mean_3D', lambda: plots.surface_3d(
                wn, time, recon_full, f'Reconstructed, {label} (+ mean)')),
        ]
    _save_figures(figures, out, log)

    log(f"Reconstruction done. Results saved in {out}")
    return out
