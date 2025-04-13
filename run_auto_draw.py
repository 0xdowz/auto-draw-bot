#!/usr/bin/env python3
"""
AutoDraw Entry Point - نقطة تشغيل برنامج الرسم التلقائي

هذا الملف يعمل كنقطة دخول لتشغيل برنامج AutoDraw مع إدارة الأخطاء
وإمكانية التشغيل في وضع سطر الأوامر.
"""

import sys
import os
import traceback
import time

# إضافة مجلد auto_draw لمسار البحث
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'auto_draw'))

def check_requirements():
    """التحقق من وجود المكتبات المطلوبة"""
    missing = []
    
    # قائمة المكتبات الضرورية
    required = [
        "pillow", "PIL",
        "pyautogui",
        "numpy",
        "keyboard"
    ]
    
    # التحقق من كل مكتبة
    for lib in required:
        try:
            __import__(lib)
        except ImportError:
            missing.append(lib)
    
    return missing

def run_gui():
    """تشغيل البرنامج في وضع الواجهة الرسومية"""
    print("جاري تشغيل البرنامج في وضع الواجهة الرسومية...")
    from auto_draw import main
    main()

def run_cli():
    """تشغيل البرنامج في وضع سطر الأوامر"""
    from auto_draw import AutoDraw, run_cli_mode, parse_arguments
    
    print("تشغيل البرنامج في وضع سطر الأوامر...")
    
    # تمرير الإعدادات الافتراضية للتشغيل في وضع سطر الأوامر
    args = parse_arguments()
    if args.image is None:
        img_path = input("أدخل مسار الصورة: ")
        if img_path and os.path.exists(img_path):
            args.image = img_path
        else:
            print("مسار الصورة غير صالح!")
            return
    
    # تشغيل وضع سطر الأوامر
    run_cli_mode(args)

if __name__ == "__main__":
    # التحقق من المتطلبات
    missing_libs = check_requirements()
    if missing_libs:
        print("خطأ: بعض المكتبات المطلوبة غير متوفرة:")
        for lib in missing_libs:
            print(f"- {lib}")
        print("\nيرجى تثبيت المكتبات المطلوبة باستخدام الأمر:")
        print("pip install -r auto_draw/requirements.txt")
        input("\nاضغط Enter للخروج...")
        sys.exit(1)
    
    # محاولة تشغيل البرنامج
    try:
        print("جاري تهيئة البرنامج...")
        try:
            # محاولة تشغيل وضع الواجهة الرسومية أولاً
            # التحقق من توفر Tkinter
            import tkinter
            run_gui()
        except (ImportError, Exception) as gui_error:
            # إذا فشلت الواجهة الرسومية، يتم تشغيل وضع سطر الأوامر
            print(f"تعذر تشغيل الواجهة الرسومية: {str(gui_error)}")
            print("جاري التحويل لوضع سطر الأوامر...")
            run_cli()
            
    except Exception as e:
        print("\n" + "="*50)
        print("حدث خطأ أثناء تشغيل البرنامج:")
        print(str(e))
        print("\nتفاصيل الخطأ:")
        traceback.print_exc()
        print("="*50)
        
        # طباعة معلومات إضافية للتشخيص
        print("\nمعلومات تشخيصية إضافية:")
        print(f"- Python: {sys.version}")
        print(f"- المسار: {os.getcwd()}")
        print(f"- مسارات البحث: {sys.path}")
        
        input("\nاضغط Enter للخروج...") 