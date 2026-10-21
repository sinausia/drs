"""Loading spectra from a CSV file and selecting spectra / wavenumber regions.

Expected CSV layout (as written by the SPA to CSV converter):

    Wavenumber, spectrum_1, spectrum_2, ...
    4000.188,   0.0123,     0.0125,     ...
    ...

Files without a header row (first column = wavenumbers) are also accepted.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class SpectraData:
    wavenumbers: np.ndarray   # shape (n_wavenumbers,)
    spectra: np.ndarray       # shape (n_spectra, n_wavenumbers), one row per spectrum
    names: list               # one name per spectrum
    indices: np.ndarray       # 0-based position of each spectrum in the original file

    @property
    def n_spectra(self):
        return self.spectra.shape[0]

    @property
    def n_wavenumbers(self):
        return self.spectra.shape[1]


def _is_number(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def load_spectra_csv(path):
    """Read a CSV with wavenumbers in the first column and one spectrum per column."""
    df = pd.read_csv(path)
    if all(_is_number(c) for c in df.columns):
        # No header row: the "column names" are actually the first row of data
        df = pd.read_csv(path, header=None)
        df.columns = ['Wavenumber'] + [f'Spectrum {i}' for i in range(1, df.shape[1])]

    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna(subset=[df.columns[0]])
    if df.shape[1] < 2:
        raise ValueError("The CSV needs a wavenumber column and at least one spectrum column.")

    return SpectraData(
        wavenumbers=df.iloc[:, 0].to_numpy(dtype=float),
        spectra=df.iloc[:, 1:].to_numpy(dtype=float).T,
        names=[str(c) for c in df.columns[1:]],
        indices=np.arange(df.shape[1] - 1),
    )


def select_data(data, first_spectrum=1, last_spectrum=None, wn_min=None, wn_max=None):
    """Keep spectra first..last (1-based, inclusive) and wavenumbers within [wn_min, wn_max].

    Wavenumbers where any selected spectrum is missing (NaN) are dropped.
    Returns (selected SpectraData, number of wavenumbers dropped because of NaNs).
    """
    last_spectrum = last_spectrum or data.n_spectra
    if not 1 <= first_spectrum <= last_spectrum <= data.n_spectra:
        raise ValueError(f"Spectra range must be between 1 and {data.n_spectra} (first <= last).")

    wn = data.wavenumbers
    lo = wn.min() if wn_min is None else wn_min
    hi = wn.max() if wn_max is None else wn_max
    if lo > hi:
        lo, hi = hi, lo
    wn_mask = (wn >= lo) & (wn <= hi)

    rows = slice(first_spectrum - 1, last_spectrum)
    spectra = data.spectra[rows][:, wn_mask]
    finite = np.isfinite(spectra).all(axis=0)
    n_dropped = int((~finite).sum())
    spectra = spectra[:, finite]

    if spectra.shape[1] < 2:
        raise ValueError(f"Only {spectra.shape[1]} wavenumber(s) between {lo} and {hi} cm-1. "
                         f"The file covers {wn.min():.1f} to {wn.max():.1f} cm-1.")
    if spectra.shape[0] < 2:
        raise ValueError("Select at least 2 spectra for PCA.")

    return SpectraData(
        wavenumbers=wn[wn_mask][finite],
        spectra=spectra,
        names=data.names[rows],
        indices=data.indices[rows],
    ), n_dropped


def spectra_to_dataframe(wavenumbers, spectra, names):
    """Inverse of load_spectra_csv: back to 'Wavenumber' + one column per spectrum."""
    df = pd.DataFrame(spectra.T, columns=names)
    df.insert(0, 'Wavenumber', wavenumbers)
    return df
