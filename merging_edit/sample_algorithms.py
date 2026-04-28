SAMPLE_ALGORITHMS = {
    "O(1) – Array Access": """\
def my_algorithm(arr):
    # O(1) - Constant time
    if len(arr) == 0:
        return None
    return arr[0]
""",
    "O(n) – Linear Search": """\
def my_algorithm(arr):
    # O(n) - Linear search
    target = arr[-1] if arr else 0
    for item in arr:
        if item == target:
            return item
    return -1
""",
    "O(n log n) – Merge Sort": """\
def my_algorithm(arr):
    # O(n log n) - Merge Sort
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = my_algorithm(arr[:mid])
    right = my_algorithm(arr[mid:])
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
""",
    "O(n²) – Bubble Sort": """\
def my_algorithm(arr):
    # O(n^2) - Bubble Sort
    arr = arr[:]
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
""",
   "O(n³) – Triple Loop": """\
def my_algorithm(arr):
    # O(n^3) - True Cubic Time
    n = len(arr)
    acc = 0
    for i in range(n):
        for j in range(n):
            for k in range(n):
                acc += 1
    return acc
""",
    "O(2ⁿ) – Fibonacci Recursive": """\
def my_algorithm(arr):
    # O(2^n) - Exponential: Recursive Fibonacci
    # WARNING: Only works for small n (≤ 25) due to exponential growth
    def fib(n):
        if n <= 1:
            return n
        return fib(n-1) + fib(n-2)
    n = min(len(arr), 20)  # cap at 20 to prevent freezing
    return fib(n)
""",
}