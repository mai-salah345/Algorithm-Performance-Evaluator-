import time
import threading
import copy

def execution_engine(user_code, array_input):
    safe_array = copy.deepcopy(array_input)
    namespace = {}
    result = {'execution_time': 0, 'error': None}

    def target_function():
        try:
            exec(user_code, namespace)

            func = namespace.get('my_algorithm')
            if not func:
                raise ValueError("Function 'my_algorithm' not found.")

            start_time = time.perf_counter()
            func(safe_array)
            end_time = time.perf_counter()

            result['execution_time'] = end_time - start_time

        except Exception as e:
            result['error'] = str(e)

    thread = threading.Thread(target=target_function, daemon=True)
    thread.start()
    thread.join(timeout=3.0)

    if thread.is_alive():
        result['error'] = "Timeout: Code took too long!"

    return result