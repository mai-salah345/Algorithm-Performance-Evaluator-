from GUI_1 import AlgorithmEvaluatorApp
from complexity_engine3 import analyze_auto, analyze_manual
import threading
import re

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
        raw = self._array_entry.get().strip()
        try:
            arr = [float(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            raise RuntimeError("Array input must be comma-separated numbers.")
        if not arr:
            raise RuntimeError("Please enter at least one number.")
        res = analyze_manual(code, [arr])
        return res["sizes"], res["times"], res
    
    def _run_auto(self, code):

    # تحويل الكود لـ lower case عشان البحث يبقى أسهل
        code_lower = code.lower()
        rep = 5 
    
    # 1. كشف الـ Exponential (O(2^n)) - بندور على نداء الدالة لنفسها (Recursion)
    # بنفترض إن اسم الدالة موجود في الكود وبيتم استدعاؤه مرتين أو فيه "2**n"
        if re.search(r"(\w+)\(.*\).*\1\(", code_lower) or "2**n" in code_lower or "fib(" in code_lower:
            custom_sizes = [5, 8, 10, 12, 14, 16, 18, 20]
            rep = 3
        
    # 2. كشف الـ Cubic (O(n^3)) - بنعد الـ 'for' المتداخلة (3 مستويات)
        elif code_lower.count("for ") >= 3:
            custom_sizes = [10, 20, 40, 80, 100, 120, 150]
        
    # 3. كشف الـ Quadratic (O(n^2)) - لو فيه 2 'for'
        elif code_lower.count("for ") == 2:
            custom_sizes = [10, 50, 100, 200, 400, 600, 800]
        
    # 4. كشف الـ Linear أو Log-Linear (O(n) / O(n log n))
    # لو فيه loop واحدة أو كلمات بتدل على تقسيم (زي Merge Sort)
        elif "for " in code_lower or "while " in code_lower or "split" in code_lower:
            custom_sizes = [1000, 3000, 5000, 8000, 12000, 16000, 20000]
            rep = 7 # زودنا التكرار عشان نفرق بين الـ n والـ n log n
        
    # 5. حالة الـ Constant أو Logarithmic (O(1) / O(log n))
        else:
        # هنا بقى السر: بنستخدم أحجام كبيرة جداً وتكرار عالي عشان نقتل الـ Noise
        # لأن الـ O(1) لو خدت أحجام صغيرة، الـ CPU Noise هيخليها تبان تربيعية
            custom_sizes = [10000, 20000, 40000, 60000, 80000, 100000]
            rep = 20 

    # تشغيل المحرك بنفس الطريقة
        res = analyze_auto(code, sizes=custom_sizes, repeats=rep, include_cases=True)
    
        sizes = res["sizes"]
        self._best_times_map = dict(zip(sizes, res["best_case"]["times"]))
        self._worst_times_map = dict(zip(sizes, res["worst_case"]["times"]))
        self._best_engine_result = res["best_case"]
        self._worst_engine_result = res["worst_case"]
    
        return sizes, res["times"], res
        
    
if __name__ == "__main__":
    app = AppController()
    app.mainloop()