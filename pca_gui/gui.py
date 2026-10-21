"""Tkinter window for running PCA on a CSV of spectra, in two steps.

Step 1 "Run PCA" shows the eigenspectra and scores of every PC.
Step 2 "Reconstruct" then uses the PCs you tick after inspecting them.
"""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib
matplotlib.use('TkAgg')
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import plots
from analysis import PCASettings, run_pca_step, run_reconstruction
from data_loader import load_spectra_csv
from style import ramp_colors

GRID_ROW_PX = 95   # height of one PC row in the results tab


def results_subfolder_name(s):
    return f"PCA_{s.wn_min:g}-{s.wn_max:g}cm-1_spectra{s.first_spectrum}-{s.last_spectrum}"


class PCAApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PCA of spectra")
        self.root.minsize(900, 600)

        self.data = None
        self.pca_run = None          # result of step 1
        self.last_output = None
        self.pc_vars = []            # one BooleanVar per PC checkbox
        self.grid_canvas = None
        self.grid_width = 0
        self.messages = queue.Queue()

        self.csv_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.first_var = tk.StringVar(value='1')
        self.last_var = tk.StringVar()
        self.wn_min_var = tk.StringVar()
        self.wn_max_var = tk.StringVar()
        self.time_var = tk.StringVar(value='1.1')
        self.n_show_var = tk.StringVar(value='15')
        self.plots_3d_var = tk.BooleanVar(value=False)

        self._build_widgets()
        self.root.after(100, self._poll_messages)

    # ---------- layout ----------

    def _build_widgets(self):
        pad = {'padx': 6, 'pady': 3}
        # Controls on the left keep their full width; the plots take the rest
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        left = ttk.Frame(self.root, padding=10)
        right = ttk.Frame(self.root, padding=(0, 10, 10, 10))
        left.grid(row=0, column=0, sticky='ns')
        right.grid(row=0, column=1, sticky='nsew')

        # 1. Files
        files = ttk.LabelFrame(left, text="1. Files", padding=8)
        files.pack(fill='x', **pad)
        files.columnconfigure(1, weight=1)
        ttk.Label(files, text="CSV file:").grid(row=0, column=0, sticky='w')
        ttk.Entry(files, textvariable=self.csv_var, width=36).grid(row=0, column=1, sticky='ew', padx=4)
        ttk.Button(files, text="Browse...", command=self._choose_csv).grid(row=0, column=2)
        ttk.Label(files, text="Save results in:").grid(row=1, column=0, sticky='w', pady=(4, 0))
        ttk.Entry(files, textvariable=self.output_var, width=36).grid(row=1, column=1, sticky='ew', padx=4, pady=(4, 0))
        ttk.Button(files, text="Browse...", command=self._choose_output).grid(row=1, column=2, pady=(4, 0))
        self.file_info = ttk.Label(files, text="No file loaded", foreground='gray')
        self.file_info.grid(row=2, column=0, columnspan=3, sticky='w', pady=(4, 0))

        # 2. Data selection
        sel = ttk.LabelFrame(left, text="2. Data to use", padding=8)
        sel.pack(fill='x', **pad)
        self._range_row(sel, 0, "Spectra (first, last):", self.first_var, self.last_var)
        self._range_row(sel, 1, "Wavenumbers (cm-1, min, max):", self.wn_min_var, self.wn_max_var)
        ttk.Button(sel, text="Update preview", command=self._update_preview).grid(
            row=2, column=0, columnspan=3, sticky='w', pady=(6, 0))

        # 3. PCA
        opts = ttk.LabelFrame(left, text="3. PCA", padding=8)
        opts.pack(fill='x', **pad)
        self._field_row(opts, 0, "Time per spectrum (s):", self.time_var)
        self._field_row(opts, 1, "Number of PCs to inspect:", self.n_show_var)
        ttk.Checkbutton(opts, text="Make 3D plots (slower)", variable=self.plots_3d_var).grid(
            row=2, column=0, columnspan=2, sticky='w', pady=(4, 0))
        self.run_btn = ttk.Button(opts, text="Run PCA", command=self._start_pca)
        self.run_btn.grid(row=3, column=0, sticky='w', pady=(6, 0))

        # 4. Reconstruction (enabled after step 3)
        self.recon_frame = ttk.LabelFrame(left, text="4. Reconstruct with selected PCs", padding=8)
        self.recon_frame.pack(fill='x', **pad)
        self.recon_hint = ttk.Label(self.recon_frame, foreground='gray',
                                    text="Run PCA first, inspect the eigenspectra and scores,\n"
                                         "then tick the PCs to use here.")
        self.recon_hint.grid(row=0, column=0, columnspan=5, sticky='w')
        self.pc_box = ttk.Frame(self.recon_frame)
        self.pc_box.grid(row=1, column=0, columnspan=5, sticky='w', pady=(4, 0))
        self.recon_btn = ttk.Button(self.recon_frame, text="Reconstruct", command=self._start_reconstruction,
                                    state='disabled')
        self.recon_btn.grid(row=2, column=0, sticky='w', pady=(6, 0))

        # Status row
        status = ttk.Frame(left)
        status.pack(fill='x', **pad)
        self.open_btn = ttk.Button(status, text="Open results folder", command=self._open_output, state='disabled')
        self.open_btn.pack(side='left')
        self.busy = ttk.Progressbar(status, mode='indeterminate', length=120)
        self.busy.pack(side='left', padx=6)

        # Log
        log_frame = ttk.Frame(left)
        log_frame.pack(fill='both', expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=8, width=56, wrap='word', state='disabled')
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        # Right side: tabs
        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill='both', expand=True)
        preview_tab = ttk.Frame(self.tabs)
        self.results_tab = ttk.Frame(self.tabs)
        self.tabs.add(preview_tab, text="Data preview")
        self.tabs.add(self.results_tab, text="PCA results")

        self.fig = Figure(figsize=(5, 4), facecolor='white')
        self.ax = self.fig.add_subplot()
        self.canvas = FigureCanvasTkAgg(self.fig, master=preview_tab)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        self._draw_empty_preview()

        # Scrollable area for the eigenspectra/scores grid
        self.scroll_canvas = tk.Canvas(self.results_tab, background='white', highlightthickness=0)
        grid_scroll = ttk.Scrollbar(self.results_tab, orient='vertical', command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=grid_scroll.set)
        grid_scroll.pack(side='right', fill='y')
        self.scroll_canvas.pack(side='left', fill='both', expand=True)
        self.grid_holder = tk.Frame(self.scroll_canvas, background='white')
        self.scroll_canvas.create_window((0, 0), window=self.grid_holder, anchor='nw')
        self.grid_holder.bind('<Configure>', lambda e: self.scroll_canvas.configure(
            scrollregion=self.scroll_canvas.bbox('all')))
        self.scroll_canvas.bind('<Configure>', self._on_results_resize)
        tk.Label(self.grid_holder, text="Run PCA to see the eigenspectra and scores of each PC here.",
                 background='white', foreground='gray').pack(padx=20, pady=20)

    def _range_row(self, parent, row, label, var_a, var_b):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w')
        for col, var in ((1, var_a), (2, var_b)):
            entry = ttk.Entry(parent, textvariable=var, width=10)
            entry.grid(row=row, column=col, padx=4, pady=2)
            entry.bind('<Return>', lambda e: self._update_preview())

    def _field_row(self, parent, row, label, var):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w')
        ttk.Entry(parent, textvariable=var, width=10).grid(row=row, column=1, padx=4, pady=2, sticky='w')

    # ---------- file selection ----------

    def _choose_csv(self):
        path = filedialog.askopenfilename(
            title="Select the CSV file with spectra",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self.csv_var.set(path)
            self._load_csv(path)

    def _choose_output(self):
        folder = filedialog.askdirectory(title="Select where to save the results")
        if folder:
            self.output_var.set(folder)

    def _load_csv(self, path):
        try:
            self.root.config(cursor='watch')
            self.root.update_idletasks()
            self.data = load_spectra_csv(path)
        except Exception as e:
            self.data = None
            messagebox.showerror("Could not read file", str(e))
            return
        finally:
            self.root.config(cursor='')

        wn = self.data.wavenumbers
        self.first_var.set('1')
        self.last_var.set(str(self.data.n_spectra))
        self.wn_min_var.set(f"{wn.min():g}")
        self.wn_max_var.set(f"{wn.max():g}")
        if not self.output_var.get():
            self.output_var.set(os.path.dirname(path))
        self.file_info.configure(
            text=f"{self.data.n_spectra} spectra, {len(wn)} wavenumbers "
                 f"({wn.min():.1f} to {wn.max():.1f} cm-1)", foreground='')
        self._log(f"Loaded {os.path.basename(path)}")
        self.tabs.select(0)
        self._update_preview()

    # ---------- settings ----------

    def _read_settings(self):
        """Validate the form. Returns PCASettings or None (after showing an error)."""
        if self.data is None:
            messagebox.showerror("No data", "Please select a CSV file first.")
            return None
        try:
            settings = PCASettings(
                csv_path=self.csv_var.get(),
                output_folder='',
                first_spectrum=int(self.first_var.get()),
                last_spectrum=int(self.last_var.get()),
                wn_min=float(self.wn_min_var.get()),
                wn_max=float(self.wn_max_var.get()),
                time_per_spectrum=float(self.time_var.get()),
                n_pcs_to_show=int(self.n_show_var.get()),
                make_3d_plots=self.plots_3d_var.get(),
            )
        except ValueError:
            messagebox.showerror("Invalid input", "Please check that all numeric fields contain numbers.")
            return None
        if settings.wn_min > settings.wn_max:
            settings.wn_min, settings.wn_max = settings.wn_max, settings.wn_min
        return settings

    # ---------- preview ----------

    def _draw_empty_preview(self):
        self.ax.clear()
        self.ax.text(0.5, 0.5, "Load a CSV file to see a preview", ha='center', va='center',
                     transform=self.ax.transAxes, color='gray')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    def _update_preview(self):
        if self.data is None:
            return
        try:
            first = int(self.first_var.get())
            last = int(self.last_var.get())
            lo, hi = sorted((float(self.wn_min_var.get()), float(self.wn_max_var.get())))
        except ValueError:
            return
        first = max(1, min(first, self.data.n_spectra))
        last = max(first, min(last, self.data.n_spectra))

        wn = self.data.wavenumbers
        spectra = self.data.spectra[first - 1:last]
        ax = self.ax
        ax.clear()

        # Up to 10 evenly spaced spectra from the selection, coloured by time
        picks = np.unique(np.linspace(0, len(spectra) - 1, min(10, len(spectra))).astype(int))
        colors = ramp_colors(len(picks))
        for color, i in zip(colors, picks):
            ax.plot(wn, spectra[i], color=color, lw=0.8, label=f"#{first + i}")
        ax.axvspan(lo, hi, color='#a9bde3', alpha=0.35, label='Selected region', zorder=0)
        ax.axvline(lo, color='#5b7ec4', lw=1)
        ax.axvline(hi, color='#5b7ec4', lw=1)
        ax.set_xlim(wn.max(), wn.min())
        ax.set_xlabel('Wavenumbers (cm$^{-1}$)')
        ax.set_ylabel('Absorbance (a.u.)')
        ax.set_title(f"Spectra {first}-{last} ({last - first + 1} selected), region {lo:g}-{hi:g} cm$^{{-1}}$",
                     fontsize=10)
        ax.legend(fontsize=7, ncol=2, loc='best')
        self.fig.tight_layout()
        self.canvas.draw_idle()

    # ---------- PCA results tab ----------

    def _show_pca_results(self):
        """Draw the eigenspectra/scores grid and build the PC checkboxes."""
        self.tabs.select(1)
        self.root.update_idletasks()
        self._draw_pc_grid()

        run = self.pca_run
        for child in self.pc_box.winfo_children():
            child.destroy()
        self.pc_vars = []
        for i in range(run.n_show):
            var = tk.BooleanVar(value=False)
            self.pc_vars.append(var)
            ttk.Checkbutton(self.pc_box, text=f"PC {i + 1} ({plots.format_percent(run.result.explained_variance[i])})",
                            variable=var).grid(row=i // 3, column=i % 3, sticky='w', padx=(0, 10))
        s = run.settings
        self.recon_hint.configure(
            foreground='',
            text=f"Using the PCA of spectra {s.first_spectrum}-{s.last_spectrum}, "
                 f"{s.wn_min:g}-{s.wn_max:g} cm-1.\nTick the PCs to use:")
        self.recon_btn.configure(state='normal')

    def _draw_pc_grid(self):
        run = self.pca_run
        if run is None:
            return
        for child in self.grid_holder.winfo_children():
            child.destroy()
        width_px = max(400, self.scroll_canvas.winfo_width())
        self.grid_width = width_px
        dpi = 100
        n = run.n_show
        fig = Figure(figsize=(width_px / dpi, (70 + GRID_ROW_PX * n) / dpi), dpi=dpi, facecolor='white')
        plots.draw_pc_grid(fig, run.selection.wavenumbers, run.time, run.result, n, label_size=8)
        fig.subplots_adjust(left=0.11, right=0.98, top=1 - 25 / (70 + GRID_ROW_PX * n),
                            bottom=48 / (70 + GRID_ROW_PX * n))
        self.grid_canvas = FigureCanvasTkAgg(fig, master=self.grid_holder)
        widget = self.grid_canvas.get_tk_widget()
        widget.pack()
        self.grid_canvas.draw()
        for w in (widget, self.scroll_canvas):
            w.bind('<MouseWheel>', self._on_mousewheel)
            w.bind('<Button-4>', lambda e: self.scroll_canvas.yview_scroll(-1, 'units'))
            w.bind('<Button-5>', lambda e: self.scroll_canvas.yview_scroll(1, 'units'))

    def _on_results_resize(self, event):
        # Redraw the grid at the new width (debounced)
        if self.pca_run is not None and abs(event.width - self.grid_width) > 40:
            if hasattr(self, '_resize_job'):
                self.root.after_cancel(self._resize_job)
            self._resize_job = self.root.after(300, self._draw_pc_grid)

    def _on_mousewheel(self, event):
        step = -event.delta if sys.platform == 'darwin' else -event.delta // 120
        self.scroll_canvas.yview_scroll(int(step), 'units')

    # ---------- running ----------

    def _start_pca(self):
        settings = self._read_settings()
        if settings is None:
            return
        base = self.output_var.get().strip() or os.path.dirname(settings.csv_path)
        settings.output_folder = os.path.join(base, results_subfolder_name(settings))
        if os.path.isdir(settings.output_folder) and not messagebox.askyesno(
                "Overwrite?", f"{settings.output_folder}\nalready exists. Overwrite the results in it?"):
            return
        self._update_preview()
        self._run_in_background(self._pca_job, settings)

    def _start_reconstruction(self):
        pcs = [i + 1 for i, var in enumerate(self.pc_vars) if var.get()]
        if not pcs:
            messagebox.showerror("No PCs selected", "Tick at least one PC to reconstruct with.")
            return
        self._run_in_background(self._reconstruction_job, pcs, self.plots_3d_var.get())

    def _run_in_background(self, job, *args):
        self.run_btn.configure(state='disabled')
        self.recon_btn.configure(state='disabled')
        self.busy.start(10)
        threading.Thread(target=job, args=args, daemon=True).start()

    def _send_log(self, msg):
        self.messages.put(('log', msg))

    def _pca_job(self, settings):
        try:
            run = run_pca_step(settings, log=self._send_log, data=self.data)
            self.messages.put(('pca_done', run))
        except Exception as e:
            self.messages.put(('error', str(e)))

    def _reconstruction_job(self, pcs, make_3d):
        try:
            folder = run_reconstruction(self.pca_run, pcs, make_3d_plots=make_3d, log=self._send_log)
            self.messages.put(('recon_done', folder))
        except Exception as e:
            self.messages.put(('error', str(e)))

    def _poll_messages(self):
        """Apply updates sent from the worker thread (Tk is not thread-safe)."""
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == 'log':
                    self._log(payload)
                elif kind == 'pca_done':
                    self.pca_run = payload
                    self._finish(payload.output_folder)
                    self._show_pca_results()
                    self._log("Inspect the PCA results tab, then tick PCs in step 4 to reconstruct.")
                elif kind == 'recon_done':
                    self._finish(payload)
                    messagebox.showinfo("Done", f"Reconstruction saved in:\n{payload}")
                elif kind == 'error':
                    self._log(f"ERROR: {payload}")
                    self._finish(None)
                    messagebox.showerror("Error", payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_messages)

    def _finish(self, output_folder):
        self.busy.stop()
        self.run_btn.configure(state='normal')
        if self.pca_run is not None:
            self.recon_btn.configure(state='normal')
        if output_folder:
            self.last_output = output_folder
            self.open_btn.configure(state='normal')

    def _open_output(self):
        if not self.last_output:
            return
        if sys.platform == 'darwin':
            subprocess.run(['open', self.last_output])
        elif sys.platform == 'win32':
            os.startfile(self.last_output)
        else:
            subprocess.run(['xdg-open', self.last_output])

    def _log(self, msg):
        self.log_text.configure(state='normal')
        self.log_text.insert('end', msg + '\n')
        self.log_text.see('end')
        self.log_text.configure(state='disabled')


def main():
    root = tk.Tk()
    PCAApp(root)
    root.mainloop()
