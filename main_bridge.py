from GUI_1 import AlgorithmEvaluatorApp
from complexity_engine3 import analyze_auto, analyze_manual
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
        #هنا دي تظبيط لايه اللي هيحصل لما اعمل run لل algo
    
    def _run_analysis(self):
        try:
            code = self._editor.get("1.0", "end-1c") #دي بتاخد الكود من ال editor
            mode = self._mode.get() #دي بتشوف انا اخترت انهي mode
            if mode == "Manual":
                sizes, times, res = self._run_manual(code) # لو اخترت ال manual بينادي دالة ال run manual
            else:
                sizes, times, res = self._run_auto(code) # لو اخترت ال auto بينادي دالة ال run auto
            best  = res["best_fit"] #بعد ما كود ال run يخلص بياخد نتيجة الbest من ال res
            conf  = res["confidence_pct"] #بعد ما كود ال run يخلص بياخد نتيجة ال confidence من ال res
            scores = {lbl: 1.0 - sc for lbl, sc in res["r2_rankings"]} #بيحول قيمة ال r2 ويحولها لنسبةة علشان تظهر في ال candidate class
            self.after(0, lambda: self._update_results(sizes, times, best, scores, mode, conf)) #دي بتقول لل main thread اللي هو الواجهة اني كtarget thread خلصت حساباتي وبعد ما تفضي بعد 0 ميللي ثانية حدث الشاشة عن طريق دالة ال update results
        except Exception as e:
            msg = str(e)
            self.after(0, lambda: self._show_error(msg)) #هنا علشان لو حصل مشكلة يظهرها
        finally:
            self._running = False # هنا سواء الكود خلص او حصل مشكلة بيخلي ال running ب false علشان اعرف اعمل run تاني
            self.after(0, lambda: self._run_btn.configure(state="normal", text="▶  Run Analysis")) # بنبدء نرجع كل حاجة تاني
    
    def _run_manual(self, code):
        # ── 1. قراءة مصفوفة المستخدم ────────────────────────────────────
        raw = self._array_entry.get().strip()
        try:
            user_arr = [float(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            raise RuntimeError("Array input must be comma-separated numbers.")
        if not user_arr:
            raise RuntimeError("Please enter at least one number.")

        n_user = len(user_arr)

        # ── 2. جيب الـ sizes المناسبة لنوع الخوارزمية (نفس منطق Auto) ───
        custom_sizes, rep = self._detect_sizes_and_reps(code)

        # ── 3. شغّل Auto بالـ sizes الصح عشان تجيب الـ 3 curves ─────────
        self._status("Running background analysis (best/avg/worst curves)…")
        res_auto = analyze_auto(code, sizes=custom_sizes, repeats=rep, include_cases=True)

        sizes      = res_auto["sizes"]
        avg_times  = res_auto["times"]
        best_times = res_auto["best_case"]["times"]
        worst_times= res_auto["worst_case"]["times"]

        # حفظ الـ maps عشان _update_results يرسم الـ curves
        self._best_times_map  = dict(zip(sizes, best_times))
        self._worst_times_map = dict(zip(sizes, worst_times))

        # ── 4. قيس وقت تنفيذ مصفوفة المستخدم ────────────────────────────
        res_user  = analyze_manual(code, [user_arr], repeats=5)
        user_time = res_user["times"][0]

        # ── 5. حدد أقرب حالة للمستخدم ───────────────────────────────────
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
        )[::2]  # بناخد العنصر الأول والتالت بس (الاسم واللون)

        # ── 6. حفظ نقطة المستخدم عشان _update_results يرسمها ────────────
        self._manual_marker = (n_user, user_time, case_label, case_color)
        self._status(f"Your input ({n_user} elements) → {case_label}")

        return sizes, avg_times, res_auto
        



    def _run_auto(self, code):
        # دلوقتي بتستدعي الدالة المشتركة بدل تكرار المنطق
        custom_sizes, rep = self._detect_sizes_and_reps(code)

        res = analyze_auto(code, sizes=custom_sizes, repeats=rep, include_cases=True)

        sizes = res["sizes"]
        self._best_times_map      = dict(zip(sizes, res["best_case"]["times"]))
        self._worst_times_map     = dict(zip(sizes, res["worst_case"]["times"]))
        self._best_engine_result  = res["best_case"]
        self._worst_engine_result = res["worst_case"]

        return sizes, res["times"], res
        

    def _detect_sizes_and_reps(self, code):
        """
        نفس المنطق الذكي بتاع _run_auto — مشتركة بين Manual وAuto
        بتكشف نوع الخوارزمية من الكود وترجع (custom_sizes, rep)
        """
        code_lower = code.lower()
        rep = 5

        if re.search(r"(\w+)\(.*\).*\1\(", code_lower) or "2**n" in code_lower or "fib(" in code_lower:
            # O(2^n) — exponential
            custom_sizes = [5, 8, 10, 12, 14, 16, 18, 20]
            rep = 3

        elif code_lower.count("for ") >= 3:
            # O(n^3) — cubic
            custom_sizes = [10, 20, 40, 80, 100, 120, 150]

        elif code_lower.count("for ") == 2:
            # O(n^2) — quadratic
            custom_sizes = [10, 50, 100, 200, 400, 600, 800]

        elif "for " in code_lower or "while " in code_lower or "split" in code_lower:
            # O(n) / O(n log n) — linear / linearithmic
            custom_sizes = [1000, 3000, 5000, 8000, 12000, 16000, 20000]
            rep = 10

        else:
            # O(1) / O(log n) — constant / logarithmic
            custom_sizes = [10000, 20000, 40000, 60000, 80000, 100000]
            rep = 20

        return custom_sizes, rep
    
if __name__ == "__main__":
    app = AppController()
    app.mainloop()