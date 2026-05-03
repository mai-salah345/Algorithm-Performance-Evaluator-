from GUI_1 import AlgorithmEvaluatorApp
from complexity_engine3 import analyze_auto, analyze_manual, _compile_cache
import threading
import re
import numpy as np
 
class AppController(AlgorithmEvaluatorApp):
    def __init__(self):
        super().__init__()
 
    def _on_run(self):
        if self._running: return
        self._running = True
        self._run_btn.configure(state="disabled", text="⏳  Running…")
        self._status("Running analysis…")
        threading.Thread(target=self._run_analysis, daemon=True).start()
 
    def _run_analysis(self):
        try:
            code = self._editor.get("1.0", "end-1c")
            mode = self._mode.get()
            if mode == "Manual":
                sizes, times, res = self._run_manual(code)
            else:
                sizes, times, res = self._run_auto(code)
            best   = res["best_fit"]
            conf   = res["confidence_pct"]
            scores = {lbl: 1.0 - sc for lbl, sc in res["r2_rankings"]}
            self.after(0, lambda: self._update_results(sizes, times, best, scores, mode, conf))
        except Exception as e:
            msg = str(e)
            self.after(0, lambda: self._show_error(msg))
        finally:
            self._running = False
            self.after(0, lambda: self._run_btn.configure(state="normal", text="▶  Run Analysis"))
 
    def _run_manual(self, code):
        # ── 1. Parse user array ───────────────────────────────────────────────
        raw = self._array_entry.get().strip()
        try:
            user_arr = [float(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            raise RuntimeError("Array input must be comma-separated numbers.")
        if not user_arr:
            raise RuntimeError("Please enter at least one number.")
 
        n_user = len(user_arr)
 
        # ── 2. Get smart size range for this algorithm ────────────────────────
        custom_sizes, rep = self._detect_sizes_and_reps(code)
 
        # ── 3. Run full auto analysis to get best/avg/worst curves ───────────
        self._status("Running background analysis (best/avg/worst curves)…")
        res_auto = analyze_auto(code, sizes=custom_sizes, repeats=rep, include_cases=True)
 
        sizes       = res_auto["sizes"]
        avg_times   = res_auto["times"]
        best_times  = res_auto["best_case"]["times"]
        worst_times = res_auto["worst_case"]["times"]
 
        self._best_times_map  = dict(zip(sizes, best_times))
        self._worst_times_map = dict(zip(sizes, worst_times))
 
        # ── 4. Time the user's own array ─────────────────────────────────────
        res_user  = analyze_manual(code, [user_arr], repeats=5)
        user_time = res_user["times"][0]
 
        # ── 5. Find which case the user array is closest to ──────────────────
        idx        = int(np.argmin(np.abs(np.array(sizes) - n_user)))
        best_at_n  = best_times[idx]
        avg_at_n   = avg_times[idx]
        worst_at_n = worst_times[idx]
 
        dist_best  = abs(user_time - best_at_n)  / (best_at_n  + 1e-12)
        dist_avg   = abs(user_time - avg_at_n)   / (avg_at_n   + 1e-12)
        dist_worst = abs(user_time - worst_at_n) / (worst_at_n + 1e-12)
 
        case_label, case_color = min(
            ("Best Case",  dist_best,  "#3fb950"),
            ("Avg Case",   dist_avg,   "#58a6ff"),
            ("Worst Case", dist_worst, "#f85149"),
            key=lambda x: x[1]
        )[::2]
 
        self._manual_marker = (n_user, user_time, case_label, case_color)
        self._status(f"Your input ({n_user} elements) → {case_label}")
 
        return sizes, avg_times, res_auto
 
    def _run_auto(self, code):
        custom_sizes, rep = self._detect_sizes_and_reps(code)
        res = analyze_auto(code, sizes=custom_sizes, repeats=rep, include_cases=True)
 
        sizes = res["sizes"]
        self._best_times_map      = dict(zip(sizes, res["best_case"]["times"]))
        self._worst_times_map     = dict(zip(sizes, res["worst_case"]["times"]))
        self._best_engine_result  = res["best_case"]
        self._worst_engine_result = res["worst_case"]
 
        return sizes, res["times"], res
 
    # ── BUG 5 FIX: smart size detection ──────────────────────────────────────
    def _detect_sizes_and_reps(self, code):
        cl  = code.lower()
        
        # ── 1. الحماية من الانفجار الأسّي O(2^n) ──
        is_exp = (
            'fib(' in cl or
            '2**n' in cl or
            '2 ** n' in cl or
            bool(re.search(r'return\s+\w+\(n\s*-\s*1\)\s*\+\s*\w+\(n\s*-\s*2\)', cl))
        )
        if is_exp:
            return [5, 8, 10, 12, 14, 16, 18, 20], 3

        # ── 2. عد كل الحلقات (for و while) ──
        for_count   = len(re.findall(r'\bfor\b',   cl))
        while_count = len(re.findall(r'\bwhile\b', cl))
        total_loops = for_count + while_count

        if total_loops >= 3:
            # O(n^3) 
            return [10, 20, 40, 80, 120, 150, 200], 3
            
        elif total_loops == 2:
            # O(n^2) 
            return [10, 50, 100, 200, 400, 600, 800], 3
            
        elif total_loops == 1:
            # O(n) or O(n log n) 
            return [100, 500, 1000, 2000, 3000, 4000, 5000], 3
            
        else:
            # O(1) or O(log n)
            return [1000, 3000, 5000, 10000, 15000, 20000, 30000], 3
 
 
if __name__ == "__main__":
    app = AppController()
    app.mainloop()