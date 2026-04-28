import random

class AutoModeGenerator:
    def __init__(self):
        # القاموس الرئيسي اللي هيشيل كل المصفوفات
        self.all_test_cases = {}

    def generate_all_cases(self, n_min=10, n_max=1000, step=100):
        """
        دالة توليد البيانات بالمدى المطلوب (المهمة 4)
        """
        self.all_test_cases = {} # تصفير القاموس قبل البدء
        
        for n in range(n_min, n_max + 1, step):
            # إنشاء Sub-dictionary لكل حجم n لتمثيل الحالات الثلاث [cite: 30]
            self.all_test_cases[n] = {
                'best': list(range(n)),              # مصفوفة مرتبة تصاعدياً
                'avg': random.sample(range(n * 10), n), # مصفوفة عشوائية
                'worst': list(range(n, 0, -1))       # مصفوفة مرتبة تنازلياً
            }
        
        return self.all_test_cases



# --- تجربة الكود (Test) مع الطباعة المختصرة ---
if __name__ == "__main__":
    generator = AutoModeGenerator()
    
    # 1. توليد البيانات (من 10 لـ 1000 بخطوة 200)
    data = generator.generate_all_cases(n_min=10, n_max=1000, step=200)
    
    print("=== Detailed Case Preview (First 10 elements) ===\n")

    for n in sorted(data.keys()):
        print(f"📍 Input Size n = {n}:")
        
        for case_type in ['best', 'avg', 'worst']:
            array = data[n][case_type]
            
            # منطق الطباعة: لو أكتر من 10 عناصر، اطبع أول 10 وحط نقاط
            if len(array) > 10:
                preview = f"{array[:10]} ..."
            else:
                preview = f"{array}"
                
            print(f"  - {case_type.upper():<6}: {preview}")
        
        print("-" * 50)