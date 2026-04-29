import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time
import random
import math
import threading
import traceback
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from complexity_engine3 import analyze_manual, analyze_auto


# ─────────────────────────────────────────────
#  COMPLEXITY ESTIMATION ENGINE
# ─────────────────────────────────────────────

COMPLEXITY_MODELS = {
    "O(1)":          lambda n: np.ones_like(n, dtype=float),
    "O(log n)":      lambda n: np.log2(n + 1),
    "O(n)":          lambda n: n.astype(float),
    "O(n log n)":    lambda n: n * np.log2(n + 1),
    "O(n²)":         lambda n: n ** 2.0,
    "O(n² log n)":   lambda n: (n ** 2) * np.log2(n + 1),
    "O(n³)":         lambda n: n ** 3.0,
    "O(2ⁿ)":         lambda n: 2.0 ** np.minimum(n, 30),   # clamp to avoid overflow
}


def estimate_complexity(sizes, times):
    """Fit measured (size, time) pairs to known complexity models and return the best match."""
    sizes = np.array(sizes, dtype=float)
    times = np.array(times, dtype=float)

    # Normalise so we compare shapes, not magnitudes
    if times.max() == 0:
        return "O(1)", {k: 1.0 for k in COMPLEXITY_MODELS}

    scores = {}
    for name, model_fn in COMPLEXITY_MODELS.items():
        predicted = model_fn(sizes)
        # Scale predicted to match measured (least-squares scalar)
        scale = np.dot(predicted, times) / (np.dot(predicted, predicted) + 1e-12)
        fitted = scale * predicted
        # Relative residual (lower = better)
        residual = np.mean((times - fitted) ** 2) / (times.mean() ** 2 + 1e-12)
        scores[name] = residual

    best = min(scores, key=scores.get)
    return best, scores


# ─────────────────────────────────────────────
#  SAFE CODE EXECUTOR
# ─────────────────────────────────────────────

FUNCTION_TEMPLATE = """\
# do NOT rename the function 'my_algorithm'

def my_algorithm(arr):
    n = len(arr)
    # ── your code below ──────────────────────

    return arr
"""


def build_and_time(user_code: str, arr: list):
    """
    Compile user_code, call my_algorithm(arr), and return (result, elapsed_seconds).
    Raises RuntimeError on any problem.
    """
    namespace = {}
    try:
        exec(compile(user_code, "<user_code>", "exec"), namespace)
    except SyntaxError as e:
        raise RuntimeError(f"Syntax error in your code:\n{e}")

    if "my_algorithm" not in namespace:
        raise RuntimeError("Function 'my_algorithm' not found. Keep that exact name.")

    fn = namespace["my_algorithm"]
    start = time.perf_counter()
    result = fn(list(arr))          # pass a copy so repeated calls are independent
    elapsed = time.perf_counter() - start
    return result, elapsed

# ─────────────────────────────────────────────
#  MAIN APPLICATION WINDOW
# ─────────────────────────────────────────────

class AlgorithmEvaluatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Algorithm Performance Evaluator")
        self.configure(bg="#0d1117")
        self.geometry("1280x780")
        self.minsize(1000, 650)

        self._mode = tk.StringVar(value="Manual")   # "Manual" | "Auto"
        self._running = False

        self._build_header()
        self._build_body()
        self._build_status_bar()

    # ── HEADER ──────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg="#161b22", pady=8)
        hdr.pack(fill="x", side="top")

        # Title
        tk.Label(hdr, text="Algorithm ", font=("bold"),
                 fg="#e6edf3", bg="#161b22").pack(side="left", padx=(16, 0))
        tk.Label(hdr, text="Performance", font=("bold"),
                 fg="#58a6ff", bg="#161b22").pack(side="left")
        tk.Label(hdr, text=" Evaluator", font=("bold"),
                 fg="#e6edf3", bg="#161b22").pack(side="left")

        # Mode toggle + Run button on the right
        right = tk.Frame(hdr, bg="#161b22")
        right.pack(side="right", padx=16)

        self._btn_manual = self._mode_btn(right, "Manual")
        self._btn_auto   = self._mode_btn(right, "Auto")
        self._btn_manual.pack(side="left", padx=2)
        self._btn_auto.pack(side="left", padx=2)

        self._run_btn = tk.Button(right, text="▶  Run Analysis",
                                  bg="#3fb950", fg="#0d1117",
                                  cursor="hand2", padx=14, pady=5,
                                  command=self._on_run)
        self._run_btn.pack(side="left", padx=(12, 0))
        self._refresh_mode_buttons()

    def _mode_btn(self, parent, label):
        return tk.Button(parent, text=label,
                         cursor="hand2", padx=12, pady=5,
                         command=lambda l=label: self._set_mode(l))

    def _set_mode(self, mode):
        self._mode.set(mode)
        self._refresh_mode_buttons()
        # Show/hide manual input row
        if mode == "Manual":
            self._manual_row.pack(fill="x", pady=(6, 0))
        else:
            self._manual_row.pack_forget()

    def _refresh_mode_buttons(self):
        active = self._mode.get()
        for btn, label in [(self._btn_manual, "Manual"), (self._btn_auto, "Auto")]:
            if label == active:
                btn.configure(bg="#58a6ff", fg="#0d1117", font=("Segoe UI", 10, "bold"))
            else:
                btn.configure(bg="#30363d", fg="#e6edf3", font=("Segoe UI", 10))

    # ── BODY (two columns) ──────────────────

    def _build_body(self):
        body = tk.Frame(self, bg="#0d1117")
        body.pack(fill="both", expand=True, padx=12, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_right_panel(body)

    # ── LEFT: code editor + manual input ────

    def _build_left_panel(self, parent):
        left = tk.Frame(parent, bg="#0d1117")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        # Header row
        hdr = tk.Frame(left, bg="#161b22", padx=8, pady=6)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="CODE EDITOR", font=("bold"),
                 fg="#8b949e", bg="#161b22").pack(side="left")
        tk.Label(hdr, text=" Python", font=("Segoe UI", 9),
                 fg="#58a6ff", bg="#161b22").pack(side="left")

        # Editor
        editor_frame = tk.Frame(left, bg="#161b22", bd=1, relief="flat",
                                 highlightbackground="#30363d", highlightthickness=1)
        editor_frame.grid(row=1, column=0, sticky="nsew", pady=(2, 0))
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)

        self._editor = scrolledtext.ScrolledText(
            editor_frame, bg="#0d1117", fg="#79c0ff",
            padx=10, pady=10,
            undo=True, wrap="none",
            selectbackground="#264f78"
        )
        self._editor.insert("1.0", FUNCTION_TEMPLATE)
        self._editor.grid(row=0, column=0, sticky="nsew")

        # Manual input row (hidden when mode=Auto)
        self._manual_row = tk.Frame(left, bg="#161b22", padx=8, pady=6)
        tk.Label(self._manual_row, text="Array input:",
                 fg="#e6edf3", bg="#161b22").pack(side="left")
        self._array_entry = tk.Entry(self._manual_row,
                                     bg="#0d1117", fg="#e6edf3",
                                     width=30)
        self._array_entry.insert(0, "5, 3, 8, 1, 9, 2")
        self._array_entry.pack(side="left", padx=(8, 0))
        tk.Label(self._manual_row, text="(use comma between numbers)",
                 fg="#8b949e", bg="#161b22").pack(side="left", padx=6)
        self._manual_row.grid(row=0, column=0, sticky="ew", pady=(6, 0))
        
    # ── RIGHT: results panel ─────────────────

    def _build_right_panel(self, parent):
        right = tk.Frame(parent, bg="#0d1117")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        tk.Label(right, text="ANALYSIS RESULTS", 
                 font=("Segoe UI", 9, "bold"),
                 fg="#8b949e", bg="#0d1117").grid(row=0, column=0, sticky="w", padx=4, pady=(0, 4))

        results_frame = tk.Frame(right, bg="#161b22", bd=0,
                                  highlightbackground="#30363d", 
                                  highlightthickness=1)
        results_frame.grid(row=1, column=0, sticky="nsew")
        results_frame.rowconfigure(3, weight=1)
        results_frame.columnconfigure(0, weight=1)

        # ── Detected complexity ──
        det = tk.Frame(results_frame, bg="#161b22", padx=16, pady=12)
        det.grid(row=0, column=0, sticky="ew")
        tk.Label(det, text="DETECTED COMPLEXITY", font=("Segoe UI", 8, "bold"),
                 fg="#8b949e", bg="#161b22").pack(anchor="w")
        self._complexity_label = tk.Label(det, text="—", font=("Segoe UI", 32, "bold"),
                                           fg="#3fb950", bg="#161b22")
        self._complexity_label.pack(anchor="w")
        self._complexity_desc = tk.Label(det, text="Run an analysis to see results",
                                          fg="#8b949e", bg="#161b22")
        self._complexity_desc.pack(anchor="w")

        # Confidence bar
        conf_frame = tk.Frame(det, bg="#161b22")
        conf_frame.pack(fill="x", pady=(6, 0))
        tk.Label(conf_frame, text="Confidence", fg="#8b949e", bg="#161b22").pack(anchor="w")
        bar_bg = tk.Frame(conf_frame, bg="#30363d", height=6)
        bar_bg.pack(fill="x", pady=(2, 0))
        self._conf_bar = tk.Frame(bar_bg, bg="#3fb950", height=6, width=0)
        self._conf_bar.place(x=0, y=0, height=6)

        sep = tk.Frame(results_frame, bg="#30363d", height=1)
        sep.grid(row=1, column=0, sticky="ew", padx=16)

        # ── Candidate classes ──
        cand = tk.Frame(results_frame, bg="#161b22", padx=16, pady=10)
        cand.grid(row=2, column=0, sticky="ew")
        tk.Label(cand, text="CANDIDATE CLASSES", font=("Segoe UI", 8, "bold"),
                 fg="#8b949e", bg="#161b22").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        self._cand_frame = cand

        sep2 = tk.Frame(results_frame, bg="#30363d", height=1)
        sep2.grid(row=3, column=0, sticky="ew", padx=16)

        # ── Chart ──
        chart_wrapper = tk.Frame(results_frame, bg="#161b22")
        chart_wrapper.grid(row=4, column=0, sticky="nsew", padx=16, pady=10)
        chart_wrapper.rowconfigure(0, weight=1)
        chart_wrapper.columnconfigure(0, weight=1)

        tk.Label(chart_wrapper, text="RUNTIME ACROSS INPUT SIZES",
                 font=("Segoe UI", 8, "bold"), fg="#8b949e", bg="#161b22").pack(anchor="w")

        self._fig = Figure(figsize=(5, 2.6), dpi=96, facecolor="#161b22")
        self._ax  = self._fig.add_subplot(111)
        self._style_axes()
        self._canvas = FigureCanvasTkAgg(self._fig, master=chart_wrapper)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

        sep3 = tk.Frame(results_frame, bg="#30363d", height=1)
        sep3.grid(row=5, column=0, sticky="ew", padx=16)

        # ── Best / Avg / Worst footer ──
        baw = tk.Frame(results_frame, bg="#161b22", padx=16, pady=10)
        baw.grid(row=6, column=0, sticky="ew")
        for i, (label, var_name) in enumerate(
                [("BEST", "_best_lbl"), ("AVG", "_avg_lbl"), ("WORST", "_worst_lbl")]):
            col = tk.Frame(baw, bg="#161b22")
            col.pack(side="left", expand=True)
            tk.Label(col, text=label, fg="#8b949e", bg="#161b22").pack()
            lbl = tk.Label(col, text="—", font=("Segoe UI", 11, "bold"), fg="#e6edf3", bg="#161b22")
            lbl.pack()
            setattr(self, var_name, lbl)

    # ── STATUS BAR ───────────────────────────

    def _build_status_bar(self):
        bar = tk.Frame(self, bg="#30363d", height=24)
        bar.pack(fill="x", side="bottom")
        self._status_var = tk.StringVar(value="Ready.")
        tk.Label(bar, textvariable=self._status_var,
                 fg="#8b949e", bg="#30363d", anchor="w", padx=10).pack(fill="x")

    # ─────────────────────────────────────────
    #  RUN ANALYSIS
    # ─────────────────────────────────────────

    def _on_run(self):
        if self._running:
            return
        self._running = True
        self._run_btn.configure(state="disabled", text="⏳  Running…")
        self._status("Running analysis…")
        thread = threading.Thread(target=self._run_analysis, daemon=True)
        thread.start()

    def _run_analysis(self):
        try:
            code = self._editor.get("1.0", "end-1c")
            mode = self._mode.get()

            if mode == "Manual":
                sizes, times = self._run_manual(code)
            else:
                sizes, times = self._run_auto(code)

            best_complexity, scores = estimate_complexity(sizes, times)
            self.after(0, lambda: self._update_results(sizes, times, best_complexity, scores, mode))

        except Exception as e:
            msg = str(e)
            self.after(0, lambda: self._show_error(msg))
        finally:
            self._running = False
            self.after(0, lambda: self._run_btn.configure(state="normal", text="▶  Run Analysis"))

    def _run_manual(self, code):
        raw = self._array_entry.get().strip()
        try:
            base_arr = [float(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            raise RuntimeError("Array input must be comma-separated numbers.")
        if not base_arr:
            raise RuntimeError("Please enter at least one number.")
        result = analyze_manual(code, [base_arr])
        return result["sizes"], result["times"]

    def _run_auto(self, code):
        result = analyze_auto(code, repeats=5, include_cases=True)
        sizes = result["sizes"]
        self._best_times_map  = dict(zip(sizes, result["best_case"]["times"]))
        self._worst_times_map = dict(zip(sizes, result["worst_case"]["times"]))
        self._avg_times_map   = dict(zip(sizes, result["times"]))
        return sizes, result["times"]

    # ─────────────────────────────────────────
    #  UPDATE UI AFTER RUN
    # ─────────────────────────────────────────

    def _update_results(self, sizes, times, best_complexity, scores, mode):
        # ── Complexity label ──
        self._complexity_label.configure(text=best_complexity, fg="#3fb950")
        desc_map = {
            "O(1)":        "Constant ",
            "O(log n)":    "Logarithmic ",
            "O(n)":        "Linear",
            "O(n log n)":  "Linearithmic",
            "O(n²)":       "Quadratic",
            "O(n² log n)": "Super-quadratic",
            "O(n³)":       "Cubic",
            "O(2ⁿ)":       "Exponential",
        }
        self._complexity_desc.configure(text=desc_map.get(best_complexity, ""))

        # ── Confidence bar ──
        # Confidence ≈ how much better the best score is vs the second-best
        sorted_scores = sorted(scores.values())
        best_score = sorted_scores[0]
        second     = sorted_scores[1] if len(sorted_scores) > 1 else best_score * 2
        confidence = min(1.0, max(0.0, 1.0 - best_score / (second + 1e-12)))
        bar_width = int(self._conf_bar.master.winfo_width() * confidence)
        self._conf_bar.configure(width=max(bar_width, 2))

        # ── Candidate classes ──
        for w in list(self._cand_frame.grid_slaves()):
            if int(w.grid_info()["row"]) > 0:
                w.destroy()

        top3 = sorted(scores.items(), key=lambda x: x[1])[:3]
        max_bar = max(s for _, s in top3) + 1e-12
        colors = ["#3fb950", "#58a6ff", "#d29922"]
        for i, (name, score) in enumerate(top3):
            row = i + 1
            tk.Label(self._cand_frame, text=name, font=("Segoe UI", 10, "bold"),
                     fg="#e6edf3", bg="#161b22", width=12, anchor="w").grid(row=row, column=0, sticky="w")
            bar_frame = tk.Frame(self._cand_frame, bg="#30363d", height=8, width=160)
            bar_frame.grid(row=row, column=1, padx=8, pady=2)
            bar_len = max(4, int(160 * (1 - score / max_bar)))
            tk.Frame(bar_frame, bg=colors[i], height=8, width=bar_len).place(x=0, y=0)

        # ── Chart ──
        self._ax.clear()
        self._style_axes()
        sizes_arr = np.array(sizes, dtype=float)
        times_arr = np.array(times, dtype=float)

        if mode == "Auto" and hasattr(self, "_best_times_map"):
            b = [self._best_times_map[s] for s in sizes]
            w = [self._worst_times_map[s] for s in sizes]
            self._ax.fill_between(sizes_arr, b, w, color="#58a6ff", alpha=0.15)
            self._ax.plot(sizes_arr, b, color="#3fb950", linewidth=1.5, label="Best", linestyle="--")
            self._ax.plot(sizes_arr, w, color="#f85149", linewidth=1.5, label="Worst", linestyle="--")
            self._ax.plot(sizes_arr, times_arr, color="#58a6ff", linewidth=2.5, label="Avg")
            self._ax.legend(loc="upper left", fontsize=7, framealpha=0.3,
                            labelcolor="#e6edf3", facecolor="#161b22", edgecolor="#30363d")
        else:
            self._ax.plot(sizes_arr, times_arr, color="#3fb950", linewidth=2.5, marker="o",
                          markersize=5, label="Time")

        # Overlay fitted complexity curve (dashed)
        if len(sizes_arr) >= 2 and times_arr.max() > 0:
            fn = COMPLEXITY_MODELS[best_complexity]
            predicted = fn(sizes_arr)
            scale = np.dot(predicted, times_arr) / (np.dot(predicted, predicted) + 1e-12)
            self._ax.plot(sizes_arr, scale * predicted, color="#d29922",
                          linewidth=1, linestyle=":", alpha=0.7, label=best_complexity+" fit")

        self._ax.set_xlabel("Input size  n", fontsize=7, color="#8b949e")
        self._ax.set_ylabel("Time (s)", fontsize=7, color="#8b949e")
        self._fig.tight_layout()
        self._canvas.draw()

        # ── Best / Avg / Worst labels ──
        if mode == "Auto" and hasattr(self, "_best_times_map"):
            b_cx, _, b_sc = estimate_complexity(sizes, [self._best_times_map[s] for s in sizes])
            w_cx, _, w_sc = estimate_complexity(sizes, [self._worst_times_map[s] for s in sizes])
            self._best_lbl.configure(text=b_cx, fg="#3fb950")
            self._avg_lbl.configure(text=best_complexity, fg="#58a6ff")
            self._worst_lbl.configure(text=w_cx, fg="#f85149")
        else:
            for lbl in [self._best_lbl, self._avg_lbl, self._worst_lbl]:
                lbl.configure(text=best_complexity, fg="#3fb950")

        self._status(f"Done. Estimated complexity: {best_complexity}")

    def _show_error(self, msg):
        self._complexity_label.configure(text="Error", fg="#f85149")
        self._complexity_desc.configure(text=msg[:120])
        self._status(f"Error: {msg[:80]}")
        messagebox.showerror("Execution Error", msg)

    # ─────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────

    def _style_axes(self):
        ax = self._ax
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#8b949e", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")
        ax.xaxis.label.set_color("#8b949e")
        ax.yaxis.label.set_color("#8b949e")
        self._fig.patch.set_facecolor("#161b22")

    def _status(self, msg):
        self.after(0, lambda: self._status_var.set(msg))


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = AlgorithmEvaluatorApp()
    app.mainloop()