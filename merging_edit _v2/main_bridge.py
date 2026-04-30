import statistics
from engine import execution_engine
from data_provider import AutoModeGenerator, SAMPLE_ALGORITHMS
 # استدعاء العقل التحليلي من الملف التالت
from complexity_engine3 import _decide

# ==========================================
# دالة الربط الأساسية (The Main Integration Loop)
# ==========================================

def run_comprehensive_analysis(algo_name):
    # 1. الحصول على كود الخوارزمية المختارة
    user_code = SAMPLE_ALGORITHMS[algo_name]
    generator = AutoModeGenerator()
    
    # 🔥 التحديد الذكي والأحجام الضخمة لفك الاشتباك بين n و nlogn
    if "O(2ⁿ)" in algo_name:
        n_min, n_max, step = 5, 20, 3       
    elif "O(n³)" in algo_name:
        n_min, n_max, step = 10, 100, 20    
    elif "O(n²)" in algo_name:
        n_min, n_max, step = 10, 1000, 200  
    else:
        # للخوارزميات السريعة جداً زي (Linear و Merge) لازم مصفوفات بالآلاف!
        n_min, n_max, step = 2000, 20000, 4000 
        
    print(f"\n--- Running Analysis for: {algo_name} ---")
    print(f"⚙️ Auto-Configured Sizes: min={n_min}, max={n_max}, step={step}")

    all_test_data = generator.generate_all_cases(n_min=n_min, n_max=n_max, step=step)
    analysis_results = {}

    for n in sorted(all_test_data.keys()):
        analysis_results[n] = {}
        for case_type in ['best', 'avg', 'worst']:
            array_to_test = all_test_data[n][case_type]
            
            # 🔥 الحل السحري لتنقية الضوضاء: تشغيل الكود 5 مرات وأخذ الوسيط (Median)
            times_for_this_size = []
            has_error = False
            error_msg = ""
            
            for _ in range(5):
                execution_output = execution_engine(user_code, array_to_test)
                if execution_output['error']:
                    has_error = True
                    error_msg = execution_output['error']
                    break
                times_for_this_size.append(execution_output['execution_time'])
            
            if has_error:
                print(f"  [!] Error at n={n} ({case_type}): {error_msg}")
                analysis_results[n][case_type] = None
            else:
                # نحسب الوسيط ونستبعد الأرقام الشاذة
                median_time = statistics.median(times_for_this_size)
                analysis_results[n][case_type] = median_time
                print(f"  Size {n:<5} | {case_type.upper():<6} | Time: {median_time:.8f}s")

    return analysis_results

# ==========================================
# حتة الـ Complexity (المكان اللي هنسيبه لزميلك)
# ==========================================
def bridge_to_complexity(results):
    # بنرتب الأحجام عشان الرسم البياني والتحليل يمشي صح من الصغير للكبير
    sizes = sorted(results.keys())
    # بنفلتر البيانات: بناخد بس الأحجام اللي الوقت بتاعها مش None (يعني مفيش فيها Error)
    actual_sizes = [n for n in sizes if results[n]['avg'] is not None]
    avg_times = [results[n]['avg'] for n in sizes if results[n]['avg'] is not None]
    # استدعاء العقل التحليلي من الملف التالت
    final_report = _decide(actual_sizes, avg_times)
    return final_report

if __name__ == "__main__":
    try:
        # غيرنا الاسم هنا 👇
        algo_to_test = "O(n³) – Triple Loop"
        
        # 2. تشغيل المحرك وجمع أوقات التنفيذ
        final_data = run_comprehensive_analysis(algo_to_test)
        
        # 3. تمرير النتائج للملف التالت عشان يحلل ويقولنا الـ Big O كام
        print("\n--- Generating Complexity Report ---")
        report = bridge_to_complexity(final_data)
        
        # 4. طباعة النتيجة النهائية بشكل شيك
        print(f"\nFinal Verdict: {report['best_fit']}")
        print(f"Confidence: {report['confidence_pct']:.2f}%")
        
        if report.get('ambiguous'):
            print("⚠ Note: The results were a bit close to other complexity classes.")
            
    except Exception as e:
        # لو حصل أي Error في الكود اللي فوق، هيدخل هنا بدل ما يقفل
        import traceback
        print("\nprogram stopped")
        print("-" * 40)
        traceback.print_exc()
        print("-" * 40)
        
    finally:
        # السطر ده هيتنفذ دايماً سواء البرنامج اشتغل صح أو ضرب Error
        input("\nPress Enter to exit...")