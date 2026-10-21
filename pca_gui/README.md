# PCA of spectra

Principal component analysis (PCA) of a series of spectra stored in a CSV file,
e.g. the CSV produced by the SPA to CSV converter (`DTU/FTIR/spa_to_csv_gui`).

Expected CSV layout: a `Wavenumber` column followed by one column per spectrum
(in time order). Files without a header row are also accepted.

## Installation

You need Python 3.9 or newer:

```
pip install -r requirements.txt
```

**Windows computer without internet?** Use the offline kit in
`DTU/offline_install_windows` (see its README.md).

## Starting it with a double-click (macOS)

Double-click **PCA of spectra - Mac.app** in this folder. It finds a Python installation with
the required packages (Anaconda, Miniconda, Homebrew, ...) and opens the window,
without a Terminal. To put it on the Dock or Desktop, make an alias
(⌘+⌥ drag) rather than moving the app: it has to stay next to these scripts.
If nothing appears, the log is in `~/Library/Logs/PCA of spectra.log`.

On another Mac, the first time macOS may say the app is from an unidentified
developer: right-click it → **Open** → **Open**.

## Starting it with a double-click (Windows)

Double-click **PCA of spectra - Windows.bat** in this folder. It finds a Python installation with
the required packages (Anaconda, Miniconda, the python.org `py` launcher, or
Python on the PATH) and opens the window. A console flashes briefly and closes.
For a Desktop shortcut: right-click the file → **Send to** → **Desktop (create
shortcut)**; keep the `.bat` itself next to these scripts.
If nothing appears, the log is in `%LOCALAPPDATA%\PCA of spectra.log`. If no suitable
Python is found, the console stays open and says so.

The first time, Windows SmartScreen may warn about a file from the internet:
**More info** → **Run anyway**.

## Usage with the window (recommended)

```
cd path/to/pca_gui
python run_gui.py
```

The analysis runs in two steps, so you can look at the PCs before choosing which
ones to reconstruct with.

1. **Files → Browse...** and choose the CSV. The window shows how many spectra
   and wavenumbers it contains, and the *Data preview* tab plots the spectra.
2. **Data to use**: choose the first and last spectrum and the wavenumber region.
   Press **Update preview** (or Enter) to see the selection highlighted.
3. **PCA**: set the time per spectrum and how many PCs to inspect, then click
   **Run PCA**. The *PCA results* tab then shows one row per PC with its
   eigenspectrum (left), its scores over time (right) and its % of variance.
   Scroll to see all PCs. Results are saved in a subfolder named after the
   selection, e.g. `PCA_1000-4000cm-1_spectra1-910`.
4. **Reconstruct with selected PCs**: tick the PCs you want and click
   **Reconstruct**. The reconstruction is saved in a subfolder of the PCA folder,
   e.g. `reconstruction_PCs1_3`. Try as many combinations as you like; the PCA
   is not re-run.

**Open results folder** opens the last folder written.

## Usage from the terminal

```
# Step 1 only: PCA, then look at eigenspectra_and_scores_PCs1-15.png
python run_cli.py data.csv -o results --spectra 1 910 --wn 1000 3000

# Step 1 + step 2: also reconstruct with PCs 1 and 3
python run_cli.py data.csv -o results --spectra 1 910 --wn 1000 3000 --pcs 1,3 --no-3d
```

## Output

In the PCA folder (step 1):

| File | Content |
|------|---------|
| `eigenvalues_and_cve.csv` | Eigenvalue, % variance and cumulative % per PC |
| `eigenspectra.csv` | Wavenumber + one column per PC (loadings) |
| `scores.csv` | Spectrum name, time and score of every PC |
| `mean_spectrum.csv` | Mean spectrum that was subtracted before PCA |
| `eigenspectra_and_scores_PCs1-N` | One row per PC: eigenspectrum and scores side by side |
| `cve`, `*_overview_*`, `*_correlation_matrix` | CVE, stacked eigenspectra/scores, correlation matrices |
| `loaded_data_*`, `mean_centered_data_*` | 2D (and optional 3D) maps of the data |

In `reconstruction_PCs…/` (step 2):

| File | Content |
|------|---------|
| `reconstructed_PCs…_before_adding_mean.csv` | Spectra rebuilt from the chosen PCs (mean-centred) |
| `reconstructed_PCs…_after_adding_mean.csv` | Same, with the mean spectrum added back |
| `residuals_PCs….csv` | Original spectra minus the reconstruction |
| figures | Scores and eigenspectra of the chosen PCs, 2D (and optional 3D) maps of the reconstruction and residuals |

Every figure is saved as PNG, SVG and PDF.

The reconstructed and residual CSVs have the same layout as the input, so they
can be loaded back into this tool.

## Figure style

Figures follow Nature-journal conventions (89 mm single-column width, Arial 7–8 pt,
thin axes, no top/right spines) and are saved as PNG (600 dpi), SVG and PDF with
editable text and a transparent background.

Colours (all defined in `style.py`, change them there):
- **PC lines**: a plum → rose → apricot "sunset" ramp; each trace is labelled.
- **Intensity maps**: sequential dark plum → cream.
- **Signed maps** (mean-centred data, reconstruction before adding the mean,
  residuals, correlation): blueberry ↔ raspberry, grey at zero, symmetric limits.
- Colour limits ignore the most extreme 0.5 % of values so one spike can't wash
  out the map (the colour bar arrows mark clipped values).

## Method

Each spectrum is an observation and each wavenumber a variable. The data are
mean-centred (the mean spectrum is subtracted), and the PCs are obtained from
an SVD of the centred data, which is equivalent to diagonalising the
covariance matrix between wavenumbers. Reconstruction with a set of PCs is
`scores · eigenspectraᵀ` (+ mean spectrum).

## Files

| File | What it does |
|------|--------------|
| `run_gui.py` | Starts the window |
| `run_cli.py` | Command-line version |
| `gui.py` | The Tkinter window and preview |
| `analysis.py` | The two steps: `run_pca_step` and `run_reconstruction` |
| `data_loader.py` | Reads the CSV and selects spectra / wavenumber region |
| `pca.py` | PCA, reconstruction and parsing of the PC list |
| `plots.py` | All figures |
| `style.py` | Journal style settings and colour palettes |
