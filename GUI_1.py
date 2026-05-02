import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from complexity_engine3 import analyze_manual, analyze_auto
from data_provider import SAMPLE_ALGORITHMS

# ── Constants ─────────────────────────────────────────────────────────────────
BG, PANEL, BORDER = "#0d1117", "#161b22", "#30363d"
FG, BLUE, GREEN, RED, DIM = "#e6edf3", "#58a6ff", "#3fb950", "#f85149", "#8b949e"

COMPLEXITY_MODELS = {
    "O(1)":         lambda n: np.ones_like(n, dtype=float),
    "O(log n)":     lambda n: np.log2(n + 1),
    "O(n)":         lambda n: n.astype(float),
    "O(n log n)":   lambda n: n * np.log2(n + 1),
    "O(n²)":        lambda n: n ** 2.0,   "O(n^2)":       lambda n: n ** 2.0,
    "O(n² log n)":  lambda n: n**2 * np.log2(n+1), "O(n^2 log n)": lambda n: n**2 * np.log2(n+1),
    "O(n³)":        lambda n: n ** 3.0,   "O(n^3)":       lambda n: n ** 3.0,
    "O(2ⁿ)":        lambda n: 2.0 ** np.minimum(n, 30),
    "O(2^n)":       lambda n: 2.0 ** np.minimum(n, 30),
}
# دي علشان لما اجي ارسم الرسمة الصح مع الرسمة اللي طلعتلي

DESC = {
    "O(1)": "Constant", "O(log n)": "Logarithmic", "O(n)": "Linear",
    "O(n log n)": "Linearithmic", "O(n^2)": "Quadratic", "O(n²)": "Quadratic",
    "O(n^2 log n)": "Super-quadratic", "O(n² log n)": "Super-quadratic",
    "O(n^3)": "Cubic", "O(n³)": "Cubic",
    "O(2^n)": "Exponential", "O(2ⁿ)": "Exponential",
}
# دي علشان احسن شكل النتايج في ال gui

FUNCTION_TEMPLATE = """\
# do NOT rename the function 'my_algorithm'

def my_algorithm(arr):
    n = len(arr)
    # ── your code below ──────────────────────

    return arr
"""
#دي الحتة اللي بتتكتب في الeditor علشان تظهر لليوزر

def lbl(parent, text, fg=FG, bg=PANEL, **kw):
    return tk.Label(parent, text=text, fg=fg, bg=bg, **kw)

def sep(parent, row):
    tk.Frame(parent, bg=BORDER, height=1).grid(row=row, column=0, sticky="ew", padx=16)
#الدالتين دول لتظبيط الشكل مش الlogic

# ── Main App ──────────────────────────────────────────────────────────────────
class AlgorithmEvaluatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Algorithm Performance Evaluator")
        self.configure(bg=BG)
        self.geometry("1280x780")
        self.minsize(1000, 650)
        self._mode = tk.StringVar(value="Manual")
        self._running = False
        self._build_header()
        self._build_body()
        self._build_status_bar()
        #دي تجهيز للشكل وكدة يعني مش للوجيك برضو

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=PANEL, pady=8)
        hdr.pack(fill="x", side="top")
        for text, color in [("Algorithm ", FG), ("Performance", BLUE), (" Evaluator", FG)]:
            lbl(hdr, text, fg=color, bg=PANEL, font=("bold")).pack(side="left", padx=(16,0) if text=="Algorithm " else 0)

        right = tk.Frame(hdr, bg=PANEL)
        right.pack(side="right", padx=16)
        self._btn_manual = self._mode_btn(right, "Manual")
        self._btn_auto   = self._mode_btn(right, "Auto")
        self._btn_manual.pack(side="left", padx=2)
        self._btn_auto.pack(side="left", padx=2)
        self._run_btn = tk.Button(right, text="▶  Run Analysis", bg=GREEN, fg=BG,
                                  cursor="hand2", padx=14, pady=5, command=self._on_run)
        self._run_btn.pack(side="left", padx=(12, 0))
        self._refresh_mode_buttons()

    def _mode_btn(self, parent, label):
        return tk.Button(parent, text=label, cursor="hand2", padx=12, pady=5,
                         command=lambda l=label: self._set_mode(l))

    def _set_mode(self, mode):
        self._mode.set(mode)
        self._refresh_mode_buttons()
        if mode == "Manual":
            self._manual_row.grid(row=2, column=0, sticky="ew", pady=(6, 0))
            self._auto_row.grid_forget()
        else:
            self._auto_row.grid(row=2, column=0, sticky="ew", pady=(6, 0))
            self._manual_row.grid_forget()
            self._load_algo_to_editor()

    def _refresh_mode_buttons(self):
        active = self._mode.get()
        for btn, label in [(self._btn_manual, "Manual"), (self._btn_auto, "Auto")]:
            if label == active:
                btn.configure(bg=BLUE, fg=BG, font=("Segoe UI", 10, "bold"))
            else:
                btn.configure(bg=BORDER, fg=FG, font=("Segoe UI", 10))
    #هنا ده تظبيط لشكل وشغل ال header يعني مش للوجيك برضو

    # ── Body ──────────────────────────────────────────────────────────────────
    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)
        self._build_left_panel(body)
        self._build_right_panel(body)

    def _build_left_panel(self, parent):
        left = tk.Frame(parent, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        # Editor header
        hdr = tk.Frame(left, bg=PANEL, padx=8, pady=6)
        hdr.grid(row=0, column=0, sticky="ew")
        lbl(hdr, "CODE EDITOR", fg=DIM, bg=PANEL, font=("bold")).pack(side="left")
        lbl(hdr, " Python", fg=BLUE, bg=PANEL, font=("Segoe UI", 9)).pack(side="left")

        # Editor
        ef = tk.Frame(left, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        ef.grid(row=1, column=0, sticky="nsew", pady=(2, 0))
        ef.rowconfigure(0, weight=1); ef.columnconfigure(0, weight=1)
        self._editor = scrolledtext.ScrolledText(ef, bg=BG, fg="#79c0ff",
                                                  padx=10, pady=10, undo=True, wrap="none",
                                                  selectbackground="#264f78")
        self._editor.insert("1.0", FUNCTION_TEMPLATE)
        self._editor.grid(row=0, column=0, sticky="nsew")
#----------------------------------------------جديد --------------------------------------------------------
        self._editor.bind("<Control-c>", lambda e: self._editor.event_generate("<<Copy>>"))
        self._editor.bind("<Control-v>", lambda e: self._editor.event_generate("<<Paste>>"))
        self._editor.bind("<Control-x>", lambda e: self._editor.event_generate("<<Cut>>"))
        self._editor.bind("<Control-a>", lambda e: self._select_all(e))
        

        self._context_menu = tk.Menu(self._editor, tearoff=0, bg=PANEL, fg=FG, selectcolor=BLUE)
        self._context_menu.add_command(label="Copy", command=lambda: self._editor.event_generate("<<Copy>>"))
        self._context_menu.add_command(label="Paste", command=lambda: self._editor.event_generate("<<Paste>>"))
        self._context_menu.add_command(label="Cut", command=lambda: self._editor.event_generate("<<Cut>>"))
        self._context_menu.add_separator()
        self._context_menu.add_command(label="Select All", command=lambda: self._select_all())

        self._editor.bind("<Button-3>", lambda e: self._context_menu.post(e.x_root, e.y_root))
#----------------------------------------------جديد --------------------------------------------------------

        # Manual row
        self._manual_row = tk.Frame(left, bg=PANEL, padx=8, pady=6)
        lbl(self._manual_row, "Array input:", bg=PANEL).pack(side="left")
        self._array_entry = tk.Entry(self._manual_row, bg=BG, fg=FG, width=30)
        self._array_entry.insert(0, "5, 3, 8, 1, 9, 2")
        self._array_entry.pack(side="left", padx=(8, 0))
        lbl(self._manual_row, "(comma-separated numbers)", fg=DIM, bg=PANEL).pack(side="left", padx=6)
        self._manual_row.grid(row=2, column=0, sticky="ew", pady=(6, 0))

        # Auto row (dropdown)
        self._auto_row = tk.Frame(left, bg=PANEL, padx=8, pady=6)
        lbl(self._auto_row, "Algorithm:", bg=PANEL).pack(side="left")
        self._algo_var = tk.StringVar()
        algo_names = list(SAMPLE_ALGORITHMS.keys()) # هنا بياخد اسماء الخواريزميات المتخزنين علشان يعرضها في ال combo box
        self._algo_combo = ttk.Combobox(self._auto_row, textvariable=self._algo_var,
                                         values=algo_names, state="readonly", width=38)
        self._algo_combo.set(algo_names[0])
        self._algo_combo.pack(side="left", padx=(8, 0))
        self._algo_combo.bind("<<ComboboxSelected>>", lambda e: self._load_algo_to_editor())
        s = ttk.Style(); s.theme_use("default")
        s.configure("TCombobox", fieldbackground=BG, background=BORDER,
                    foreground=FG, selectbackground="#264f78", arrowcolor=BLUE)
 #----------------------------------------------جديد --------------------------------------------------------
    def _select_all(self, event=None):
        self._editor.tag_add("sel", "1.0", "end")
        return "break" 
 #----------------------------------------------جديد --------------------------------------------------------

    def _load_algo_to_editor(self):
        code = SAMPLE_ALGORITHMS.get(self._algo_var.get(), "")
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", code)
        #هنا دي اللي لما بختار حاجة معينة من ال combo box بتاخد الكود بتاعها اللي انا مخزناه وتعرضه في ال editor

    def _build_right_panel(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1); right.columnconfigure(0, weight=1)

        lbl(right, "ANALYSIS RESULTS", fg=DIM, bg=BG,
            font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=4, pady=(0,4))

        rf = tk.Frame(right, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        rf.grid(row=1, column=0, sticky="nsew")
        rf.rowconfigure(3, weight=1); rf.columnconfigure(0, weight=1)

        # Detected complexity
        det = tk.Frame(rf, bg=PANEL, padx=16, pady=12)
        det.grid(row=0, column=0, sticky="ew")
        lbl(det, "DETECTED COMPLEXITY", fg=DIM, bg=PANEL, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self._complexity_label = lbl(det, "—", fg=GREEN, bg=PANEL, font=("Segoe UI", 32, "bold"))
        self._complexity_label.pack(anchor="w")
        self._complexity_desc = lbl(det, "Run an analysis to see results", fg=DIM, bg=PANEL) #ده بيتغير لما اطلع الناتج
        self._complexity_desc.pack(anchor="w")

        # Confidence bar
        cf = tk.Frame(det, bg=PANEL); cf.pack(fill="x", pady=(6, 0))
        lbl(cf, "Confidence", fg=DIM, bg=PANEL).pack(anchor="w")
        bar_bg = tk.Frame(cf, bg=BORDER, height=6); bar_bg.pack(fill="x", pady=(2, 0))
        self._conf_bar = tk.Frame(bar_bg, bg=GREEN, height=6, width=0)
        self._conf_bar.place(x=0, y=0, height=6)

        sep(rf, 1)

        # Candidate classes
        cand = tk.Frame(rf, bg=PANEL, padx=16, pady=10)
        cand.grid(row=2, column=0, sticky="ew")
        lbl(cand, "CANDIDATE CLASSES", fg=DIM, bg=PANEL,
            font=("Segoe UI", 8, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,4))
        self._cand_frame = cand

        sep(rf, 3)

        # Chart
        cw = tk.Frame(rf, bg=PANEL); cw.grid(row=4, column=0, sticky="nsew", padx=16, pady=10)
        cw.rowconfigure(0, weight=1); cw.columnconfigure(0, weight=1)
        lbl(cw, "RUNTIME ACROSS INPUT SIZES", fg=DIM, bg=PANEL,
            font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self._fig = Figure(figsize=(5, 2.6), dpi=96, facecolor=PANEL)
        self._ax  = self._fig.add_subplot(111)
        self._style_axes()
        self._canvas = FigureCanvasTkAgg(self._fig, master=cw)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

        sep(rf, 5)

        # Best / Avg / Worst
        baw = tk.Frame(rf, bg=PANEL, padx=16, pady=10)
        baw.grid(row=6, column=0, sticky="ew")
        for label, attr in [("BEST", "_best_lbl"), ("AVG", "_avg_lbl"), ("WORST", "_worst_lbl")]:
            col = tk.Frame(baw, bg=PANEL); col.pack(side="left", expand=True)
            lbl(col, label, fg=DIM, bg=PANEL).pack()
            l = lbl(col, "—", fg=FG, bg=PANEL, font=("Segoe UI", 11, "bold")); l.pack()
            setattr(self, attr, l)

    # ── Status bar ────────────────────────────────────────────────────────────
    def _build_status_bar(self):
        bar = tk.Frame(self, bg=BORDER, height=24)
        bar.pack(fill="x", side="bottom")
        self._status_var = tk.StringVar(value="Ready.")
        tk.Label(bar, textvariable=self._status_var, fg=DIM, bg=BORDER,
                 anchor="w", padx=10).pack(fill="x")


    # ── Update UI ─────────────────────────────────────────────────────────────
    def _update_results(self, sizes, times, best, scores, mode, conf=None):
        self._complexity_label.configure(text=best, fg=GREEN)
        self._complexity_desc.configure(text=DESC.get(best, ""))

        # Confidence bar
        confidence = (conf / 100.0) if conf is not None else 0.0
        self._conf_bar.configure(width=max(int(self._conf_bar.master.winfo_width() * confidence), 2))

        # Candidate classes
        for w in self._cand_frame.grid_slaves():
            if int(w.grid_info()["row"]) > 0: w.destroy()
        top3   = sorted(scores.items(), key=lambda x: x[1])[:3]
        max_sc = max(s for _, s in top3) + 1e-12
        for i, (name, score) in enumerate(top3):
            tk.Label(self._cand_frame, text=name, font=("Segoe UI", 10, "bold"),
                     fg=FG, bg=PANEL, width=12, anchor="w").grid(row=i+1, column=0, sticky="w")
            bf = tk.Frame(self._cand_frame, bg=BORDER, height=8, width=160)
            bf.grid(row=i+1, column=1, padx=8, pady=2)
            tk.Frame(bf, bg=[GREEN, BLUE, "#d29922"][i], height=8,
                     width=max(4, int(160*(1-score/max_sc)))).place(x=0, y=0)

        # Chart
        sa, ta = np.array(sizes, dtype=float), np.array(times, dtype=float)
        self._ax.clear(); self._style_axes()
        if mode == "Auto" and hasattr(self, "_best_times_map"):
            b = [self._best_times_map[s] for s in sizes]
            w = [self._worst_times_map[s] for s in sizes]
            self._ax.fill_between(sa, b, w, color=BLUE, alpha=0.15)
            self._ax.plot(sa, b, color=GREEN, linewidth=1.5, linestyle="--", label="Best")
            self._ax.plot(sa, w, color=RED,   linewidth=1.5, linestyle="--", label="Worst")
            self._ax.plot(sa, ta, color=BLUE, linewidth=2.5, label="Avg")
            self._ax.legend(loc="upper left", fontsize=7, framealpha=0.3,
                            labelcolor=FG, facecolor=PANEL, edgecolor=BORDER)
        else:
            self._ax.plot(sa, ta, color=GREEN, linewidth=2.5, marker="o", markersize=5)

        if len(sa) >= 2 and ta.max() > 0 and best in COMPLEXITY_MODELS:
            pred  = COMPLEXITY_MODELS[best](sa)
            scale = np.dot(pred, ta) / (np.dot(pred, pred) + 1e-12)
            self._ax.plot(sa, scale*pred, color="#d29922", linewidth=1, linestyle=":", alpha=0.7,
                          label=best+" fit")

        self._ax.set_xlabel("Input size  n", fontsize=7, color=DIM)
        self._ax.set_ylabel("Time (s)",      fontsize=7, color=DIM)
        self._fig.tight_layout(); self._canvas.draw()

        # Best / Avg / Worst labels
        if mode == "Auto" and hasattr(self, "_best_engine_result"):
            self._best_lbl.configure( text=self._best_engine_result["best_fit"],  fg=GREEN)
            self._avg_lbl.configure(  text=best,                                   fg=BLUE)
            self._worst_lbl.configure(text=self._worst_engine_result["best_fit"],  fg=RED)
        else:
            for l in [self._best_lbl, self._avg_lbl, self._worst_lbl]:
                l.configure(text=best, fg=GREEN)

        self._status(f"Done. Estimated complexity: {best}")

    def _show_error(self, msg):
        self._complexity_label.configure(text="Error", fg=RED)
        self._complexity_desc.configure(text=msg[:120])
        self._status(f"Error: {msg[:80]}")
        messagebox.showerror("Execution Error", msg)

    def _style_axes(self):
        self._ax.set_facecolor(PANEL)
        self._ax.tick_params(colors=DIM, labelsize=7)
        for spine in self._ax.spines.values(): spine.set_edgecolor(BORDER)
        self._ax.xaxis.label.set_color(DIM)
        self._ax.yaxis.label.set_color(DIM)
        self._fig.patch.set_facecolor(PANEL)

    def _status(self, msg):
        self.after(0, lambda: self._status_var.set(msg))
