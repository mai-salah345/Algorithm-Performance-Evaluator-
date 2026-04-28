import time
import threading
import copy

def execution_engine(user_code, array_input):
    # 1. أخذ نسخة من المصفوفة لحمايتها من التعديل (عشان الـ Sorting)
    safe_array = copy.deepcopy(array_input)
    
    # التعديل هنا: دمجنا مساحة العمل في قاموس واحد اسمه namespace
    namespace = {}
    result = {'execution_time': 0, 'error': None}

    def target_function():
        try:
            # 2. الترجمة (Compile) في مساحة عمل واحدة تدعم الـ Recursion
            exec(user_code, namespace)
            
            # استخراج الدالة
            func = namespace.get('my_algorithm')
            if not func:
                raise ValueError("Function 'my_algorithm' not found.")

            # 3. القياس الفعلي لتنفيذ الخوارزمية فقط!
            start_time = time.perf_counter()
            func(safe_array) 
            end_time = time.perf_counter()
            
            result['execution_time'] = end_time - start_time
        except Exception as e:
            result['error'] = str(e)

    thread = threading.Thread(target=target_function)
    thread.start()
    thread.join(timeout=5.0)

    if thread.is_alive():
        result['error'] = "Timeout: Code took too long!"

    return result


