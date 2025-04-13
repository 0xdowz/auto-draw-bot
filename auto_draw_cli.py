#!/usr/bin/env python3
"""
برنامج الرسم التلقائي المبسط - نسخة سطر الأوامر

هذا البرنامج مصمم للعمل في وضع سطر الأوامر فقط بدون الحاجة للواجهة الرسومية
ويتضمن تخطي اللون الأبيض لتسريع الرسم
"""

import os
import sys
import time
import json
import logging
import argparse
from PIL import Image
import numpy as np
import pyautogui
import keyboard

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_draw_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutoDrawCLI")

# تعطيل ميزة الأمان في PyAutoGUI
pyautogui.FAILSAFE = False

class SimpleAutoDraw:
    """نسخة مبسطة من فئة AutoDraw"""
    
    def __init__(self):
        self.image = None
        self.processed_image = None
        self.canvas_area = None  # (x1, y1, x2, y2)
        self.speed = 0.001
        self.resolution = 1.0
        self.skip_white = True
        self.stop_drawing = False
        self.palette = []
        
    def load_image(self, image_path):
        """تحميل صورة من مسار"""
        try:
            logger.info(f"تحميل الصورة من: {image_path}")
            self.image = Image.open(image_path).convert("RGBA")
            logger.info(f"تم تحميل الصورة: {self.image.width}x{self.image.height} بكسل")
            return True
        except Exception as e:
            logger.error(f"فشل تحميل الصورة: {e}")
            return False
            
    def process_image(self):
        """معالجة الصورة للرسم مع تطبيق التحسينات"""
        if not self.image:
            logger.error("لم يتم تحميل صورة")
            return False
            
        try:
            # نسخة من الصورة الأصلية
            img = self.image.copy()
            
            # تغيير الحجم حسب دقة الإخراج
            if self.resolution != 1.0:
                width, height = img.size
                new_width = int(width * self.resolution)
                new_height = int(height * self.resolution)
                img = img.resize((new_width, new_height), Image.LANCZOS)
                logger.info(f"تغيير حجم الصورة إلى {new_width}x{new_height}")
            
            # معالجة البكسلات البيضاء
            if self.skip_white:
                # التحويل لوضع RGBA إذا لم يكن كذلك بالفعل
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                
                pixel_data = img.load()
                width, height = img.size
                
                # تحديد البكسلات البيضاء كشفافة
                white_threshold = 240
                white_count = 0
                
                for y in range(height):
                    for x in range(width):
                        r, g, b, a = pixel_data[x, y]
                        # التحقق إذا كان البكسل أبيض أو قريب من الأبيض
                        if r >= white_threshold and g >= white_threshold and b >= white_threshold:
                            # جعل البكسل الأبيض شفافًا
                            pixel_data[x, y] = (r, g, b, 0)
                            white_count += 1
                
                # إحصائيات
                white_percentage = (white_count / (width * height)) * 100
                logger.info(f"تم تحديد {white_count} بكسل أبيض كشفاف ({white_percentage:.1f}% من الصورة)")
            
            # تخزين الصورة المعالجة
            self.processed_image = img
            logger.info("تم معالجة الصورة بنجاح")
            return True
            
        except Exception as e:
            logger.error(f"فشل معالجة الصورة: {e}")
            return False
    
    def stop_drawing_callback(self):
        """استدعاء للتوقف عن الرسم عند الضغط على Esc"""
        self.stop_drawing = True
        logger.info("تم طلب إيقاف الرسم")
    
    def draw_image(self):
        """رسم الصورة المعالجة مع تخطي البكسلات البيضاء/الشفافة"""
        if not self.processed_image:
            logger.error("لم تتم معالجة الصورة بعد")
            return False
            
        logger.info("بدء عملية الرسم...")
        
        # إعادة تعيين علامة التوقف
        self.stop_drawing = False
        
        # تثبيت معالج مفتاح ESC
        keyboard.on_press_key("esc", lambda _: self.stop_drawing_callback())
        
        try:
            # الحصول على بيانات الصورة
            img_data = np.array(self.processed_image)
            height, width = img_data.shape[:2]
            
            # إذا لم يتم تعيين منطقة الرسم، استخدم وسط الشاشة
            if not self.canvas_area:
                logger.info("لم يتم تعيين منطقة الرسم، استخدام وسط الشاشة")
                screen_width, screen_height = pyautogui.size()
                x1 = (screen_width - width) // 2
                y1 = (screen_height - height) // 2
                self.canvas_area = (x1, y1, x1 + width, y1 + height)
                logger.info(f"منطقة الرسم التلقائية: {self.canvas_area}")
            
            x1, y1, x2, y2 = self.canvas_area
            
            # حساب حجم البكسل
            pixel_width = (x2 - x1) / width
            pixel_height = (y2 - y1) / height
            
            # تحسين pyautogui للسرعة
            pyautogui.MINIMUM_DURATION = 0
            pyautogui.MINIMUM_SLEEP = 0
            pyautogui.PAUSE = 0
            
            # التحضير للرسم
            pixels_drawn = 0
            skipped_pixels = 0
            start_time = time.time()
            
            # تجهيز قائمة البكسلات المراد رسمها مع تجاهل البكسلات الشفافة
            pixels_to_draw = []
            
            logger.info("تحليل البكسلات للرسم...")
            
            for y in range(height):
                for x in range(width):
                    # التحقق من الشفافية (قناة ألفا)
                    if len(img_data.shape) > 2 and img_data.shape[2] > 3:
                        # هناك قناة ألفا
                        alpha = img_data[y, x][3]
                        if alpha == 0:  # شفاف تمامًا
                            skipped_pixels += 1
                            continue
                    
                    # حساب الموقع
                    pos_x = x1 + (x * pixel_width) + (pixel_width / 2)
                    pos_y = y1 + (y * pixel_height) + (pixel_height / 2)
                    
                    # إضافة البكسل للقائمة
                    pixels_to_draw.append((pos_x, pos_y))
            
            total_pixels = len(pixels_to_draw)
            logger.info(f"سيتم رسم {total_pixels} بكسل، تم تخطي {skipped_pixels} بكسل")
            
            # التحرك لمنطقة الرسم
            pyautogui.moveTo(x1, y1)
            time.sleep(0.5)  # إعطاء وقت للتحرك
            
            # الرسم
            for i, (pos_x, pos_y) in enumerate(pixels_to_draw):
                # التحقق من طلب التوقف
                if self.stop_drawing:
                    logger.info("تم إيقاف الرسم بواسطة المستخدم")
                    return True
                
                # التحرك والنقر
                pyautogui.moveTo(pos_x, pos_y, duration=0)
                pyautogui.click()
                
                pixels_drawn += 1
                
                # تأخير بين البكسلات
                if self.speed > 0:
                    time.sleep(self.speed)
                
                # تسجيل التقدم
                if i % 500 == 0 or i == total_pixels - 1:
                    elapsed = time.time() - start_time
                    pixels_per_second = pixels_drawn / elapsed if elapsed > 0 else 0
                    percent = (pixels_drawn / total_pixels) * 100
                    logger.info(f"التقدم: {pixels_drawn}/{total_pixels} بكسل ({percent:.1f}%) - {pixels_per_second:.1f} بكسل/ثانية")
            
            # إحصائيات النهاية
            elapsed = time.time() - start_time
            logger.info(f"اكتمل الرسم: {pixels_drawn} بكسل في {elapsed:.1f} ثانية ({pixels_drawn/elapsed:.1f} بكسل/ثانية)")
            return True
            
        except Exception as e:
            logger.error(f"خطأ أثناء الرسم: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
        finally:
            # تنظيف
            keyboard.unhook_all()

def main():
    """الدالة الرئيسية للبرنامج"""
    parser = argparse.ArgumentParser(description="برنامج الرسم التلقائي - نسخة سطر الأوامر")
    parser.add_argument("image", nargs="?", help="مسار الصورة")
    parser.add_argument("--speed", "-s", type=float, default=0.001, help="سرعة الرسم (تأخير بالثواني)")
    parser.add_argument("--resolution", "-r", type=float, default=1.0, help="دقة الإخراج")
    parser.add_argument("--no-skip-white", action="store_true", help="عدم تخطي البكسلات البيضاء")
    
    args = parser.parse_args()
    
    # إنشاء كائن الرسم
    app = SimpleAutoDraw()
    app.speed = args.speed
    app.resolution = args.resolution
    app.skip_white = not args.no_skip_white
    
    # عرض الإعدادات
    logger.info(f"الإعدادات:")
    logger.info(f"- السرعة: {app.speed}s")
    logger.info(f"- الدقة: {app.resolution}x")
    logger.info(f"- تخطي البكسلات البيضاء: {app.skip_white}")
    
    # طلب مسار الصورة إذا لم يتم تحديده
    image_path = args.image
    if not image_path:
        image_path = input("أدخل مسار الصورة للرسم: ")
    
    if not os.path.exists(image_path):
        logger.error(f"الملف غير موجود: {image_path}")
        return
    
    # تحميل الصورة
    if not app.load_image(image_path):
        logger.error("فشل تحميل الصورة")
        return
    
    # معالجة الصورة
    logger.info("جاري معالجة الصورة...")
    if not app.process_image():
        logger.error("فشل معالجة الصورة")
        return
    
    # التأكيد قبل الرسم
    print("\n=== تنبيه مهم ===")
    print("1. تأكد من فتح التطبيق المستهدف (مثل برنامج الرسام)")
    print("2. تأكد من تحديد منطقة فارغة للرسم")
    print("3. اضغط ESC في أي وقت لإيقاف الرسم")
    print("4. لا تحرك الماوس أو تستخدم لوحة المفاتيح أثناء الرسم")
    
    choice = input("\nهل تريد بدء الرسم الآن؟ (y/n): ")
    if choice.lower() != 'y':
        logger.info("تم إلغاء الرسم بواسطة المستخدم")
        return
    
    # عد تنازلي
    print("\nالرسم سيبدأ خلال:")
    for i in range(5, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    print("\nبدء الرسم... اضغط ESC للإيقاف الفوري.")
    
    # بدء الرسم
    if app.draw_image():
        if app.stop_drawing:
            logger.info("تم إيقاف الرسم بواسطة المستخدم")
            print("\nتم إيقاف الرسم بواسطة المستخدم.")
        else:
            logger.info("اكتمل الرسم بنجاح")
            print("\nاكتمل الرسم بنجاح!")
    else:
        logger.error("فشل الرسم")
        print("\nفشل الرسم. راجع ملف السجل للمزيد من التفاصيل.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nتم إيقاف البرنامج بواسطة المستخدم.")
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"\nحدث خطأ غير متوقع: {e}")
    
    input("\nاضغط Enter للخروج...") 