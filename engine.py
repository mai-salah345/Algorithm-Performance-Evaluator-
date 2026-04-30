import time
import threading
from data_provider import AutoModeGenerator, SAMPLE_ALGORITHMS

def execution_engine(user_code, array_input):

    local_vars = {'arr': array_input}
    result = {'execution_time': 0, 'error': None}

    def target_function():
        try:
            start_time = time.perf_counter()
            exec(user_code, local_vars, local_vars)
            end_time = time.perf_counter()
            result['execution_time'] = end_time - start_time
        except Exception as e:
            result['error'] = str(e)

   
    thread = threading.Thread(target=target_function)
    thread.start()
    thread.join()

    return result


generator = AutoModeGenerator()
data = generator.generate_all_cases(n_min=10, n_max=100, step=20)
code_to_test = SAMPLE_ALGORITHMS["O(n²) – Bubble Sort"]

output = execution_engine(code_to_test, data[10]['avg'])

if output['error']:
    print(f"Error: {output['error']}")
else:
    print(f"Time Taken: {output['execution_time']:.6f} seconds")