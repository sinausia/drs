"""Principal component analysis of a set of spectra.

Each spectrum is one observation and each wavenumber is one variable, as in
the original script (covariance matrix between wavenumbers). The PCs are
computed with an SVD of the mean-centred data, which gives the same
eigenvalues/eigenvectors as diagonalising the covariance matrix, but is much
faster when there are thousands of wavenumbers.
"""
from dataclasses import dataclass

import numpy as np


@dataclass
class PCAResult:
    mean: np.ndarray          # mean spectrum, shape (n_wavenumbers,)
    eigenvalues: np.ndarray   # variance of each PC, descending, shape (n_pcs,)
    eigenvectors: np.ndarray  # eigenspectra/loadings, shape (n_wavenumbers, n_pcs)
    scores: np.ndarray        # shape (n_spectra, n_pcs)

    @property
    def n_pcs(self):
        return len(self.eigenvalues)

    @property
    def explained_variance(self):
        """Variance explained by each PC, in %."""
        return self.eigenvalues / self.eigenvalues.sum() * 100

    @property
    def cumulative_variance(self):
        """Cumulative variance explained (CVE), in %."""
        return np.cumsum(self.explained_variance)


def run_pca(spectra):
    """PCA of spectra with shape (n_spectra, n_wavenumbers)."""
    mean = spectra.mean(axis=0)
    centered = spectra - mean
    u, s, vt = np.linalg.svd(centered, full_matrices=False)
    eigenvalues = s ** 2 / (spectra.shape[0] - 1)
    eigenvectors = vt.T
    scores = centered @ eigenvectors
    return PCAResult(mean=mean, eigenvalues=eigenvalues, eigenvectors=eigenvectors, scores=scores)


def reconstruct(result, pcs, add_mean=False):
    """Rebuild the spectra using only the given PCs (1-based numbers, e.g. [1, 3])."""
    idx = [pc - 1 for pc in pcs]
    reconstructed = result.scores[:, idx] @ result.eigenvectors[:, idx].T
    if add_mean:
        reconstructed = reconstructed + result.mean
    return reconstructed


def parse_pc_list(text, n_pcs):
    """Turn '1, 3, 5-7' into [1, 3, 5, 6, 7], checking each PC exists."""
    pcs = []
    for part in text.replace(';', ',').split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            start, end = (int(p) for p in part.split('-', 1))
            pcs.extend(range(start, end + 1))
        else:
            pcs.append(int(part))
    if not pcs:
        raise ValueError("Enter at least one PC to reconstruct (e.g. '1' or '1, 3' or '2-4').")
    bad = [pc for pc in pcs if not 1 <= pc <= n_pcs]
    if bad:
        raise ValueError(f"PC(s) {bad} do not exist. Choose between 1 and {n_pcs}.")
    return sorted(set(pcs))
