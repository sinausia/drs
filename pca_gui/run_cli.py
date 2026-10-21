"""Command-line version of the PCA tool (no window).

Step 1 only (PCA, then inspect eigenspectra_and_scores_*.png):
    python run_cli.py data.csv -o results --wn 1000 3000 --spectra 1 910

Step 1 + step 2 (also reconstruct with PCs 1 and 3):
    python run_cli.py data.csv -o results --wn 1000 3000 --spectra 1 910 --pcs 1,3
"""
import argparse
import os

import matplotlib
matplotlib.use('Agg')

from analysis import PCASettings, run_pca_step, run_reconstruction


def main():
    parser = argparse.ArgumentParser(description="PCA of spectra stored in a CSV file.")
    parser.add_argument('csv', help="CSV file: 'Wavenumber' column + one column per spectrum")
    parser.add_argument('-o', '--output', help="Output folder (default: <csv name>_PCA next to the CSV)")
    parser.add_argument('--spectra', nargs=2, type=int, metavar=('FIRST', 'LAST'), help="Spectra to use (1-based)")
    parser.add_argument('--wn', nargs=2, type=float, metavar=('MIN', 'MAX'), help="Wavenumber region (cm-1)")
    parser.add_argument('--pcs', help="Also reconstruct with these PCs, e.g. '1' or '1,3' or '2-4'")
    parser.add_argument('--time-per-spectrum', type=float, default=1.1)
    parser.add_argument('--n-pcs-to-show', type=int, default=15)
    parser.add_argument('--no-3d', action='store_true', help="Skip the (slow) 3D plots")
    args = parser.parse_args()

    output = args.output or os.path.splitext(os.path.abspath(args.csv))[0] + '_PCA'
    first, last = args.spectra or (1, None)
    wn_min, wn_max = args.wn or (None, None)
    run = run_pca_step(PCASettings(
        csv_path=args.csv, output_folder=output,
        first_spectrum=first, last_spectrum=last, wn_min=wn_min, wn_max=wn_max,
        time_per_spectrum=args.time_per_spectrum,
        n_pcs_to_show=args.n_pcs_to_show, make_3d_plots=not args.no_3d,
    ))
    if args.pcs:
        run_reconstruction(run, args.pcs)


if __name__ == '__main__':
    main()
