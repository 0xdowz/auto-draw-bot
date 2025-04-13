#!/usr/bin/env python3
"""
اختبار بسيط لتأكد من عمل Tkinter
"""

import sys

print("Python version:", sys.version)
print("Checking Tkinter...")

try:
    import tkinter as tk
    print("Tkinter is available.")
    
    # إنشاء نافذة بسيطة
    root = tk.Tk()
    root.title("اختبار Tkinter")
    root.geometry("300x200")
    
    # إضافة عنصر نصي
    label = tk.Label(root, text="إذا كنت ترى هذه النافذة، فإن Tkinter يعمل بشكل صحيح")
    label.pack(padx=20, pady=20)
    
    # إضافة زر للإغلاق
    button = tk.Button(root, text="إغلاق", command=root.destroy)
    button.pack(pady=10)
    
    print("Starting Tkinter mainloop...")
    root.mainloop()
    print("Tkinter window closed.")
    
except ImportError:
    print("ERROR: Tkinter is not available!")
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    
print("Test complete.") 