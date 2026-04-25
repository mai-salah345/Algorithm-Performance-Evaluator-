"""
Complexity Engine v3 — Algorithm Performance Evaluator
Course: Algorithms (CSE 2nd Year) | Dr. Hend Gaballah | Eng. Mahmoud Ibrahim
Auther: Mayar Mohamed Mohamed Basha
Detects: O(1), O(log n), O(n), O(n log n), O(n²), O(n² log n), O(n³), O(2^n)
Modes:   analyze_manual() → Mode 1  |  analyze_auto() → Mode 2
"""

import time, math, random, statistics
from typing import Callable, List, Tuple, Dict, Optional

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

# ── Timer (subtracts array-copy baseline so O(1) isn't mis-timed as O(n)) ────
def _time_function(func: Callable, array: list, r: int = 5) -> float:
    def _copy(a):
        t = time.perf_counter(); _ = list(a); return time.perf_counter() - t
    def _run(f, a):
        c = list(a); t = time.perf_counter(); f(c); return time.perf_counter() - t
    return max(0.0, statistics.median(_run(func, array) for _ in range(r))
                  - statistics.median(_copy(array)      for _ in range(r)))

# ── Array generators ──────────────────────────────────────────────────────────
_rnd  = lambda n: [random.randint(0, n * 10) for _ in range(n)]
_asc  = lambda n: list(range(n))
_desc = lambda n: list(range(n, 0, -1))

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
def analyze_manual(func: Callable, arrays: List[list], repeats: int = 5) -> Dict:
    """Mode 1 — profile func on caller-supplied arrays."""
    sizes = [len(a) for a in arrays]
    times = [_time_function(func, a, repeats) for a in arrays]
    return {"mode": "Manual", "sizes": sizes, "times": times, **_decide(sizes, times)}

def analyze_auto(func: Callable, sizes: Optional[List[int]] = None,
                 repeats: int = 5, include_cases: bool = True) -> Dict:
    """Mode 2 — auto-generate random arrays of increasing size and profile func."""
    sizes = sizes or AUTO_SIZES_DEFAULT
    avg   = [_time_function(func, _rnd(n), repeats) for n in sizes]
    res   = {"mode": "Auto", "sizes": sizes, "times": avg, **_decide(sizes, avg)}
    if include_cases:
        for key, gen in (("best_case", _asc), ("worst_case", _desc)):
            t = [_time_function(func, gen(n), repeats) for n in sizes]
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
    print("\n  Ratio-Test Rankings  (lower error = better):")
    for i, (lbl, err) in enumerate(r["ratio_rankings"][:4], 1):
        print(f"    {i}. {lbl:<14} err={err:.4f}{'  ◄' if i==1 else ''}")
    if "best_case" in r:
        print(f"\n  Best-case  : {r['best_case']['best_fit']}")
        print(f"  Worst-case : {r['worst_case']['best_fit']}")
    print(S)

# ── Demo ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    def constant(arr):           return arr[0] if arr else None
    def linear_search(arr):
        for x in arr:
            if x == -1: return True
        return False
    def merge_sort(arr):
        if len(arr) <= 1: return arr
        m = len(arr)//2; l, r = merge_sort(arr[:m]), merge_sort(arr[m:])
        out=[]; i=j=0
        while i<len(l) and j<len(r):
            if l[i]<=r[j]: out.append(l[i]); i+=1
            else:           out.append(r[j]); j+=1
        return out + l[i:] + r[j:]
    def bubble_sort(arr):
        n=len(arr)
        for i in range(n):
            for j in range(n-i-1):
                if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]
        return arr
    def triple_loop(arr):
        n=len(arr); acc=0
        for i in range(n):
            for j in range(n):
                for k in range(n): acc+=arr[i]-arr[k]+arr[j]
        return acc
    def fibonacci_recursive(arr):
        def fib(x): return x if x<=1 else fib(x-1)+fib(x-2)
        return fib(len(arr))

    demos = [
        ("O(1)       Constant",      constant,            AUTO_SIZES_DEFAULT),
        ("O(n)       Linear Search", linear_search,       AUTO_SIZES_DEFAULT),
        ("O(n log n) Merge Sort",    merge_sort,          AUTO_SIZES_DEFAULT),
        ("O(n^2)     Bubble Sort",   bubble_sort,         [10,50,200,500,800,1_000,1_500]),
        ("O(n^3)     Triple Loop",   triple_loop,         AUTO_SIZES_CUBIC),
        ("O(2^n)     Fibonacci Rec", fibonacci_recursive, AUTO_SIZES_EXP),
    ]

    print("\n" + "═"*62 + "\n  RUNNING ALL 6 COMPLEXITY CLASS DEMOS\n" + "═"*62)
    for title, fn, szs in demos:
        print(f"\n{'─'*62}\n  Testing: {title}")
        print_report(analyze_auto(fn, sizes=szs, repeats=5, include_cases=False))
        input("\n press enter to continue")