"""
Complexity Engine v3 — Algorithm Performance Evaluator
Course: Algorithms (CSE 2nd Year) | Dr. Hend Gaballah | Eng. Mahmoud Ibrahim
Author: Mayar Mohamed Mohamed Basha
Detects: O(1), O(log n), O(n), O(n log n), O(n²), O(n² log n), O(n³), O(2^n)
Modes:    analyze_manual() → Mode 1  |  analyze_auto() → Mode 2
"""

import time, math, random, statistics
from typing import Callable, List, Tuple, Dict, Optional

# استيراد الأكواد اللي حفظناها عشان نبدل بيها
from data_provider import AutoModeGenerator, SAMPLE_ALGORITHMS
from engine import execution_engine

# ── Complexity class definitions ──────────────────────────────────────────────
log2 = math.log2
COMPLEXITY_CLASSES = [
    ("O(1)",         lambda n: 1.0),
    ("O(log n)",     lambda n: log2(n) if n > 1 else 1.0),
    ("O(n)",         lambda n: float(n)),
    ("O(n log n)",   lambda n: n * log2(n) if n > 1 else float(n)),
    ("O(n^2)",       lambda n: n ** 2),
    ("O(n^2 log n)", lambda n: n**2 * log2(n) if n > 1 else n**2),
    ("O(n^3)",       lambda n: n ** 3),
    ("O(2^n)",       lambda n: 2.0 ** n),
]

# ── Size presets ──────────────────────────────────────────────────────────────
AUTO_SIZES_DEFAULT = [10, 100, 500, 1_000, 3_000, 5_000, 10_000]
AUTO_SIZES_CUBIC   = [10, 20, 40, 80, 150, 250, 400]
AUTO_SIZES_EXP     = [5, 8, 10, 12, 14, 16, 18, 20, 22]

# ── Timer ─────────────────────────────────────────────────────────────────────
def _time_function(func_code: str, array: list, r: int = 5) -> float:
    # التبديل هنا: شلنا الـ copy والـ median اليدوي واستخدمنا الـ execution_engine
    results = []
    for _ in range(r):
        output = execution_engine(func_code, array)
        if not output['error']:
            results.append(output['execution_time'])
    return statistics.median(results) if results else 0.0

# ── Array generators ──────────────────────────────────────────────────────────
gen = AutoModeGenerator()

# التعديل هنا: ناديت دوال التوليد المباشرة عشان نمنع تكرار توليد الـ 3 حالات
def _rnd(n):  return gen._generate_random(n)
def _asc(n):  return gen._generate_sorted(n)
def _desc(n): return gen._generate_reverse_sorted(n)

# ── O(1) flat-line detector ───────────────────────────────────────────────────
def _is_flat(times):
    m = statistics.mean(times)
    return m < 1e-7 or (statistics.stdev(times) / m < 0.20)

# ── Scorer A: R² curve fitting ────────────────────────────────────────────────
def _norm(v):
    mx = max(v) or 1.0; return [x / mx for x in v]

def _r2(actual, predicted):
    ma = statistics.mean(actual)
    ss_t = sum((a - ma)**2 for a in actual)
    ss_r = sum((a - p)**2 for a, p in zip(actual, predicted))
    return 1.0 - ss_r / ss_t if ss_t else 1.0

def _fit_r2(sizes, times):
    nt = _norm(times)
    out = []
    for lbl, fn in COMPLEXITY_CLASSES:
        try:    out.append((lbl, round(_r2(nt, _norm([fn(float(n)) for n in sizes])), 6)))
        except: out.append((lbl, -999.0))
    return sorted(out, key=lambda x: x[1], reverse=True)

# ── Scorer B: ratio-growth test ───────────────────────────────────────────────
def _fit_ratio(sizes, times):
    err = {lbl: 0.0 for lbl, _ in COMPLEXITY_CLASSES}
    pairs = 0
    for i in range(1, len(sizes)):
        t1 = times[i - 1]
        if t1 <= 0: continue
        obs = times[i] / t1; pairs += 1
        n1, n2 = float(sizes[i - 1]), float(sizes[i])
        for lbl, fn in COMPLEXITY_CLASSES:
            try:
                g1 = fn(n1) or 1e-15; th = fn(n2) / g1
                if th > 0: err[lbl] += abs(obs - th) / th
            except: err[lbl] += 1e9
    return sorted(err.items(), key=lambda x: x[1]) if pairs else [(l, 0.0) for l, _ in COMPLEXITY_CLASSES]

# ── Decision engine ───────────────────────────────────────────────────────────
def _decide(sizes, times):
    if _is_flat(times):
        return {"best_fit": "O(1)", "confidence_pct": 99.0, "ambiguous": False,
                "r2_rankings": [("O(1)", 1.0)], "ratio_rankings": [("O(1)", 0.0)]}
    r2, rt = _fit_r2(sizes, times), _fit_ratio(sizes, times)
    l1, s1 = r2[0]; l2, _ = r2[1] if len(r2) > 1 else (l1, s1)
    rb = rt[0][0]
    if (s1 - (r2[1][1] if len(r2) > 1 else s1)) <= 0.015 and rb in (l1, l2):
        best, amb = rb, rb != l1
    else:
        best, amb = l1, rb != l1
    conf = next(s for l, s in r2 if l == best)
    return {"best_fit": best, "confidence_pct": max(0.0, conf * 100),
            "ambiguous": amb, "r2_rankings": r2, "ratio_rankings": rt}

# ── Public API ────────────────────────────────────────────────────────────────
def analyze_manual(func_code: str, arrays: List[list], repeats: int = 5) -> Dict:
    sizes = [len(a) for a in arrays]
    times = [_time_function(func_code, a, repeats) for a in arrays]
    return {"mode": "Manual", "sizes": sizes, "times": times, **_decide(sizes, times)}

def analyze_auto(func_code: str, sizes: Optional[List[int]] = None,
                 repeats: int = 5, include_cases: bool = True) -> Dict:
    sizes = sizes or AUTO_SIZES_DEFAULT
    avg   = [_time_function(func_code, _rnd(n), repeats) for n in sizes]
    res   = {"mode": "Auto", "sizes": sizes, "times": avg, **_decide(sizes, avg)}
    if include_cases:
        for key, gen_func in (("best_case", _asc), ("worst_case", _desc)):
            t = [_time_function(func_code, gen_func(n), repeats) for n in sizes]
            res[key] = {"times": t, **_decide(sizes, t)}
    return res

# ── Pretty printer ────────────────────────────────────────────────────────────
def print_report(r: Dict) -> None:
    S = "=" * 62
    print(f"{S}\n  COMPLEXITY REPORT  [{r.get('mode','?')} Mode]\n{S}")
    print(f"  Detected   : {r['best_fit']}{'  ⚠ scorers disagree' if r.get('ambiguous') else ''}")
    print(f"  Confidence : {r['confidence_pct']:.1f}%\n")
    print(f"  Sizes : {r['sizes']}")
    print(f"  Times : {[f'{t:.8f}' for t in r['times']]}\n")
    print("  R² Rankings  (higher = better):")
    for i, (lbl, sc) in enumerate(r["r2_rankings"][:6], 1):
        print(f"    {i}. {lbl:<14} {sc:>8.4f}  {'█'*max(0,int(sc*20))}{'  ◄' if lbl==r['best_fit'] else ''}")
    if "best_case" in r:
        print(f"\n  Best-case  : {r['best_case']['best_fit']}")
        print(f"  Worst-case : {r['worst_case']['best_fit']}")
    print(S)

# ── Demo ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    # التبديل هنا: سحبنا الأكواد من القاموس اللي استوردناه فوق مباشرة
    # مفيش داعي نعرف الدوال يدوي تاني هنا
    
    demos = [
        ("O(1)       Constant",      SAMPLE_ALGORITHMS["O(1) – Array Access"],   AUTO_SIZES_DEFAULT),
        ("O(n)       Linear Search",  SAMPLE_ALGORITHMS["O(n) – Linear Search"],  AUTO_SIZES_DEFAULT),
        ("O(n log n) Merge Sort",     SAMPLE_ALGORITHMS["O(n log n) – Merge Sort"], AUTO_SIZES_DEFAULT),
        ("O(n^2)     Bubble Sort",    SAMPLE_ALGORITHMS["O(n²) – Bubble Sort"],    [10,50,200,500,800]),
        ("O(n^3)     Triple Loop",    SAMPLE_ALGORITHMS["O(n³) – Matrix Multiply"],    AUTO_SIZES_CUBIC),
        ("O(2^n)     Fibonacci Rec", SAMPLE_ALGORITHMS["O(2ⁿ) – Fibonacci Recursive"], AUTO_SIZES_EXP),
    ]

    print("\n" + "═"*62 + "\n  RUNNING OPTIMIZED COMPLEXITY DEMOS\n" + "═"*62)
    for title, code_str, szs in demos:
        print(f"\n{'─'*62}\n  Testing: {title}")
        # بنبعت code_str للـ analyze_auto اللي بتبعتها للـ engine
        print_report(analyze_auto(code_str, sizes=szs, repeats=3, include_cases=False))
        input("\n press enter to continue")