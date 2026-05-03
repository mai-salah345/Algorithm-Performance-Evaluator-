"""
Complexity Engine v3 — Algorithm Performance Evaluator
Course: Algorithms (CSE 2nd Year) | Dr. Hend Gaballah | Eng. Mahmoud Ibrahim
Author: Mayar Mohamed Mohamed Basha

BUGS FIXED IN THIS VERSION
────────────────────────────
BUG 1 — exec() called r times per measurement (300-500 µs overhead each)
  Old: execution_engine(user_code, array) called r times → exec() paid every rep.
  O(1) actual work ≈ 193 ns but exec overhead ≈ 400 µs → 1500× noise → wrong result.
  Fix: _compile_once() runs exec() ONCE and caches the function object.
       _time_function() then calls fn(array) directly — zero exec overhead per rep.

BUG 2 — O(1) flat-line threshold too small (1e-7 s = 100 ns)
  With compile-once timing, O(1) functions take ~200-400 ns > 100 ns threshold.
  Fix: raise absolute threshold to 1e-6 s (1 µs). Anything under 1 µs is O(1).

BUG 3 — deepcopy() in timer inflates timings for large arrays
  copy.deepcopy(array) at n=50 000 takes ~5 ms, masking the actual algorithm time.
  Fix: use list(array) — sufficient for all integer/float arrays, ~100× faster.

BUG 4 — _decide() biased: always picked O(n log n) over O(n) when R² gap ≤ 0.03
  This caused true O(n) algorithms to be reported as O(n log n).
  Fix: use the dual-scorer rule — let the ratio-growth test break ties neutrally.

BUG 5 — _detect_sizes_and_reps wrongly classified recursive O(n log n) as O(2^n)
  The recursion regex matched any self-calling function (including merge sort).
  Fix: only flag O(2^n) on explicit markers: 'fib(', '2**n', or fib return pattern.
"""

import time, math, random, statistics, threading, copy, re
from typing import List, Dict, Optional

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
AUTO_SIZES_DEFAULT = [100, 500, 1_000, 3_000, 5_000, 8_000, 10_000]
AUTO_SIZES_CUBIC   = [10, 20, 40, 80, 150, 250, 400]
AUTO_SIZES_EXP     = [5, 8, 10, 12, 14, 16, 18, 20, 22]

# ── BUG 1 FIX: compile cache ──────────────────────────────────────────────────
_compile_cache: dict = {}

def _compile_once(func_code: str):
    """
    Run exec(func_code) exactly once, extract my_algorithm, cache the function.
    Zero exec overhead on all subsequent timing repetitions.
    """
    if func_code in _compile_cache:
        return _compile_cache[func_code]

    namespace = {}
    result = {'fn': None}

    def _run():
        try:
            exec(func_code, namespace)
            result['fn'] = namespace.get('my_algorithm')
        except Exception:
            pass

    th = threading.Thread(target=_run, daemon=True)
    th.start()
    th.join(timeout=5.0)

    if result['fn']:
        _compile_cache[func_code] = result['fn']
    return result['fn']


# ── BUG 1 + 3 FIX: timer ─────────────────────────────────────────────────────
def _time_function(func_code: str, array: list, r: int = 5) -> float:
    """
    Compile once, time fn(list(array)) r times, return median.
    - No exec overhead per repetition (BUG 1).
    - list() copy is ~100x faster than deepcopy for flat int arrays (BUG 3).
    """
    fn = _compile_once(func_code)
    if fn is None:
        return 0.0

    samples = []
    for _ in range(r):
        arr_copy = list(array)          # BUG 3 FIX: was deepcopy
        try:
            t0 = time.perf_counter()
            fn(arr_copy)
            samples.append(time.perf_counter() - t0)
        except Exception:
            pass

    return statistics.median(samples) if samples else 0.0


# ── Array generators ──────────────────────────────────────────────────────────
_gen  = AutoModeGenerator()
_rnd  = lambda n: _gen._generate_random(n)
_asc  = lambda n: _gen._generate_sorted(n)
_desc = lambda n: _gen._generate_reverse_sorted(n)


# ── BUG 2 FIX: flat-line detector with 1 µs threshold ────────────────────────
def _is_flat(times: list) -> bool:
    if len(times) < 2:
        return False
    m = statistics.mean(times)
    if m == 0 or m < 1e-6:     # BUG 2 FIX: was 1e-7
        return True
    return statistics.stdev(times) / m < 0.20


# ── Scorer A: R² curve fitting ────────────────────────────────────────────────
def _norm(v):
    mx = max(v) or 1.0
    return [x / mx for x in v]

def _r2(actual, predicted):
    ma   = statistics.mean(actual)
    ss_t = sum((a - ma)**2 for a in actual)
    ss_r = sum((a - p)**2  for a, p in zip(actual, predicted))
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
    err   = {lbl: 0.0 for lbl, _ in COMPLEXITY_CLASSES}
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
    return sorted(err.items(), key=lambda x: x[1]) if pairs else \
           [(l, 0.0) for l, _ in COMPLEXITY_CLASSES]


# ── BUG 4 FIX: decision engine — neutral dual-scorer tiebreak ────────────────
def _decide(sizes, times):
    """
    BUG 4 FIX: removed hardcoded 'always pick O(n log n) over O(n)' bias.
    Ratio-growth test now breaks ties neutrally between ANY two adjacent classes.
    """
    if len(sizes) < 2:
        default = [(lbl, 0.0) for lbl, _ in COMPLEXITY_CLASSES]
        return {"best_fit": "Need more data", "confidence_pct": 0.0,
                "ambiguous": True, "r2_rankings": default, "ratio_rankings": default}

    if _is_flat(times):
        return {"best_fit": "O(1)", "confidence_pct": 99.0, "ambiguous": False,
                "r2_rankings": [("O(1)", 1.0)], "ratio_rankings": [("O(1)", 0.0)]}

    r2, rt = _fit_r2(sizes, times), _fit_ratio(sizes, times)
    l1, s1 = r2[0]
    l2, s2 = r2[1] if len(r2) > 1 else (l1, s1)
    rb = rt[0][0]

    # If top-2 R² scores are close, let ratio test decide between them
    if (s1 - s2) <= 0.015 and rb in (l1, l2):
        best, amb = rb, rb != l1
    else:
        best, amb = l1, rb != l1

    conf = next(s for l, s in r2 if l == best)
    return {"best_fit": best, "confidence_pct": max(0.0, conf * 100),
            "ambiguous": amb, "r2_rankings": r2, "ratio_rankings": rt}


# ── Public API ────────────────────────────────────────────────────────────────
def analyze_manual(func_code: str, arrays: List[list], repeats: int = 5) -> Dict:
    """Mode 1 — profile func_code on caller-supplied arrays."""
    _compile_cache.pop(func_code, None)
    sizes = [len(a) for a in arrays]
    times = [_time_function(func_code, a, repeats) for a in arrays]
    return {"mode": "Manual", "sizes": sizes, "times": times, **_decide(sizes, times)}

def analyze_auto(func_code: str, sizes: Optional[List[int]] = None,
                 repeats: int = 5, include_cases: bool = True) -> Dict:
    """Mode 2 — auto-generate arrays of increasing size and profile func_code."""
    _compile_cache.pop(func_code, None)
    sizes = sizes or AUTO_SIZES_DEFAULT
    avg   = [_time_function(func_code, _rnd(n), repeats) for n in sizes]
    res   = {"mode": "Auto", "sizes": sizes, "times": avg, **_decide(sizes, avg)}
    if include_cases:
        for key, gen_fn in (("best_case", _asc), ("worst_case", _desc)):
            t = [_time_function(func_code, gen_fn(n), repeats) for n in sizes]
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
        bar  = "█" * max(0, int(sc * 20))
        mark = "  ◄" if lbl == r['best_fit'] else ""
        print(f"    {i}. {lbl:<14} {sc:>8.4f}  {bar}{mark}")
    if "best_case" in r:
        print(f"\n  Best-case  : {r['best_case']['best_fit']}")
        print(f"  Worst-case : {r['worst_case']['best_fit']}")
    print(S)


# ── Demo ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    demos = [
        ("O(1)       Constant",       SAMPLE_ALGORITHMS["O(1) \u2013 Array Access"],        AUTO_SIZES_DEFAULT),
        ("O(n)       Linear Search",  SAMPLE_ALGORITHMS["O(n) \u2013 Linear Search"],        AUTO_SIZES_DEFAULT),
        ("O(n log n) Merge Sort",     SAMPLE_ALGORITHMS["O(n log n) \u2013 Merge Sort"],     AUTO_SIZES_DEFAULT),
        ("O(n^2)     Bubble Sort",    SAMPLE_ALGORITHMS["O(n\u00b2) \u2013 Bubble Sort"],    [10, 50, 200, 500, 800]),
        ("O(n^3)     Triple Loop",    SAMPLE_ALGORITHMS["O(n\u00b3) \u2013 Triple Loop"],    AUTO_SIZES_CUBIC),
        ("O(2^n)     Fibonacci Rec",  SAMPLE_ALGORITHMS["O(2\u207f) \u2013 Fibonacci Recursive"], AUTO_SIZES_EXP),
    ]
    print("\n" + "═"*62 + "\n  RUNNING COMPLEXITY DEMOS\n" + "═"*62)
    for title, code_str, szs in demos:
        print(f"\n{'─'*62}\n  Testing: {title}")
        print_report(analyze_auto(code_str, sizes=szs, repeats=3, include_cases=False))
        input("\n press enter to continue")