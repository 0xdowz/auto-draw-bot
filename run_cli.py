#!/usr/bin/env python3
"""
AutoDraw CLI Version - نسخة مبسطة تعمل من سطر الأوامر
"""

import sys
import os
import traceback

# إضافة مجلد auto_draw لمسار البحث
sys.path.append(os.path.join(os.path.dirname(__file__), 'auto_draw'))

# استيراد الفئة الرئيسية
from auto_draw import AutoDraw

def run_cli():
    """تشغيل نسخة سطر الأوامر من البرنامج"""
    print("=== AutoDraw CLI ===")
    print("برنامج الرسم التلقائي - نسخة سطر الأوامر")
    print("-" * 40)
    
    # إنشاء كائن من الفئة الرئيسية
    app = AutoDraw()
    
    # تحميل الإعدادات الافتراضية
    app.load_settings()
    
    # عرض الإعدادات الحالية
    print(f"الإعدادات الحالية:")
    print(f"- التطبيق المستهدف: {app.target_app}")
    print(f"- أسلوب الرسم: {app.style}")
    print(f"- الدقة: {app.resolution}")
    print(f"- السرعة: {app.speed}")
    print(f"- تخطي اللون الأبيض: {app.skip_white}")
    print("-" * 40)
    
    # سؤال المستخدم عن مسار الصورة
    image_path = input("أدخل مسار الصورة للرسم: ")
    
    if not os.path.exists(image_path):
        print(f"خطأ: الملف {image_path} غير موجود!")
        return
    
    # تحميل الصورة
    print(f"جاري تحميل الصورة من {image_path}...")
    if not app.load_image(image_path):
        print("فشل في تحميل الصورة!")
        return
    
    print("تم تحميل الصورة بنجاح.")
    
    # معالجة الصورة
    print("جاري معالجة الصورة...")
    if not app.process_image():
        print("فشل في معالجة الصورة!")
        return
    
    print("تم معالجة الصورة بنجاح وهي جاهزة للرسم.")
    
    # التأكيد قبل الرسم
    print("\nتنبيه مهم:")
    print("1. تأكد من فتح التطبيق المستهدف (مثل برنامج الرسام)")
    print("2. حدد المنطقة التي تريد الرسم فيها")
    print("3. اضغط ESC في أي وقت لإيقاف الرسم")
    
    confirm = input("\nهل تريد البدء بالرسم الآن؟ (y/n): ")
    if confirm.lower() != 'y':
        print("تم إلغاء عملية الرسم.")
        return
    
    # عد تنازلي
    print("الرسم سيبدأ خلال:")
    for i in range(5, 0, -1):
        print(f"{i}...")
        import time
        time.sleep(1)
    
    # بدء الرسم
    print("جاري الرسم... اضغط ESC للإيقاف.")
    if app.draw_image():
        if app.stop_drawing:
            print("تم إيقاف الرسم بواسطة المستخدم.")
        else:
            print("تم الانتهاء من الرسم بنجاح!")
    else:
        print("حدث خطأ أثناء الرسم.")

if __name__ == "__main__":
    try:
        run_cli()
    except Exception as e:
        print("حدث خطأ أثناء تشغيل البرنامج:")
        print(str(e))
        print("\nتفاصيل الخطأ:")
        traceback.print_exc()
    
    input("\nاضغط Enter للإغلاق...") 