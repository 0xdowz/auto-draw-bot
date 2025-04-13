#!/usr/bin/env python3
"""
AutoDraw - برنامج الرسم التلقائي
----------------------------
هذا البرنامج يمكّنك من رسم الصور تلقائيًا في برامج الرسم المختلفة

المميزات الرئيسية:
- رسم الصور تلقائيًا في برامج مثل الرسام (Paint) وغيرها
- تخطي البكسلات البيضاء لتسريع عملية الرسم
- خيارات متعددة لأسلوب الرسم (بكسل، محيط، متجه)
- تخصيص الدقة والسرعة
- تحسينات للأداء والدقة

متطلبات التشغيل:
- Python 3.6+
- pillow>=8.0.0 (معالجة الصور)
- pyautogui>=0.9.52 (التحكم في الماوس والكيبورد)
- numpy>=1.19.0 (معالجة المصفوفات)
- keyboard>=0.13.5 (التقاط مفتاح ESC)
- opencv-python>=4.5.0 (اختياري - لتحسين معالجة الصور)
- win32gui (اختياري - للتعامل مع النوافذ في Windows)
"""

# تأكد من استيراد المكتبات الأساسية أولاً
import os
import sys
import time
import json
import argparse
import logging
import threading
import traceback
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse

# Setup logging
def setup_logging():
    """Configure application-wide logging with proper formatting and file output"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    
    # Ensure log directory exists
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception:
            # Fall back to current directory if we can't create the logs dir
            log_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create timestamped log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"autodraw_{timestamp}.log")
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # File handler for debug logs - enhanced to log everything
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    detailed_format = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s')
    file_handler.setFormatter(detailed_format)
    
    # Add rotating file handler to manage log file size
    try:
        from logging.handlers import RotatingFileHandler
        # Keep backup logs up to 5MB each, 5 backups max
        rotating_handler = RotatingFileHandler(
            os.path.join(log_dir, "autodraw.log"),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        rotating_handler.setLevel(logging.DEBUG)
        rotating_handler.setFormatter(detailed_format)
        logger.addHandler(rotating_handler)
        
        # Also clean up old log files (older than 7 days)
        try:
            for f in os.listdir(log_dir):
                if f.startswith("autodraw_") and f.endswith(".log"):
                    file_path = os.path.join(log_dir, f)
                    file_time = os.path.getmtime(file_path)
                    if (time.time() - file_time) > 7 * 24 * 60 * 60:  # 7 days
                        try:
                            os.remove(file_path)
                            print(f"Removed old log file: {f}")
                        except:
                            pass
        except Exception as e:
            print(f"Error cleaning old log files: {e}")
    except ImportError:
        # If RotatingFileHandler is not available (unlikely), continue with regular handler
        pass
    
    # Console handler for info+ logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log system information
    logger.info(f"AutoDraw started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Operating system: {sys.platform}")
    logger.info(f"Log file: {log_file}")
    
    return logger

# Initialize logger at module level
logger = setup_logging()
logger.info(f"Starting AutoDraw application")

# Error handling decorator
def error_handler(func):
    """Decorator for catching and logging exceptions in methods"""
    def wrapper(*args, **kwargs):
        try:
            # Log function calls with parameters when in debug mode
            if args and hasattr(args[0], '__class__'):
                class_name = args[0].__class__.__name__
            else:
                class_name = func.__module__
                
            arg_str = ', '.join([str(a) for a in args[1:]])
            kwarg_str = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
            params = ', '.join(filter(None, [arg_str, kwarg_str]))
            logger.debug(f"Calling {class_name}.{func.__name__}({params})")
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Log completion
            logger.debug(f"Completed {class_name}.{func.__name__}")
            return result
            
        except Exception as e:
            # Get name of class or module
            if args and hasattr(args[0], '__class__'):
                class_name = args[0].__class__.__name__
            else:
                class_name = func.__module__
                
            # Log detailed error information
            logger.error(f"Error in {class_name}.{func.__name__}: {str(e)}")
            logger.debug(f"Exception type: {type(e).__name__}")
            logger.debug(f"Function arguments: {args[1:]} {kwargs}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            
            # Show error to user if it's a UI function
            if 'GUI' in class_name:
                try:
                    import tkinter.messagebox as messagebox
                    messagebox.showerror(
                        "Error",
                        f"An error occurred in {func.__name__}:\n{str(e)}\n\n"
                        "Check the log file for more details."
                    )
                except:
                    # If messagebox fails (maybe no UI), just print
                    print(f"ERROR: {str(e)}")
                    
            return None
    return wrapper

# Import required packages with error handling
try:
    import requests
    import tkinter as tk
    from tkinter import filedialog, ttk, messagebox, simpledialog
    from PIL import Image, ImageTk, ImageOps, ImageFilter, ImageEnhance
    import numpy as np
    import pyautogui
    import keyboard  # Added for Esc key detection
    import re
    import webbrowser
    
    # Disable PyAutoGUI failsafe
    pyautogui.FAILSAFE = False
    
    # Optional imports with fallbacks
    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV (cv2) not found. Some image processing features may be limited.")
        cv2 = None
        
    try:
        import win32gui  # pylint: disable=unused-import
    except ImportError:
        logger.warning("win32gui not found. Window handling features may be limited.")
        win32gui = None
        
    # Type checking for imports
    if sys.platform == 'win32':
        try:
            import win32gui  # pylint: disable=unused-import,reimported
        except ImportError:
            logger.warning("win32gui module import failed. Some Windows-specific features will be unavailable.")
            win32gui = None
    else:
        win32gui = None  # Non-Windows platforms
        
except ImportError as e:
    logger.critical(f"Failed to import required module: {e}")
    print(f"Error: Missing required dependency - {e}")
    print("Please install required packages using: pip install -r requirements.txt")
    sys.exit(1)

# Application version information
VERSION = "1.0.1"
AUTHOR = "AutoDraw Team"
APP_COPYRIGHT = f"© {datetime.now().year} {AUTHOR}"

# Constants - theme colors and other constants follow

# Theme colors - modernized with more vibrant colors and better contrast
LIGHT_THEME = {
    "bg": "#f8f9fa",
    "fg": "#212529",
    "accent": "#0d6efd",
    "accent_fg": "#ffffff",
    "secondary": "#e9ecef",
    "border": "#dee2e6",
    "canvas_bg": "#ffffff",
    "success": "#198754",
    "warning": "#ffc107",
    "danger": "#dc3545",
    "info": "#0dcaf0",
    "header_bg": "#f1f3f5",
    "control_bg": "#ffffff",
    "control_active": "#e7f1ff",
    "hover": "#e2e6ea"
}

DARK_THEME = {
    "bg": "#212529",
    "fg": "#f8f9fa",
    "accent": "#0d6efd",
    "accent_fg": "#ffffff",
    "secondary": "#343a40",
    "border": "#495057",
    "canvas_bg": "#2c3034",
    "success": "#20c997",
    "warning": "#ffc107",
    "danger": "#dc3545",
    "info": "#0dcaf0",
    "header_bg": "#1a1d20",
    "control_bg": "#2b3035",
    "control_active": "#1b4b91",
    "hover": "#343a40"
}

# Available languages
LANGUAGES = {
    "en": "English",
    "ar": "العربية",
    "es": "Español"
}

# Translations
TRANSLATIONS = {
    "en": {
        "app_title": "AutoDraw",
        "controls": "Controls",
        "preview": "Preview",
        "image_source": "Image Source",
        "local_file": "Local File",
        "url": "URL",
        "target_app": "Target Application",
        "drawing_area": "Drawing Area",
        "set_drawing_area": "Set Drawing Area",
        "reset": "Reset",
        "not_set": "Not set (using screen center)",
        "color_positions": "Color Positions",
        "set_color_positions": "Set Color Positions",
        "drawing_style": "Drawing Style",
        "pixel": "Pixel",
        "outline": "Outline",
        "vector": "Vector",
        "resolution": "Resolution",
        "drawing_speed": "Drawing Speed",
        "color_palette": "Color Palette",
        "default": "Default",
        "custom": "Custom",
        "draw": "Draw!",
        "ready": "Ready",
        "status_area_set": "Drawing area set",
        "status_area_reset": "Drawing area reset to default",
        "status_colors_set": "Color positions set",
        "status_colors_reset": "Color positions reset",
        "select_drawing_area": "Select Drawing Area",
        "select_drawing_area_msg": "You will now select the drawing area by clicking with your mouse.\n\n1. Click on the TOP-LEFT corner of your drawing area\n2. Then click on the BOTTOM-RIGHT corner\n\nPress OK to begin, or Cancel to abort.",
        "click_top_left": "Click on the TOP-LEFT corner of your drawing area",
        "click_bottom_right": "Now click on the BOTTOM-RIGHT corner",
        "area_selected": "Drawing Area Selected",
        "area_selected_msg": "Drawing area selected:\nTop-left: ({}, {})\nBottom-right: ({}, {})\nSize: {}×{} pixels",
        "select_window": "Select Target Window",
        "select_window_msg": "Click on the window where you want to draw",
        "window_selected": "Window Selected",
        "window_title": "Window Title: {}",
        "settings": "Settings",
        "language": "Language",
        "theme": "Theme",
        "light": "Light",
        "dark": "Dark",
        "version": "Version {}\nBy {}",
        "error": "Error",
        "error_window": "Failed to select window: {}",
        "error_area": "Failed to set drawing area: {}",
        "error_colors": "Failed to set color positions: {}",
        "save_settings": "Save Settings",
        "settings_saved": "Settings saved successfully",
        "settings_save_error": "Failed to save settings",
        "custom_target": "Custom Target"
    },
    "ar": {
        "app_title": "الرسم التلقائي",
        "controls": "أدوات التحكم",
        "preview": "معاينة",
        "image_source": "مصدر الصورة",
        "local_file": "ملف محلي",
        "url": "رابط",
        "target_app": "التطبيق المستهدف",
        "drawing_area": "منطقة الرسم",
        "set_drawing_area": "تحديد منطقة الرسم",
        "reset": "إعادة تعيين",
        "not_set": "غير محدد (استخدام وسط الشاشة)",
        "color_positions": "مواقع الألوان",
        "set_color_positions": "تحديد مواقع الألوان",
        "drawing_style": "نمط الرسم",
        "pixel": "بكسل",
        "outline": "حدود",
        "vector": "متجه",
        "resolution": "الدقة",
        "drawing_speed": "سرعة الرسم",
        "color_palette": "لوحة الألوان",
        "default": "افتراضي",
        "custom": "مخصص",
        "draw": "ارسم!",
        "ready": "جاهز",
        "status_area_set": "تم تحديد منطقة الرسم",
        "status_area_reset": "تم إعادة تعيين منطقة الرسم إلى الافتراضي",
        "status_colors_set": "تم تحديد مواقع الألوان",
        "status_colors_reset": "تم إعادة تعيين مواقع الألوان",
        "select_drawing_area": "تحديد منطقة الرسم",
        "select_drawing_area_msg": "ستقوم الآن بتحديد منطقة الرسم بالنقر بالماوس.\n\n1. انقر على الزاوية العلوية اليسرى لمنطقة الرسم\n2. ثم انقر على الزاوية السفلية اليمنى\n\nاضغط موافق للبدء، أو إلغاء للإحباط.",
        "click_top_left": "انقر على الزاوية العلوية اليسرى لمنطقة الرسم",
        "click_bottom_right": "الآن انقر على الزاوية السفلية اليمنى",
        "area_selected": "تم تحديد منطقة الرسم",
        "area_selected_msg": "تم تحديد منطقة الرسم:\nالزاوية العلوية اليسرى: ({}, {})\nالزاوية السفلية اليمنى: ({}, {})\nالحجم: {}×{} بكسل",
        "select_window": "تحديد النافذة المستهدفة",
        "select_window_msg": "انقر على النافذة التي تريد الرسم فيها",
        "window_selected": "تم تحديد النافذة",
        "window_title": "عنوان النافذة: {}",
        "settings": "الإعدادات",
        "language": "اللغة",
        "theme": "المظهر",
        "light": "فاتح",
        "dark": "داكن",
        "version": "الإصدار {}\nبواسطة {}",
        "error": "خطأ",
        "error_window": "فشل تحديد النافذة: {}",
        "error_area": "فشل تحديد منطقة الرسم: {}",
        "error_colors": "فشل تحديد مواقع الألوان: {}",
        "save_settings": "حفظ الإعدادات",
        "settings_saved": "تم حفظ الإعدادات بنجاح",
        "settings_save_error": "فشل في حفظ الإعدادات",
        "custom_target": "هدف مخصص"
    },
    "es": {
        "app_title": "AutoDraw",
        "controls": "Controles",
        "preview": "Vista previa",
        "image_source": "Fuente de imagen",
        "local_file": "Archivo local",
        "url": "URL",
        "target_app": "Aplicación objetivo",
        "drawing_area": "Área de dibujo",
        "set_drawing_area": "Establecer área de dibujo",
        "reset": "Reiniciar",
        "not_set": "No establecido (usando centro de pantalla)",
        "color_positions": "Posiciones de colores",
        "set_color_positions": "Establecer posiciones de colores",
        "drawing_style": "Estilo de dibujo",
        "pixel": "Pixel",
        "outline": "Contorno",
        "vector": "Vector",
        "resolution": "Resolución",
        "drawing_speed": "Velocidad de dibujo",
        "color_palette": "Paleta de colores",
        "default": "Predeterminado",
        "custom": "Personalizado",
        "draw": "¡Dibujar!",
        "ready": "Listo",
        "status_area_set": "Área de dibujo establecida",
        "status_area_reset": "Área de dibujo restablecida al valor predeterminado",
        "status_colors_set": "Posiciones de colores establecidas",
        "status_colors_reset": "Posiciones de colores restablecidas",
        "select_drawing_area": "Seleccionar área de dibujo",
        "select_drawing_area_msg": "Ahora seleccionará el área de dibujo haciendo clic con el ratón.\n\n1. Haga clic en la esquina SUPERIOR IZQUIERDA de su área de dibujo\n2. Luego haga clic en la esquina INFERIOR DERECHA\n\nPresione OK para comenzar o Cancelar para abortar.",
        "click_top_left": "Haga clic en la esquina SUPERIOR IZQUIERDA de su área de dibujo",
        "click_bottom_right": "Ahora haga clic en la esquina INFERIOR DERECHA",
        "area_selected": "Área de dibujo seleccionada",
        "area_selected_msg": "Área de dibujo seleccionada:\nSuperior izquierda: ({}, {})\nInferior derecha: ({}, {})\nTamaño: {}×{} píxeles",
        "select_window": "Seleccionar ventana objetivo",
        "select_window_msg": "Haga clic en la ventana donde desea dibujar",
        "window_selected": "Ventana seleccionada",
        "window_title": "Título de la ventana: {}",
        "settings": "Configuración",
        "language": "Idioma",
        "theme": "Tema",
        "light": "Claro",
        "dark": "Oscuro",
        "version": "Versión {}\nPor {}",
        "error": "Error",
        "error_window": "No se pudo seleccionar la ventana: {}",
        "error_area": "No se pudo establecer el área de dibujo: {}",
        "error_colors": "No se pudo establecer las posiciones de colores: {}",
        "save_settings": "Guardar configuración",
        "settings_saved": "Configuración guardada correctamente",
        "settings_save_error": "Error al guardar la configuración",
        "custom_target": "Objetivo personalizado"
    }
}

class DrawingAreaSelector:
    """Class to help user select drawing area and color positions"""
    
    def __init__(self, lang="en"):
        self.lang = lang
        self.translations = TRANSLATIONS[lang]
    
    def select_drawing_area(self):
        """Select drawing area with improved reliability and UX"""
        try:
            # Create instruction window
            root = tk.Tk()
            root.withdraw()  # Hide main window
            
            # Use try-finally to ensure cleanup even if there's an error
            try:
                result = messagebox.askokcancel(
                    self.translations["select_drawing_area"],
                    "You will now select the drawing area on your screen.\n\n"
                    "1. Click the top-left corner\n"
                    "2. Then click the bottom-right corner\n\n"
                    "Press OK to start or Cancel to abort."
                )
                
                if not result:
                    return None
                    
                # Get screen dimensions
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                
                # Create fullscreen transparent overlay
                overlay = tk.Toplevel(root)
                overlay.attributes("-alpha", 0.3)  # Semi-transparent
                overlay.attributes("-fullscreen", True)
                overlay.attributes("-topmost", True)
                
                # Create canvas
                canvas = tk.Canvas(overlay, highlightthickness=0)
                canvas.pack(fill=tk.BOTH, expand=True)
                
                # Result variables
                coords = []
                rect_id = None
                start_x, start_y = 0, 0
                
                # Coordinates display
                coords_label = tk.Label(
                    overlay, 
                    font=("Arial", 14), 
                    bg="black", 
                    fg="white",
                    padx=10,
                    pady=5
                )
                coords_label.place(x=10, y=10)
                
                # Instruction label
                instruction_label = tk.Label(
                    overlay, 
                    text="Click to select the top-left corner", 
                    font=("Arial", 18, "bold"), 
                    bg="black", 
                    fg="yellow",
                    padx=15,
                    pady=8
                )
                instruction_label.place(relx=0.5, rely=0.1, anchor=tk.CENTER)
                
                # Crosshair lines
                h_line = canvas.create_line(0, 0, screen_width, 0, fill="white", width=1, dash=(4, 4))
                v_line = canvas.create_line(0, 0, 0, screen_height, fill="white", width=1, dash=(4, 4))
                
                # Cancel button
                cancel_button = tk.Button(
                    overlay,
                    text="Cancel",
                    font=("Arial", 12),
                    bg="red",
                    fg="white",
                    command=lambda: overlay.destroy()
                )
                cancel_button.place(x=10, y=screen_height - 50)
                
                def update_crosshair(x, y):
                    """Update crosshair position and coordinates display"""
                    canvas.coords(h_line, 0, y, screen_width, y)
                    canvas.coords(v_line, x, 0, x, screen_height)
                    coords_label.config(text=f"X: {x}, Y: {y}")
                    
                def on_motion(event):
                    """Handle mouse movement"""
                    update_crosshair(event.x, event.y)
                    
                    # Update rectangle if first point is set
                    if len(coords) == 1 and rect_id:
                        canvas.coords(rect_id, start_x, start_y, event.x, event.y)
                        width = abs(event.x - start_x)
                        height = abs(event.y - start_y)
                        instruction_label.config(text=f"Dimensions: {width} × {height} pixels")
                    
                def on_click(event):
                    """Handle mouse clicks"""
                    nonlocal rect_id, start_x, start_y
                    
                    # First click - top-left corner
                    if len(coords) == 0:
                        start_x, start_y = event.x, event.y
                        coords.append((start_x, start_y))
                        
                        # Create rectangle
                        rect_id = canvas.create_rectangle(
                            start_x, start_y, start_x+1, start_y+1,
                            outline="lime", width=2
                        )
                        
                        instruction_label.config(text="Click to select the bottom-right corner")
                        
                    # Second click - bottom-right corner
                    elif len(coords) == 1:
                        coords.append((event.x, event.y))
                        overlay.destroy()
                        
                def on_escape(event):
                    """Cancel on escape key"""
                    overlay.destroy()
                
                # Bind events
                canvas.bind("<Motion>", on_motion)
                canvas.bind("<Button-1>", on_click)
                overlay.bind("<Escape>", on_escape)
                
                # Set focus for keyboard events
                overlay.focus_set()
                
                # Wait for overlay to close
                root.wait_window(overlay)
                
                # Process coordinates
                if len(coords) == 2:
                    x1, y1 = coords[0]
                    x2, y2 = coords[1]
                    
                    # Ensure x1,y1 is top-left and x2,y2 is bottom-right
                    if x1 > x2:
                        x1, x2 = x2, x1
                    if y1 > y2:
                        y1, y2 = y2, y1
                    
                    # Show confirmation message
                    messagebox.showinfo(
                        "Drawing Area Selected",
                        f"Drawing area:\n"
                        f"Top-left: ({x1}, {y1})\n"
                        f"Bottom-right: ({x2}, {y2})\n"
                        f"Dimensions: {x2-x1} × {y2-y1} pixels"
                    )
                    
                    return (x1, y1, x2, y2)
                else:
                    return None
            finally:
                # Ensure root is destroyed in all cases
                root.destroy()
                    
        except Exception as e:
            print(f"Error selecting drawing area: {e}")
            traceback.print_exc()
            return None
    
    def select_window(self):
        """Allow user to select a window by clicking on it"""
        root = tk.Tk()
        root.withdraw()
        
        result = messagebox.askokcancel(
            self.translations["select_window"],
            self.translations["select_window_msg"]
        )
        
        if not result:
            return None
        
        # Create a small overlay window for instructions
        overlay = tk.Toplevel(root)
        overlay.title(self.translations["select_window"])
        overlay.geometry("300x100+50+50")
        overlay.attributes("-topmost", True)
        overlay.resizable(False, False)
        
        instruction = tk.Label(overlay, text=self.translations["select_window_msg"], font=("Arial", 12))
        instruction.pack(pady=20)
        
        # Result container
        window_info = [None]
        
        # Start listening for mouse clicks
        def on_click(x, y, button, pressed):
            from pynput.mouse import Button
            
            if not pressed or button != Button.left:
                return
            
            try:
                # Get the window at the clicked position
                if sys.platform == 'win32' and 'win32gui' in sys.modules:
                    import win32gui  # pylint: disable=unused-import,reimported
                    hwnd = win32gui.WindowFromPoint((x, y))
                    if hwnd:
                        window_title = win32gui.GetWindowText(hwnd)
                        window_info[0] = {
                            "hwnd": hwnd,
                            "title": window_title
                        }
                        overlay.destroy()
                        root.destroy()
                        return False
                else:
                    logger.warning("win32gui module not available for window selection")
                    messagebox.showwarning(
                        "Window Selection Limited",
                        "win32gui module not available. Window selection may be limited."
                    )
                    overlay.destroy()
                    root.destroy()
                    return False
            except Exception as e:
                logger.error(f"Error getting window: {e}")
            
            # Stop the listener
            return False
        
        try:
            # Import pynput here to avoid global import issues
            from pynput.mouse import Listener
            
            # Start listening for mouse clicks
            with Listener(on_click=on_click) as listener:
                overlay.mainloop()
                listener.join()
            
            # Process the window information
            if window_info[0]:
                # Show the selected window
                result_root = tk.Tk()
                result_root.withdraw()
                messagebox.showinfo(
                    self.translations["window_selected"],
                    self.translations["window_title"].format(window_info[0]["title"])
                )
                result_root.destroy()
                
                return window_info[0]
            else:
                return None
                
        except ImportError:
            # Fallback message
            messagebox.showwarning(
                "Window Selection Not Available",
                "Could not import required libraries. Please install:\npip install pynput pywin32"
            )
            return None
        except Exception as e:
            messagebox.showerror(self.translations["error"], f"{self.translations['error_window']} {str(e)}")
            return None
    
    def select_color_positions(self, colors):
        """Select positions for each color with improved UI and validation
        
        This method provides a user interface for selecting the position of each
        color in the drawing application's palette. It includes features for
        previewing, testing, and validating color selections.
        
        Args:
            colors: List of RGB tuples representing colors that need positions
            
        Returns:
            dict: Mapping of colors (RGB tuples) to screen positions (x,y), or None if cancelled
        """
        if not colors or not isinstance(colors, (list, tuple)):
            print("Error: No colors provided for position selection")
            return None
            
        # Setup main window
        root = tk.Tk()
        root.withdraw()
        
        # Create instruction window with better UI
        instruction_window = tk.Toplevel(root)
        instruction_window.title("Select Color Positions")
        instruction_window.geometry("600x650+50+50")
        instruction_window.attributes("-topmost", True)
        instruction_window.configure(bg="#f0f0f0")  # Light gray background
        
        # Set window icon if available
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            if os.path.exists(icon_path):
                icon = tk.PhotoImage(file=icon_path)
                instruction_window.iconphoto(True, icon)
        except Exception:
            pass
        
        # Main frame with padding and styling
        main_frame = ttk.Frame(instruction_window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with title
        header_label = ttk.Label(
            main_frame, 
            text="Color Position Selection",
            font=("Arial", 16, "bold"),
            anchor="center"
        )
        header_label.pack(fill=tk.X, pady=(0, 15))
        
        # Instructions with detailed explanation
        instruction_text = (
            "For each color in your palette, follow these steps:\n\n"
            "1. Click the 'Pick' button next to a color\n"
            "2. Within 3 seconds, position your mouse over that color in your drawing application\n"
            "3. The position will be captured automatically when the countdown ends\n"
            "4. Use the 'Test' button to verify the correct position was captured\n\n"
            "You can also add custom colors using the 'Add Custom Color' button below."
        )
        
        instructions = ttk.Label(
            main_frame, 
            text=instruction_text,
            wraplength=550,
            justify=tk.LEFT,
            font=("Arial", 11)
        )
        instructions.pack(fill=tk.X, pady=(0, 15))
        
        # Create a separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill=tk.X, pady=10)
        
        # Color positions frame with scrollbar for many colors
        color_frame_label = ttk.Label(
            main_frame, 
            text="Available Colors",
            font=("Arial", 12, "bold")
        )
        color_frame_label.pack(anchor="w", pady=(0, 5))
        
        color_frame = ttk.LabelFrame(main_frame, padding=10)
        color_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a canvas with scrollbar for color entries
        canvas = tk.Canvas(color_frame, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(color_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Define the color positions and reference variables
        color_positions = {}
        position_vars = {}
        
        # Define common color names for better identification
        color_names = {
            (0, 0, 0): "Black",
            (127, 127, 127): "Gray", 
            (192, 192, 192): "Silver",
            (255, 255, 255): "White",
            (255, 0, 0): "Red",
            (128, 0, 0): "Maroon",
            (255, 165, 0): "Orange",
            (255, 255, 0): "Yellow",
            (0, 255, 0): "Lime",
            (0, 128, 0): "Green",
            (0, 255, 255): "Cyan",
            (0, 0, 255): "Blue",
            (0, 0, 128): "Navy",
            (128, 0, 128): "Purple",
            (255, 0, 255): "Magenta",
            (165, 42, 42): "Brown",
            (255, 192, 203): "Pink"
        }
        
        def get_color_name(color):
            """Get a user-friendly name for a color"""
            if color in color_names:
                return color_names[color]
            
            # Find closest named color for better UX
            closest_name = None
            min_distance = float('inf')
            
            for known_color, name in color_names.items():
                r1, g1, b1 = color
                r2, g2, b2 = known_color
                distance = ((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2)**0.5
                
                if distance < min_distance:
                    min_distance = distance
                    closest_name = name
            
            # If quite close to a named color, use that name with a modifier
            if min_distance < 30 and closest_name:
                return f"{closest_name}-like"
            
            # Otherwise just return RGB values
            return f"RGB({color[0]}, {color[1]}, {color[2]})"
        
        def rgb_to_hex(color):
            """Convert RGB tuple to hex color string"""
            return "#{:02x}{:02x}{:02x}".format(*color)
        
        def select_position_for_color(color, test_button):
            """Capture mouse position for a color with enhanced UI"""
            # Hide instruction window temporarily
            instruction_window.withdraw()
            
            # Create countdown window with better visibility
            countdown = tk.Toplevel(root)
            countdown.title("Select Color Position")
            countdown.geometry("400x300+100+100")
            countdown.attributes("-topmost", True)
            countdown.configure(bg="#333333")
            
            # Setup variables
            color_name = get_color_name(color)
            color_hex = rgb_to_hex(color)
            seconds_left = [3]  # Use list for nonlocal access
            
            # Color preview - larger and with border
            preview_frame = tk.Frame(countdown, bg=color_hex, width=100, height=100,
                                   highlightbackground="white", highlightthickness=2)
            preview_frame.pack(pady=20)
            
            # Instructions with animation
            text_var = tk.StringVar()
            text_var.set(f"Position your mouse over the {color_name} color\nin your drawing application.")
            
            instruction_label = tk.Label(
                countdown, 
                textvariable=text_var,
                font=("Arial", 12, "bold"),
                bg="#333333",
                fg="white"
            )
            instruction_label.pack(pady=10)
            
            # Countdown display with animated color
            countdown_var = tk.StringVar()
            countdown_var.set(f"Capturing in {seconds_left[0]} seconds...")
            
            countdown_label = tk.Label(
                countdown,
                textvariable=countdown_var,
                font=("Arial", 14, "bold"),
                bg="#333333",
                fg="#00FF00"  # Start with green
            )
            countdown_label.pack(pady=10)
            
            # Cancel button
            cancel_button = tk.Button(
                countdown,
                text="Cancel",
                font=("Arial", 11),
                bg="red",
                fg="white",
                command=lambda: countdown.destroy()
            )
            cancel_button.pack(pady=15)
            
            # Update countdown display with animation
            def update_countdown():
                """Update countdown timer"""
                seconds_left[0] -= 1
                
                # Change colors based on time left
                if seconds_left[0] == 2:
                    countdown_label.config(fg="#FFFF00")  # Yellow
                elif seconds_left[0] == 1:
                    countdown_label.config(fg="#FF0000")  # Red
                
                countdown_var.set(f"Capturing in {seconds_left[0]} seconds...")
                
                if seconds_left[0] > 0:
                    countdown.after(1000, update_countdown)
            
            # Capture position when countdown completes
            def do_capture():
                """Capture the mouse position"""
                try:
                    # Get current mouse position
                    x, y = pyautogui.position()
                    
                    # Basic validation - check if mouse is at (0,0) which is unlikely
                    if (x, y) == (0, 0):
                        result = messagebox.askyesno(
                            "Warning", 
                            "Mouse position is at (0,0), which is unusual.\n"
                            "This might indicate a problem. Do you want to try again?",
                            parent=countdown
                        )
                        if result:
                            # Restart the countdown
                            seconds_left[0] = 3
                            update_countdown()
                            countdown.after(3000, do_capture)
                            return
                    
                    # Save position and update UI
                    color_positions[color] = (x, y)
                    position_vars[color].set(f"({x}, {y})")
                    
                    # Enable test button
                    test_button.config(state="normal")
                    
                    # Close countdown window and show instruction window
                    countdown.destroy()
                    instruction_window.deiconify()
                    
                except Exception as e:
                    print(f"Error capturing mouse position: {e}")
                    messagebox.showerror(
                        "Error", 
                        f"Failed to capture position: {str(e)}",
                        parent=countdown
                    )
                    countdown.destroy()
                    instruction_window.deiconify()
            
            # Start countdown
            countdown.after(1000, update_countdown)
            countdown.after(3000, do_capture)
        
        def add_custom_color():
            """Add a custom color to the palette"""
            try:
                from tkinter import colorchooser
                color_rgb, color_hex = colorchooser.askcolor(
                    title="Select Custom Color",
                    parent=instruction_window
                )
                
                if color_rgb:
                    # Convert to integer RGB tuple
                    new_color = tuple(map(int, color_rgb))
                    
                    # Add to colors if not already there
                    if new_color not in colors:
                        colors.append(new_color)
                        add_color_entry(new_color)
                        messagebox.showinfo(
                            "Success", 
                            f"Added new color: {get_color_name(new_color)}",
                            parent=instruction_window
                        )
            except Exception as e:
                messagebox.showerror(
                    "Error", 
                    f"Failed to add custom color: {str(e)}",
                    parent=instruction_window
                )
        
        def add_color_entry(color):
            """Add a color entry to the scrollable frame"""
            # Create a frame for each color entry
            color_entry_frame = ttk.Frame(scrollable_frame)
            color_entry_frame.pack(fill=tk.X, pady=8, padx=5)
            
            # Color preview - larger and with border
            color_hex = rgb_to_hex(color)
            color_preview = tk.Frame(
                color_entry_frame, 
                width=40, 
                height=30, 
                bg=color_hex, 
                highlightbackground="black", 
                highlightthickness=1
            )
            color_preview.pack(side=tk.LEFT, padx=10)
            
            # Color name
            color_name = get_color_name(color)
            name_label = ttk.Label(
                color_entry_frame, 
                text=color_name, 
                width=15
            )
            name_label.pack(side=tk.LEFT, padx=5)
            
            # Position display
            position_var = tk.StringVar(value="Not set")
            position_vars[color] = position_var
            position_label = ttk.Label(
                color_entry_frame, 
                textvariable=position_var, 
                width=12
            )
            position_label.pack(side=tk.LEFT, padx=5)
            
            # Test button for validation - initially disabled
            test_button = ttk.Button(
                color_entry_frame,
                text="Test",
                command=lambda c=color: test_color_position(c),
                state="disabled"  # Enabled only after position is set
            )
            test_button.pack(side=tk.RIGHT, padx=5)
            
            # Pick button
            pick_button = ttk.Button(
                color_entry_frame, 
                text="Pick", 
                command=lambda c=color, btn=test_button: select_position_for_color(c, btn)
            )
            pick_button.pack(side=tk.RIGHT, padx=5)
        
        def test_color_position(color):
            """Test a color position by moving the mouse there"""
            if color in color_positions:
                # Hide the window temporarily
                instruction_window.withdraw()
                
                # Create test window
                test_window = tk.Toplevel(root)
                test_window.title("Testing Color Position")
                test_window.geometry("350x180+100+100")
                test_window.attributes("-topmost", True)
                test_window.configure(bg="#f0f0f0")
                
                # Information display
                ttk.Label(
                    test_window, 
                    text=f"Moving to {get_color_name(color)} position...",
                    font=("Arial", 12, "bold")
                ).pack(pady=(20, 10))
                
                x, y = color_positions[color]
                ttk.Label(
                    test_window, 
                    text=f"Position: ({x}, {y})",
                    font=("Arial", 11)
                ).pack(pady=5)
                
                # Close button
                ttk.Button(
                    test_window,
                    text="Done",
                    command=lambda: [test_window.destroy(), instruction_window.deiconify()]
                ).pack(pady=15)
                
                # Perform the mouse movement
                def move_mouse():
                    try:
                        # Move mouse to position
                        pyautogui.moveTo(x, y, duration=0.5)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to move mouse: {str(e)}")
                    
                # Schedule movement after a short delay
                test_window.after(500, move_mouse)
        
        # Add all colors to the UI
        for color in colors:
            add_color_entry(color)
        
        # Custom color button
        custom_color_frame = ttk.Frame(main_frame)
        custom_color_frame.pack(fill=tk.X, pady=10)
        
        add_color_button = ttk.Button(
            custom_color_frame,
            text="Add Custom Color",
            command=add_custom_color
        )
        add_color_button.pack(side=tk.LEFT)
        
        # Display total number of colors
        color_count_var = tk.StringVar(value=f"Total colors: {len(colors)}")
        ttk.Label(
            custom_color_frame,
            textvariable=color_count_var,
            font=("Arial", 10)
        ).pack(side=tk.RIGHT, padx=10)
        
        # Create separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill=tk.X, pady=10)
        
        # Bottom action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=lambda: [color_positions.clear(), instruction_window.destroy()]
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Done button
        done_button = ttk.Button(
            button_frame,
            text="Done",
            command=lambda: on_done()
        )
        done_button.pack(side=tk.RIGHT, padx=5)
        
        def on_done():
            """Handle completion of color position selection"""
            if not color_positions:
                result = messagebox.askyesno(
                    "Warning",
                    "No color positions have been set. Are you sure you want to continue?",
                    parent=instruction_window
                )
                if not result:
                    return
            
            # Check for unset colors
            unset_count = len(colors) - len(color_positions)
            if unset_count > 0:
                result = messagebox.askyesnocancel(
                    "Incomplete Selection",
                    f"{unset_count} colors don't have positions set.\n\n"
                    "• Click 'Yes' to continue setting positions\n"
                    "• Click 'No' to proceed with the colors that are set\n"
                    "• Click 'Cancel' to cancel the operation",
                    parent=instruction_window
                )
                
                if result is True:  # Yes - continue setting
                    return
                elif result is False:  # No - proceed with what we have
                    instruction_window.destroy()
                else:  # Cancel
                    color_positions.clear()
                    instruction_window.destroy()
            else:
                instruction_window.destroy()
        
        # Enable keyboard shortcuts
        instruction_window.bind("<Escape>", lambda e: [color_positions.clear(), instruction_window.destroy()])
        
        # Wait for instruction window to close
        root.wait_window(instruction_window)
        
        # Cleanup
        root.destroy()
        
        # Return the selected positions
        return color_positions if color_positions else None

class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text=''):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        
    def enter(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        # Create a toplevel window
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Add a label
        label = tk.Label(self.tooltip_window, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Arial", "9", "normal"))
        label.pack(padx=3, pady=3)
    
    def leave(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class AutoDraw:
    def __init__(self):
        """Initialize AutoDraw with improved settings for precise drawing"""
        # Core properties
        self.image = None
        self.processed_image = None
        self.palette = []
        self.target_app = "mspaint"
        self.style = "pixel"
        self.resolution = 1.0
        self.speed = 0.001
        self.stop_drawing = False
        
        # Drawing area and color positions
        self.canvas_area = None  # (x1, y1, x2, y2)
        self.color_positions = {}  # {(r,g,b): (x,y)}
        
        # Drawing optimization settings
        self.skip_white = True  # Skip white pixels
        self.optimize_colors = True  # Optimize color changes
        self.drawing_strategy = "optimized"  # optimized, line-by-line, color-by-color
        self.precision_value = 50  # 0-100, balance between speed and precision
        
        # Configuration file path
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        
        # Load saved settings
        self.load_settings()
    
    @error_handler
    def save_settings(self):
        """Save settings to JSON file with improved structure and optimizations"""
        settings = {
            "target_app": self.target_app,
            "style": self.style,
            "resolution": self.resolution,
            "speed": self.speed,
            "drawing": {
                "skip_white": self.skip_white,
                "optimize_colors": self.optimize_colors,
                "strategy": self.drawing_strategy,
                "precision": self.precision_value
            },
            "palette": self.palette if isinstance(self.palette, list) else [],
            "canvas_area": self.canvas_area,
            "color_positions": {str(k): v for k, v in self.color_positions.items()} if self.color_positions else {}
        }
        
        try:
            # Create directory if it doesn't exist
            config_dir = os.path.dirname(self.config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            # Save with pretty formatting for better human readability
            with open(self.config_file, 'w') as f:
                json.dump(settings, f, indent=4)
                
            logger.info(f"Settings saved successfully to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False
    
    @error_handler
    def load_settings(self):
        """Load settings from JSON file with support for new optimization parameters"""
        if not os.path.exists(self.config_file):
            logger.info(f"No settings file found at {self.config_file}, using defaults")
            return False
            
        try:
            with open(self.config_file, 'r') as f:
                settings = json.load(f)
                
            # Load basic settings
            if "target_app" in settings:
                self.target_app = settings["target_app"]
                
            if "style" in settings:
                self.style = settings["style"]
                
            if "resolution" in settings:
                self.resolution = float(settings["resolution"])
                
            if "speed" in settings:
                self.speed = float(settings["speed"])
                
            # Load drawing area if available
            if "canvas_area" in settings and settings["canvas_area"]:
                self.canvas_area = tuple(settings["canvas_area"])
                
            # Load palette if available
            if "palette" in settings and settings["palette"]:
                self.palette = settings["palette"]
                
            # Load color positions if available, converting string keys back to tuples
            if "color_positions" in settings and settings["color_positions"]:
                color_positions = {}
                for key, value in settings["color_positions"].items():
                    # Handle both string format "(r,g,b)" and legacy format "r,g,b"
                    if key.startswith("(") and key.endswith(")"):
                        # Modern format
                        color = eval(key)  # Convert string tuple to actual tuple
                    else:
                        # Legacy format
                        r, g, b = map(int, key.split(","))
                        color = (r, g, b)
                        
                    color_positions[color] = tuple(value)
                    
                self.color_positions = color_positions
                
            # Load optimization settings
            if "drawing" in settings:
                drawing = settings["drawing"]
                if "skip_white" in drawing:
                    self.skip_white = bool(drawing["skip_white"])
                    
                if "optimize_colors" in drawing:
                    self.optimize_colors = bool(drawing["optimize_colors"])
                    
                if "strategy" in drawing:
                    self.drawing_strategy = drawing["strategy"]
                    
                if "precision" in drawing:
                    self.precision_value = int(drawing["precision"])
            
            logger.info(f"Settings loaded successfully from {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return False
    
    @error_handler
    def load_image(self, source):
        """Load image from file path, URL, or BytesIO object with improved error handling
        
        Args:
            source: Can be a string file path, URL string, or BytesIO object
            
        Returns:
            bool: True if image loaded successfully, False otherwise
        """
        try:
            # Clear any previous image data
            self.image = None
            self.processed_image = None
            self.preview_image = None
            
            # Handle different source types
            if isinstance(source, BytesIO):
                # Direct BytesIO data (like from URL)
                self.image = Image.open(source)
                self.image_filename = "image_from_url.jpg"
                self.image_path = None
                
            elif isinstance(source, str):
                # Check if source is a URL
                if re.match(r'^https?://', source):
                    try:
                        # Use headers to avoid rejection by some servers
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                            'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Referer': 'https://www.google.com/'
                        }
                        
                        # Set reasonable timeout
                        response = requests.get(source, headers=headers, timeout=10)
                        
                        if response.status_code != 200:
                            raise ConnectionError(f"Failed to download image. Status code: {response.status_code}")
                            
                        # Check content type to verify it's an image
                        content_type = response.headers.get('Content-Type', '')
                        if not content_type.startswith('image/'):
                            raise ValueError(f"URL does not point to an image. Content-Type: {content_type}")
                            
                        self.image = Image.open(BytesIO(response.content))
                        self.image_filename = os.path.basename(source) or "image_from_url.jpg"
                        self.image_path = None
                        
                    except requests.RequestException as e:
                        raise ConnectionError(f"Network error while fetching image: {e}")
                        
                else:
                    # Local file path
                    if not os.path.isfile(source):
                        raise FileNotFoundError(f"Image file not found: {source}")
                        
                    self.image = Image.open(source)
                    self.image_path = os.path.abspath(source)
                    self.image_filename = os.path.basename(source)
            else:
                raise TypeError("Unsupported source type. Must be a file path, URL, or BytesIO object.")
            
            # Ensure image is in RGB mode for consistent processing
            if self.image.mode != 'RGB':
                self.image = self.image.convert('RGB')
                
            # Save image dimensions and log success
            self.image_width, self.image_height = self.image.size
            print(f"Image loaded successfully: {self.image_width}x{self.image_height} pixels")
            
            return True
            
        except (IOError, OSError) as e:
            print(f"Error opening image file: {e}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"Error downloading image from URL: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error loading image: {e}")
            traceback.print_exc()
            return False
    
    @error_handler
    def load_palette(self, palette_path):
        """Load color palette from a JSON or CSV file"""
        try:
            ext = os.path.splitext(palette_path)[1].lower()
            
            if ext == '.json':
                with open(palette_path, 'r') as f:
                    self.palette = json.load(f)
            elif ext == '.csv':
                self.palette = []
                with open(palette_path, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        parts = line.strip().split(',')
                        if len(parts) >= 3:
                            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                            self.palette.append((r, g, b))
            else:
                raise Exception("Unsupported palette file format")
            
            return True
        except Exception as e:
            print(f"Error loading palette: {e}")
            return False
    
    def get_default_palette(self, app_name):
        """Return default palette based on target application"""
        if app_name.lower() == "mspaint" or app_name.lower() == "paint":
            # Default MS Paint palette
            return [
                (0, 0, 0),       # Black
                (127, 127, 127), # Gray
                (136, 0, 21),    # Dark red
                (237, 28, 36),   # Red
                (255, 127, 39),  # Orange
                (255, 242, 0),   # Yellow
                (34, 177, 76),   # Green
                (0, 162, 232),   # Blue
                (63, 72, 204),   # Dark blue
                (163, 73, 164),  # Purple
                (255, 255, 255), # White
                (195, 195, 195), # Light gray
                (185, 122, 87),  # Brown
                (255, 174, 201), # Pink
                (255, 201, 14),  # Gold
                (239, 228, 176), # Light yellow
                (181, 230, 29),  # Light green
                (153, 217, 234), # Light blue
                (112, 146, 190), # Medium blue
                (200, 191, 231)  # Lavender
            ]
        elif app_name.lower() == "gartic" or app_name.lower() == "gartic phone":
            # Default Gartic Phone palette
            return [
                (0, 0, 0),       # Black
                (102, 102, 102), # Dark gray
                (170, 170, 170), # Light gray
                (255, 255, 255), # White
                (124, 77, 54),   # Brown
                (198, 120, 87),  # Light brown
                (240, 156, 118), # Beige
                (242, 178, 55),  # Orange
                (252, 215, 3),   # Yellow
                (253, 253, 150), # Light yellow
                (108, 224, 134), # Light green
                (54, 180, 107),  # Green
                (39, 127, 70),   # Dark green
                (135, 242, 255), # Light blue
                (34, 177, 214),  # Blue
                (28, 101, 140),  # Dark blue
                (158, 114, 189), # Purple
                (120, 71, 135),  # Dark purple
                (255, 110, 166), # Pink
                (255, 18, 64)    # Red
            ]
        else:
            # Basic default palette
            return [
                (0, 0, 0),       # Black
                (127, 127, 127), # Gray
                (255, 0, 0),     # Red
                (0, 255, 0),     # Green
                (0, 0, 255),     # Blue
                (255, 255, 0),   # Yellow
                (0, 255, 255),   # Cyan
                (255, 0, 255),   # Magenta
                (255, 255, 255)  # White
            ]
    
    def find_closest_color(self, color):
        """Enhanced method to find the closest color in the palette to the given color
        using a perceptually better color distance formula (CIE94)"""
        if not self.palette:
            return color
        
        r, g, b = color
        min_distance = float('inf')
        closest_color = None
        
        # Convert RGB to LAB color space for better perceptual matching
        lab1 = self.rgb2lab(color)
        
        for palette_color in self.palette:
            # Convert palette color to LAB
            lab2 = self.rgb2lab(palette_color)
            
            # Calculate delta E (CIE94 color difference)
            distance = self.delta_e_cie94(lab1, lab2)
            
            if distance < min_distance:
                min_distance = distance
                closest_color = palette_color
        
        return closest_color
    
    def rgb2lab(self, rgb):
        """Convert RGB color to LAB color space for better perceptual matching"""
        r, g, b = rgb
        
        # Normalize RGB values
        r = r / 255.0
        g = g / 255.0
        b = b / 255.0
        
        # Convert to sRGB - use if-else instead of logical operators
        if r > 0.04045:
            r = ((r + 0.055) / 1.055) ** 2.4
        else:
            r = r / 12.92
            
        if g > 0.04045:
            g = ((g + 0.055) / 1.055) ** 2.4
        else:
            g = g / 12.92
            
        if b > 0.04045:
            b = ((b + 0.055) / 1.055) ** 2.4
        else:
            b = b / 12.92
        
        # Convert to XYZ
        x = (r * 0.4124 + g * 0.3576 + b * 0.1805) * 100
        y = (r * 0.2126 + g * 0.7152 + b * 0.0722) * 100
        z = (r * 0.0193 + g * 0.1192 + b * 0.9505) * 100
        
        # Convert XYZ to Lab
        x /= 95.047
        y /= 100.0
        z /= 108.883
        
        # Use if-else instead of logical operators
        if x > 0.008856:
            x = x ** (1/3)
        else:
            x = (7.787 * x) + (16/116)
            
        if y > 0.008856:
            y = y ** (1/3)
        else:
            y = (7.787 * y) + (16/116)
            
        if z > 0.008856:
            z = z ** (1/3)
        else:
            z = (7.787 * z) + (16/116)
        
        L = (116 * y) - 16
        a = 500 * (x - y)
        b = 200 * (y - z)
        
        return (L, a, b)
    
    def delta_e_cie94(self, lab1, lab2):
        """Calculate CIE94 color difference between two LAB colors"""
        L1, a1, b1 = lab1
        L2, a2, b2 = lab2
        
        dL = L1 - L2
        da = a1 - a2
        db = b1 - b2
        
        c1 = (a1 ** 2 + b1 ** 2) ** 0.5
        c2 = (a2 ** 2 + b2 ** 2) ** 0.5
        
        dC = c1 - c2
        
        # Ensure we don't get a negative value under the square root
        # which would result in a complex number
        dhSquared = da ** 2 + db ** 2 - dC ** 2
        if dhSquared < 0:
            dH = 0  # Avoid complex numbers
        else:
            dH = dhSquared ** 0.5
        
        # Parameters
        kL = 1
        k1 = 0.045
        k2 = 0.015
        
        sl = 1
        sc = 1 + k1 * c1
        sh = 1 + k2 * c1
        
        # Delta E calculation
        dE = ((dL / (kL * sl)) ** 2 + (dC / sc) ** 2 + (dH / sh) ** 2) ** 0.5
        
        return dE
    
    @error_handler
    def process_image(self):
        """Process the image for drawing with improved efficiency and white pixel handling
        
        This method processes the loaded image based on style, resolution, and palette settings.
        It includes special handling for white pixels and optimizes the image for drawing.
        
        Returns:
            bool: True if processing successful, False otherwise
        """
        if not self.image:
            logger.error("No image loaded to process")
            return False
            
        try:
            # Work with a copy to preserve original
            img = self.image.copy()
            
            # Apply resolution scaling
            if self.resolution != 1.0:
                width, height = img.size
                new_width = int(width * self.resolution)
                new_height = int(height * self.resolution)
                img = img.resize((new_width, new_height), Image.LANCZOS)
                logger.info(f"Resized image to {new_width}x{new_height} (resolution: {self.resolution}x)")
            
            # Convert image to RGB mode for consistent processing
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Special handling for white pixels - mark them in alpha channel 
            # This helps with efficient white pixel skipping during drawing
            if hasattr(self, 'skip_white') and self.skip_white:
                # Convert to RGBA to add alpha channel
                img_rgba = img.convert("RGBA")
                pixel_data = img_rgba.load()
                width, height = img_rgba.size
                
                # Set alpha=0 for white pixels (make them transparent)
                white_threshold = 245
                white_count = 0
                total_pixels = width * height
                
                for y in range(height):
                    for x in range(width):
                        r, g, b, a = pixel_data[x, y]
                        # Check if pixel is white or near-white
                        if r >= white_threshold and g >= white_threshold and b >= white_threshold:
                            # Make white pixel transparent
                            pixel_data[x, y] = (r, g, b, 0)
                            white_count += 1
                
                # Log statistics about white pixels
                white_percentage = (white_count / total_pixels) * 100
                logger.info(f"Marked {white_count} white pixels as transparent ({white_percentage:.1f}% of image)")
                
                # Update the image
                img = img_rgba
            
            # Apply style-specific processing
            if self.style == "outline":
                # For outline style, convert to grayscale then apply edge detection
                img = img.convert("L")  # Convert to grayscale
                img = img.filter(ImageFilter.FIND_EDGES)  # Apply edge detection
                
                # Adjust contrast to make edges more pronounced
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(2.0)
                
                # Convert back to RGB
                img = img.convert("RGB")
                logger.info("Applied outline processing with edge detection")
                
            elif self.style == "vector":
                # For vector style, apply smoothing and edge preservation
                # First apply slight blur to reduce noise
                img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
                
                # Then enhance edges
                img = img.filter(ImageFilter.EDGE_ENHANCE)
                
                # Apply posterization to reduce colors (if cv2 is available)
                if cv2:
                    # Convert PIL image to cv2 format
                    cv_img = np.array(img)
                    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)
                    
                    # Apply bilateral filter to smooth while preserving edges
                    cv_img = cv2.bilateralFilter(cv_img, 9, 75, 75)
                    
                    # Convert back to PIL image
                    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(cv_img)
                    logger.info("Applied vector processing with bilateral filter")
                else:
                    # Fall back to simpler processing if OpenCV not available
                    img = img.filter(ImageFilter.SMOOTH)
                    logger.info("Applied basic vector processing (OpenCV not available)")
            
            else:  # pixel style
                # For pixel style, quantize colors to match palette
                # No additional processing needed beyond palette matching
                logger.info("Using pixel style drawing mode")
            
            # Store the processed image
            self.processed_image = img
            
            # Create a preview image for display
            self.preview_image = self.processed_image.copy()
            
            logger.info(f"Image processed successfully: {img.width}x{img.height}, mode={img.mode}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            logger.error(traceback.format_exc())
            return False
    
    @error_handler
    def find_target_window(self):
        """Find available windows for drawing target selection with improved detection and filtering"""
        try:
            # First try the more robust win32gui method
            if sys.platform == 'win32' and 'win32gui' in sys.modules:
                import win32gui  # pylint: disable=unused-import,reimported
                
                # Get list of windows with more information
                windows = []
                
                def enum_windows_callback(hwnd, windows):
                    # Only consider visible windows with titles
                    if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        # Skip common system windows and our own application
                        if (len(title) > 1 and 
                            not title.startswith("Auto") and 
                            not title == "" and
                            title not in ["Program Manager", "Settings", "Microsoft Text Input Application"]):
                            try:
                                # Get window rect for better information
                                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                                width = right - left
                                height = bottom - top
                                
                                # Skip very small windows that are likely not drawing targets
                                if width > 200 and height > 200:
                                    windows.append({
                                        "hwnd": hwnd,
                                        "title": title,
                                        "rect": (left, top, right, bottom),
                                        "width": width,
                                        "height": height
                                    })
                            except:
                                # Fall back to basic information if we can't get the rect
                                windows.append({
                                    "hwnd": hwnd,
                                    "title": title
                                })
                            
                win32gui.EnumWindows(enum_windows_callback, windows)
                
                # Filter and sort windows for easier selection
                # Sort by relevance: drawing apps first, then by window size
                # Common drawing app names to prioritize
                drawing_apps = ["paint", "draw", "canvas", "sketch", "photo", "image", "editor", "art"]
                
                def window_sort_key(window):
                    title = window["title"].lower()
                    # Check if it's likely a drawing app
                    is_drawing_app = any(app in title for app in drawing_apps)
                    # Prioritize drawing apps, then larger windows
                    return (0 if is_drawing_app else 1, 
                            -window.get("width", 0) if "width" in window else 0)
                
                windows.sort(key=window_sort_key)
                
                if not windows:
                    logger.warning("No suitable windows found")
                    messagebox.showinfo("No Windows", "No suitable target windows found. Please open the application you want to draw in first.")
                    return None
                
                # Create an enhanced selection dialog with previews
                root = tk.Tk()
                root.withdraw()
                
                dialog = tk.Toplevel(root)
                dialog.title("Select Drawing Window")
                dialog.geometry("700x600")
                dialog.attributes("-topmost", True)
                dialog.resizable(True, True)
                
                # Create a nicer UI with ttk
                style = ttk.Style()
                style.configure("TFrame", background="#f0f0f0")
                style.configure("TButton", font=("Arial", 10))
                style.configure("TLabel", font=("Arial", 11))
                
                main_frame = ttk.Frame(dialog, padding=10)
                main_frame.pack(fill=tk.BOTH, expand=True)
                
                # Instructions
                header_frame = ttk.Frame(main_frame)
                header_frame.pack(fill=tk.X, pady=(0, 10))
                
                ttk.Label(
                    header_frame, 
                    text="Select the application window where you want to draw:",
                    font=("Arial", 12, "bold")
                ).pack(side=tk.LEFT, pady=5)
                
                # Search box for filtering windows
                search_frame = ttk.Frame(main_frame)
                search_frame.pack(fill=tk.X, pady=(0, 10))
                
                ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
                
                search_var = tk.StringVar()
                search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
                search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                # Window list with details
                list_frame = ttk.Frame(main_frame)
                list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
                
                # Create headers
                headers_frame = ttk.Frame(list_frame)
                headers_frame.pack(fill=tk.X)
                
                ttk.Label(headers_frame, text="Window Title", width=40, font=("Arial", 10, "bold")).pack(side=tk.LEFT)
                ttk.Label(headers_frame, text="Size", width=15, font=("Arial", 10, "bold")).pack(side=tk.LEFT)
                
                # Create listbox with scrollbar in a frame
                listbox_frame = ttk.Frame(list_frame)
                listbox_frame.pack(fill=tk.BOTH, expand=True)
                
                scrollbar = ttk.Scrollbar(listbox_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                window_listbox = tk.Listbox(
                    listbox_frame, 
                    font=("Arial", 11),
                    selectmode=tk.SINGLE,
                    yscrollcommand=scrollbar.set,
                    height=15,
                    bd=1,
                    relief=tk.SOLID
                )
                window_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                scrollbar.config(command=window_listbox.yview)
                
                # Function to update the listbox based on search
                def update_listbox(*args):
                    search_text = search_var.get().lower()
                    window_listbox.delete(0, tk.END)
                    
                    for i, window in enumerate(windows):
                        title = window["title"]
                        # If searching, filter the windows
                        if not search_text or search_text in title.lower():
                            display_text = f"{title}"
                            if "width" in window and "height" in window:
                                display_text += f" ({window['width']}x{window['height']})"
                            window_listbox.insert(tk.END, display_text)
                
                # Connect search variable to update function
                search_var.trace("w", update_listbox)
                
                # Fill initial window list
                update_listbox()
                
                # Preview frame
                preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding=10)
                preview_frame.pack(fill=tk.X, pady=10)
                
                preview_label = ttk.Label(preview_frame, text="Select a window to see details")
                preview_label.pack(pady=5)
                
                # Storage variable for selection
                selected_window = [None]
                
                # Functions for selection
                def on_select():
                    selection = window_listbox.curselection()
                    if selection:
                        index = selection[0]
                        # Find which window this corresponds to after filtering
                        search_text = search_var.get().lower()
                        matched_windows = [w for w in windows if not search_text or search_text in w["title"].lower()]
                        if index < len(matched_windows):
                            selected_window[0] = matched_windows[index]
                            dialog.destroy()
                
                def on_listbox_select(event):
                    selection = window_listbox.curselection()
                    if selection:
                        index = selection[0]
                        # Find which window this corresponds to after filtering
                        search_text = search_var.get().lower()
                        matched_windows = [w for w in windows if not search_text or search_text in w["title"].lower()]
                        if index < len(matched_windows):
                            window = matched_windows[index]
                            # Update preview
                            preview_text = f"Title: {window['title']}\n"
                            if "width" in window and "height" in window:
                                preview_text += f"Size: {window['width']}x{window['height']}\n"
                            if "rect" in window:
                                preview_text += f"Position: ({window['rect'][0]}, {window['rect'][1]})"
                            
                            preview_label.config(text=preview_text)
                
                def on_double_click(event):
                    on_select()
                
                # Button frame
                button_frame = ttk.Frame(main_frame)
                button_frame.pack(fill=tk.X, pady=(5, 0))
                
                ttk.Button(
                    button_frame,
                    text="Cancel",
                    command=dialog.destroy,
                    style="TButton",
                    width=10
                ).pack(side=tk.RIGHT, padx=5)
                
                select_button = ttk.Button(
                    button_frame,
                    text="Select",
                    command=on_select,
                    style="TButton",
                    width=10
                )
                select_button.pack(side=tk.RIGHT, padx=5)
                
                # Bind events
                window_listbox.bind("<Double-1>", on_double_click)
                window_listbox.bind("<<ListboxSelect>>", on_listbox_select)
                
                # Set initial focus to the search box
                search_entry.focus_set()
                
                # Wait for selection
                dialog.transient(root)
                dialog.wait_window()
                
                # Process the selected window
                if selected_window[0]:
                    hwnd = selected_window[0]["hwnd"]
                    title = selected_window[0]["title"]
                    
                    try:
                        # Attempt to activate the window and bring it to front
                        if sys.platform == 'win32' and 'win32gui' in sys.modules:
                            # First try SetForegroundWindow
                            win32gui.SetForegroundWindow(hwnd)
                            
                            # If available, also try to restore the window if minimized
                            try:
                                import win32con
                                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            except:
                                pass
                                
                            logger.info(f"Activated window: '{title}' with hwnd: {hwnd}")
                        time.sleep(0.5)  # Wait longer for window to activate
                        return selected_window[0]
                    except Exception as e:
                        logger.error(f"Error activating window: {e}")
                        messagebox.showwarning("Activation Error", 
                                               f"Could not activate the selected window: {title}\n"
                                               "You may need to manually bring it to the front.")
                        return selected_window[0]  # Return anyway, let user handle activation
                        
                    return None
            
            else:
                # Fallback method for non-Windows platforms
                logger.warning("Window selection is limited on this platform")
                messagebox.showinfo("Platform Limitation", 
                                   "Advanced window selection is not available on this platform.\n"
                                   "Please manually activate the target application before drawing.")
                return {"title": "Manual Selection"}
                
        except Exception as e:
            logger.error(f"Error finding target windows: {e}")
            logger.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to enumerate windows: {str(e)}")
            return None
    
    @error_handler
    def draw_image(self):
        """Draw the processed image in the target application"""
        if not self.processed_image:
            logger.error("No processed image to draw")
            return False
            
        logger.info(f"Starting drawing process with parameters:")
        logger.info(f"  - Target application: {self.target_app}")
        logger.info(f"  - Drawing style: {self.style}")
        logger.info(f"  - Resolution: {self.resolution}x")
        logger.info(f"  - Drawing speed: {self.speed}s delay")
        logger.info(f"  - Image size: {self.processed_image.size[0]}x{self.processed_image.size[1]} pixels")
        logger.info(f"  - Canvas area: {self.canvas_area}")
        logger.info(f"  - Number of colors in palette: {len(self.palette)}")
        logger.info(f"  - Color positions defined: {len(self.color_positions)}")

        # Reset stop flag
        self.stop_drawing = False
        
        # Install keyboard handler for ESC key
        keyboard.on_press_key("esc", lambda _: self.stop_drawing_callback())
        
        try:
            # Get image data
            img_data = np.array(self.processed_image)
            height, width = img_data.shape[:2]
            
            # If canvas area is not set, use the center of the screen
            if not self.canvas_area:
                logger.info("Canvas area not set, using screen center")
                screen_width, screen_height = pyautogui.size()
                x1 = (screen_width - width) // 2
                y1 = (screen_height - height) // 2
                self.canvas_area = (x1, y1, x1 + width, y1 + height)
                logger.info(f"Auto-calculated canvas area: {self.canvas_area}")
            
            x1, y1, x2, y2 = self.canvas_area
            
            # Calculate pixel size
            pixel_width = (x2 - x1) / width
            pixel_height = (y2 - y1) / height
            
            logger.info(f"Pixel size: {pixel_width:.2f}x{pixel_height:.2f}")
            
            # Move mouse to drawing area
            pyautogui.moveTo(x1, y1)
            time.sleep(0.5)  # Give time to move

            # Optimize pyautogui for speed
            pyautogui.MINIMUM_DURATION = 0
            pyautogui.MINIMUM_SLEEP = 0
            pyautogui.PAUSE = 0
            
            # Drawing styles
            if self.style == "pixel":
                logger.info("Using pixel drawing style")
                # Draw pixel by pixel
                current_color = None
                pixels_drawn = 0
                skipped_pixels = 0
                start_time = time.time()
                
                # Prepare a list of pixels to draw, grouped by color for efficiency
                pixels_by_color = {}
                white_threshold = 245  # Threshold to consider a pixel as white (to skip)
                
                # Preprocess to group pixels by color for more efficient drawing
                logger.info("Preprocessing image to group pixels by color...")
                for y in range(height):
                    for x in range(width):
                        # Get color at pixel
                        if len(img_data.shape) == 3:
                            pixel_color = tuple(img_data[y, x][:3])  # RGB
                        else:
                            # Grayscale
                            pixel_color = (img_data[y, x], img_data[y, x], img_data[y, x])
                        
                        # Skip white pixels
                        if all(c >= white_threshold for c in pixel_color):
                            skipped_pixels += 1
                            continue
                            
                        # Skip transparent pixels
                        if len(img_data.shape) == 3 and img_data.shape[2] == 4 and img_data[y, x][3] == 0:
                            skipped_pixels += 1
                            continue
                        
                        # Find closest color in palette
                        target_color = self.find_closest_color(pixel_color)
                        
                        # Add to color group
                        if target_color not in pixels_by_color:
                            pixels_by_color[target_color] = []
                        
                        # Store pixel position
                        pos_x = x1 + (x * pixel_width) + (pixel_width / 2)
                        pos_y = y1 + (y * pixel_height) + (pixel_height / 2)
                        pixels_by_color[target_color].append((pos_x, pos_y))
                
                # Log preprocessing results
                total_pixels = height * width
                logger.info(f"Preprocessing complete. Found {len(pixels_by_color)} colors.")
                logger.info(f"Skipping {skipped_pixels} white/transparent pixels ({skipped_pixels/total_pixels*100:.1f}% of image)")
                logger.info(f"Will draw {total_pixels - skipped_pixels} pixels")
                
                # Sort colors from darkest to lightest for better visual progress
                sorted_colors = sorted(pixels_by_color.keys(), key=lambda c: sum(c))
                
                # Draw each color group
                for color in sorted_colors:
                    if self.stop_drawing:
                        logger.info("Drawing stopped by user")
                        return True
                    
                    # Set color
                    self.set_target_color(color)
                    current_color = color
                    time.sleep(max(0.2, self.speed * 2))  # Ensure color is selected
                    
                    # Get pixels for this color
                    pixels = pixels_by_color[color]
                    color_name = self.get_color_name(color) if hasattr(self, 'get_color_name') else str(color)
                    logger.info(f"Drawing {len(pixels)} pixels with color {color_name}")
                    
                    # Group pixels into clusters for more efficient drawing
                    # This reduces mouse travel distance
                    GRID_SIZE = 20
                    grid_cells = {}
                    
                    # Organize pixels into grid cells
                    for pos_x, pos_y in pixels:
                        grid_x = int((pos_x - x1) // GRID_SIZE)
                        grid_y = int((pos_y - y1) // GRID_SIZE)
                        cell_key = (grid_x, grid_y)
                        
                        if cell_key not in grid_cells:
                            grid_cells[cell_key] = []
                        
                        grid_cells[cell_key].append((pos_x, pos_y))
                    
                    # Process each cell
                    for cell_pixels in grid_cells.values():
                        # Sort pixels within cell for optimal path
                        if len(cell_pixels) > 1:
                            # Start with first pixel
                            sorted_pixels = [cell_pixels[0]]
                            remaining = cell_pixels[1:]
                            
                            # Find nearest neighbor each time
                            while remaining:
                                last = sorted_pixels[-1]
                                nearest_idx = 0
                                nearest_dist = float('inf')
                                
                                for i, pixel in enumerate(remaining):
                                    dist = ((pixel[0] - last[0])**2 + (pixel[1] - last[1])**2)**0.5
                                    if dist < nearest_dist:
                                        nearest_dist = dist
                                        nearest_idx = i
                                
                                sorted_pixels.append(remaining.pop(nearest_idx))
                            
                            cell_pixels = sorted_pixels
                        
                        # Draw pixels in cell
                        for pos_x, pos_y in cell_pixels:
                            if self.stop_drawing:
                                logger.info("Drawing stopped by user")
                                return True
                            
                            # Move and click with minimal delay
                            pyautogui.moveTo(pos_x, pos_y, duration=0)
                            pyautogui.click()
                            
                            pixels_drawn += 1
                            
                            # Minimal delay between pixels of same color
                            if self.speed > 0:
                                time.sleep(self.speed / 3)  # Faster drawing within same color
                        
                        # Log progress periodically
                        if pixels_drawn % 500 == 0:
                            elapsed = time.time() - start_time
                            pixels_per_second = pixels_drawn / elapsed if elapsed > 0 else 0
                            percent_complete = (pixels_drawn / (total_pixels - skipped_pixels)) * 100
                            logger.info(f"Progress: {pixels_drawn}/{total_pixels - skipped_pixels} pixels ({percent_complete:.1f}%) - {pixels_per_second:.1f} pixels/sec")
                
                # Log completion statistics
                elapsed = time.time() - start_time
                logger.info(f"Drawing completed: {pixels_drawn} pixels in {elapsed:.1f} seconds ({pixels_drawn/elapsed:.1f} pixels/sec)")
                logger.info(f"Skipped {skipped_pixels} white/transparent pixels")
            
            elif self.style == "outline":
                # For outline drawing, implement more efficient outline detection and drawing
                logger.info("Using outline drawing style")
                
                # Find all outline pixels (dark pixels)
                outline_pixels = []
                for y in range(height):
                    for x in range(width):
                        pixel = self.processed_image.getpixel((x, y))
                        # Only dark pixels are considered part of the outline
                        if sum(pixel) < 450:
                            outline_pixels.append((x, y))
                
                # Calculate total pixels for progress tracking
                total_points = len(outline_pixels)
                
                if total_points == 0:
                    messagebox.showinfo("Notice", "No outline pixels found in the image")
                    return False
                
                # Select black color for outline
                black_color = self.find_closest_color((0, 0, 0))
                if self.color_positions and black_color in self.color_positions:
                    color_x, color_y = self.color_positions[black_color]
                    pyautogui.click(color_x, color_y)
                    time.sleep(0.3)
                else:
                    # If color position not set, prompt user
                    messagebox.showinfo(
                        "Select Color", 
                        "Please click on the black color in your drawing program, then press OK to continue"
                    )
                    return False
                
                logger.info("Drawing outline...")
                
                # Group connected pixels into line segments
                visited = set()
                line_segments = []
                
                # Define directions for connected neighbors
                directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
                
                # Group connected points into line segments
                for point in outline_pixels:
                    x, y = point
                    if (x, y) in visited or self.stop_drawing:
                        continue
                    
                    # Start a new line segment
                    segment = [(x, y)]
                    visited.add((x, y))
                    
                    # Find connected points
                    current = (x, y)
                    while not self.stop_drawing:
                        found_next = False
                        for dx, dy in directions:
                            nx, ny = current[0] + dx, current[1] + dy
                            if (nx, ny) in outline_pixels and (nx, ny) not in visited:
                                segment.append((nx, ny))
                                visited.add((nx, ny))
                                current = (nx, ny)
                                found_next = True
                                break
                        
                        if not found_next:
                            break
                    
                    # Add complete segment
                    if len(segment) > 1:
                        line_segments.append(segment)
                
                # Draw each line segment
                points_drawn = 0
                for i, segment in enumerate(line_segments):
                    if self.stop_drawing:
                        break
                    
                    # Move to the beginning of the segment
                    first_x, first_y = segment[0]
                    pos_x = x1 + first_x
                    pos_y = y1 + first_y
                    pyautogui.moveTo(pos_x, pos_y)
                    
                    # Press down to draw a connected line
                    pyautogui.mouseDown()
                    
                    # Draw the line segment
                    for j, (x, y) in enumerate(segment[1:]):
                        try:
                            # Move to the next point in the line
                            pos_x = x1 + x
                            pos_y = y1 + y
                            pyautogui.moveTo(pos_x, pos_y, _pause=False)
                            
                            # Short delay for drawing accuracy
                            if j % 5 == 0:
                                time.sleep(self.speed * 0.5)
                                
                            # Update progress
                            points_drawn += 1
                            if points_drawn % 100 == 0:
                                percent_complete = (points_drawn / total_points) * 100
                                logger.info(f"Outline progress: {points_drawn}/{total_points} points ({percent_complete:.1f}%)")
                                
                        except Exception as e:
                            logger.error(f"Error while drawing outline: {e}")
                    
                    # Release to finish the line segment
                    pyautogui.mouseUp()
                    
                    # Short delay between segments
                    time.sleep(self.speed)
                
                # Log completion
                logger.info(f"Outline drawing completed: {points_drawn} points drawn")
            
            # Clean up and return
            keyboard.unhook_all()
            return True
            
        except Exception as e:
            logger.error(f"Error in drawing image: {e}")
            logger.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to draw image: {str(e)}")
            keyboard.unhook_all()
            return False
    
    def stop_drawing_callback(self):
        """Callback function to stop drawing when Esc is pressed"""
        self.stop_drawing = True
        
    def set_canvas_area(self, canvas_area):
        """Set the drawing canvas area"""
        self.canvas_area = canvas_area
        
    def set_color_positions(self, color_positions):
        """Set the color picker positions"""
        self.color_positions = color_positions

    def set_target_color(self, color):
        """Set target color and click it in the application"""
        try:
            self.target_color = color
            
            # Get color selection coords for common apps
            if self.target_app.lower() in ["mspaint", "paint"]:
                # MS Paint color palette coordinates and handling
                
                # Convert RGB color to closest available in the palette
                color_x, color_y = self.find_closest_color_in_palette(color)
                
                if color_x and color_y:
                    pyautogui.click(color_x, color_y)
                    time.sleep(0.2)
                    return True
                
            elif self.target_app.lower() in ["gartic", "gartic phone"]:
                # Gartic Phone color selection - scan the color palette area
                found = False
                tolerance = 20  # Color matching tolerance
                
                # Define the color palette region to scan (approximate for Gartic)
                # These coordinates can be adjusted based on screen resolution
                palette_region = (50, 50, 500, 100)  # Typical region for Gartic color palette
                
                # Try to locate the color button
                try:
                    screenshot = pyautogui.screenshot(region=palette_region)
                    width, height = screenshot.size
                    
                    for y in range(height):
                        for x in range(width):
                            pixel_color = screenshot.getpixel((x, y))
                            
                            # Check if this pixel matches our target color with tolerance
                            if self.is_color_similar(pixel_color, color, tolerance):
                                # Click this color in the actual screen coordinates
                                pyautogui.click(palette_region[0] + x, palette_region[1] + y)
                                time.sleep(0.2)
                                found = True
                                break
                        if found:
                            break
                        
                    if found:
                        return True
                except Exception as e:
                    print(f"Error finding color in palette: {e}")
            
            # Generic approach for other applications
            # Implement a color picker dialog using tkinter
            color_hex = "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
            
            if not hasattr(self, 'color_picker_shown'):
                self.color_picker_shown = False
            
            if not self.color_picker_shown:
                messagebox.showinfo("Color Selection", 
                                    "Please select the target color manually in the application.\n"
                                    f"Target color: {color_hex}\n"
                                    f"RGB: {color}")
                self.color_picker_shown = True
            
            # Create a small visual indicator of the color
            self.show_color_indicator(color)
            
            return True
            
        except Exception as e:
            print(f"Error setting target color: {e}")
            return False
            
    def show_color_indicator(self, color):
        """Show a small window with the target color"""
        color_window = tk.Toplevel()
        color_window.title("Target Color")
        color_window.geometry("200x100")
        color_window.attributes("-topmost", True)
        
        # Color indicator panel
        color_hex = "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
        color_panel = tk.Frame(color_window, bg=color_hex, width=100, height=50)
        color_panel.pack(pady=10)
        
        # Label showing RGB values
        label = tk.Label(color_window, text=f"RGB: {color}")
        label.pack()
        
        # Close button
        close_btn = tk.Button(color_window, text="Close", command=color_window.destroy)
        close_btn.pack(pady=5)
        
    def find_closest_color_in_palette(self, color):
        """Find the closest color in the MS Paint palette"""
        try:
            # First try to use fixed coordinates for standard MS Paint palette
            palette_regions = [
                # MS Paint palette in Windows 10/11
                {"region": (60, 80, 300, 60), "grid": (10, 2), "is_extended": False},
                # MS Paint palette in Windows 7 or alternative layout
                {"region": (280, 80, 400, 50), "grid": (10, 2), "is_extended": False},
                # Extended color palette (opened with "Edit Colors" option)
                {"region": (200, 200, 500, 300), "grid": None, "is_extended": True}
            ]
            
            target_rgb = color
            min_distance = float('inf')
            best_x, best_y = None, None
            
            for palette in palette_regions:
                region = palette["region"]
                try:
                    screenshot = pyautogui.screenshot(region=region)
                    
                    if palette["grid"] and not palette["is_extended"]:
                        # For standard color palettes with grid layout
                        grid_width, grid_height = palette["grid"]
                        cell_width = region[2] // grid_width
                        cell_height = region[3] // grid_height
                        
                        for row in range(grid_height):
                            for col in range(grid_width):
                                # Get center of each color cell
                                x = region[0] + (col * cell_width) + (cell_width // 2)
                                y = region[1] + (row * cell_height) + (cell_height // 2)
                                
                                # Sample color at this position
                                try:
                                    sample = pyautogui.screenshot(region=(x-1, y-1, 3, 3))
                                    sample_color = sample.getpixel((1, 1))  # Center pixel
                                    
                                    distance = self.color_distance(sample_color, target_rgb)
                                    if distance < min_distance:
                                        min_distance = distance
                                        best_x, best_y = x, y
                                except Exception:
                                    continue
                    else:
                        # For extended color palettes or custom layouts, scan pixel by pixel
                        width, height = screenshot.size
                        
                        for y in range(0, height, 5):  # Sample every 5 pixels for efficiency
                            for x in range(0, width, 5):
                                try:
                                    pixel_color = screenshot.getpixel((x, y))
                                    
                                    # Ignore white/gray background pixels
                                    if self.is_gray_or_white(pixel_color):
                                        continue
                                        
                                    distance = self.color_distance(pixel_color, target_rgb)
                                    if distance < min_distance:
                                        min_distance = distance
                                        best_x, best_y = region[0] + x, region[1] + y
                                except Exception:
                                    continue
                except Exception as e:
                    print(f"Error scanning palette region: {e}")
                    continue
                
                # If we found a close match, return it
                if min_distance < 50 and best_x and best_y:
                    return best_x, best_y
            
            # If no good match found in palette regions, try to find it in the main window
            if min_distance > 50 or not best_x or not best_y:
                # Try to find the "Edit Colors" button and click it
                try:
                    edit_colors_btn = pyautogui.locateOnScreen('auto_draw/resources/edit_colors.png', 
                                                              confidence=0.7)
                    if edit_colors_btn:
                        pyautogui.click(pyautogui.center(edit_colors_btn))
                        time.sleep(1)
                        
                        # Try the extended palette again
                        return self.find_closest_color_in_palette(color)
                except Exception:
                    pass
            
            return best_x, best_y
            
        except Exception as e:
            print(f"Error finding color in palette: {e}")
            return None, None
            
    def is_gray_or_white(self, color):
        """Check if a color is gray or white (for filtering background pixels)"""
        if len(color) >= 3:
            r, g, b = color[0], color[1], color[2]
            
            # Check if it's white or near-white
            if r > 240 and g > 240 and b > 240:
                return True
                
            # Check if it's gray (all channels similar)
            avg = (r + g + b) / 3
            diff_r = abs(r - avg)
            diff_g = abs(g - avg)
            diff_b = abs(b - avg)
            
            return diff_r < 10 and diff_g < 10 and diff_b < 10
        
        return False
        
    def color_distance(self, color1, color2):
        """Calculate Euclidean distance between two colors"""
        if len(color1) >= 3 and len(color2) >= 3:
            r1, g1, b1 = color1[0], color1[1], color1[2]
            r2, g2, b2 = color2[0], color2[1], color2[2]
            
            # Weighted RGB distance (human eyes are more sensitive to green)
            return ((r2-r1)**2 * 0.3 + (g2-g1)**2 * 0.59 + (b2-b1)**2 * 0.11) ** 0.5
        
        return float('inf')
    
    def is_color_similar(self, color1, color2, tolerance=20):
        """Check if two colors are similar within tolerance"""
        return self.color_distance(color1, color2) <= tolerance

    def get_color_name(self, color):
        """Get name for a color"""
        color_names = {
            (0, 0, 0): "Black",
            (255, 255, 255): "White",
            (255, 0, 0): "Red",
            (0, 255, 0): "Green",
            (0, 0, 255): "Blue",
            (255, 255, 0): "Yellow",
            (255, 0, 255): "Magenta",
            (0, 255, 255): "Cyan",
            (128, 128, 128): "Gray",
            (128, 0, 0): "Maroon",
            (0, 128, 0): "Dark Green",
            (0, 0, 128): "Navy Blue",
            (128, 128, 0): "Olive",
            (128, 0, 128): "Purple",
            (0, 128, 128): "Teal"
        }
        
        # Find exact match
        if color in color_names:
            return color_names[color]
        
        # Find closest named color
        min_distance = float('inf')
        closest_name = "Custom Color"
        
        for named_color, name in color_names.items():
            distance = self.color_distance(color, named_color)
            if distance < min_distance:
                min_distance = distance
                closest_name = name
        
        # Only return the name if it's reasonably close
        if min_distance < 30:
            return f"{closest_name}-like"
        else:
            return f"RGB({color[0]},{color[1]},{color[2]})"

class AutoDrawGUI:
    @error_handler
    def __init__(self, root):
        """Initialize the GUI application with error handling
        
        Sets up the main application window, UI components, and initializes
        all required subsystems with proper error handling.
        
        Args:
            root: The tkinter root window
        """
        self.root = root
        self.root.title("AutoDraw")
        self.root.geometry("1000x750")
        self.root.minsize(900, 700)
        
        # Initialize language and theme
        self.lang = "en"
        self.theme_mode = "light"
        self.theme = LIGHT_THEME
        self.translations = TRANSLATIONS[self.lang]
        
        # Create instance of AutoDraw for backend functionality
        self.auto_draw = AutoDraw()
        
        # Initialize variables
        self.canvas_info_var = tk.StringVar(value=self.translations["not_set"])
        self.color_pos_info_var = tk.StringVar(value=self.translations["not_set"])
        self.status_var = tk.StringVar(value=self.translations["ready"])
        self.target_var = tk.StringVar(value="MSPaint")
        self.custom_target_var = tk.StringVar()
        self.style_var = tk.StringVar(value="pixel")
        self.resolution_var = tk.DoubleVar(value=1.0)
        self.speed_var = tk.DoubleVar(value=0.001)
        self.palette_var = tk.StringVar(value="default")
        self.photo_img = None  # Reference for displayed image
        
        # Load recent files
        self.recent_files = []
        self.load_recent_files()
        
        # Create drawing area selector
        self.drawing_area_selector = DrawingAreaSelector(self.lang)
        
        # Set up custom styles
        self.apply_theme()
        
        # Create UI widgets
        self.create_widgets()
        
        # Create menu
        self.create_menu()
        
        # Set up keyboard shortcuts
        self.setup_shortcuts()
        
        # Update status
        self.status_var.set(self.translations["ready"])
        
        # Log successful initialization
        logger.info("AutoDrawGUI initialized successfully")
    
    def load_recent_files(self):
        """Load recently opened files from settings"""
        try:
            # Check if the auto_draw object has recent_files in its settings
            config_file = self.auto_draw.config_file
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    settings = json.load(f)
                if "recent_files" in settings:
                    self.recent_files = settings["recent_files"]
                    # Filter out files that no longer exist
                    self.recent_files = [f for f in self.recent_files if os.path.exists(f)]
        except Exception as e:
            print(f"Error loading recent files: {e}")
            
    def save_recent_files(self):
        """Save recently opened files to settings"""
        try:
            config_file = self.auto_draw.config_file
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    settings = json.load(f)
            else:
                settings = {}
                
            settings["recent_files"] = self.recent_files
            
            with open(config_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving recent files: {e}")
            
    def add_to_recent_files(self, file_path):
        """Add a file to recent files list"""
        if not os.path.exists(file_path):
            return
            
        # Remove if already exists
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
            
        # Add to the beginning
        self.recent_files.insert(0, file_path)
        
        # Limit to max number
        self.recent_files = self.recent_files[:self.max_recent_files]
        
        # Save to settings
        self.save_recent_files()
        
        # Update menu
        self.update_recent_files_menu()
        
    def update_recent_files_menu(self):
        """Update the recent files section in the File menu"""
        if hasattr(self, 'recent_files_menu'):
            # Clear existing items
            self.recent_files_menu.delete(0, tk.END)
            
            if not self.recent_files:
                self.recent_files_menu.add_command(label="No recent files", state=tk.DISABLED)
            else:
                for file_path in self.recent_files:
                    # Get just the filename for display
                    file_name = os.path.basename(file_path)
                    self.recent_files_menu.add_command(
                        label=file_name,
                        command=lambda path=file_path: self.load_and_preview_image(path)
                    )
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts for common actions"""
        # File operations
        self.root.bind("<Control-o>", lambda e: self.select_local_file())  # Ctrl+O: Open file
        self.root.bind("<Control-s>", lambda e: self.save_settings())      # Ctrl+S: Save settings
        
        # Drawing
        self.root.bind("<F5>", lambda e: self.start_drawing())             # F5: Start drawing
        self.root.bind("<F6>", lambda e: self.select_canvas_area())        # F6: Set drawing area
        self.root.bind("<F7>", lambda e: self.set_color_positions())       # F7: Set color positions
        
        # App settings
        self.root.bind("<Control-t>", lambda e: self.toggle_theme())       # Ctrl+T: Toggle theme
        
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        if self.theme_mode == "light":
            self.change_theme("dark")
        else:
            self.change_theme("light")
    
    def apply_theme(self):
        """Apply the current theme to the UI with modern styling"""
        if self.theme_mode == "dark":
            self.theme = DARK_THEME.copy()
        else:
            self.theme = LIGHT_THEME.copy()
        
        # Configure ttk styles with modern look
        self.style = ttk.Style()
        
        # Basic element styling
        self.style.configure("TFrame", background=self.theme["bg"])
        self.style.configure("TLabel", background=self.theme["bg"], foreground=self.theme["fg"], font=("Segoe UI", 10))
        self.style.configure("TLabelframe", background=self.theme["bg"], foreground=self.theme["fg"])
        self.style.configure("TLabelframe.Label", background=self.theme["bg"], foreground=self.theme["fg"], font=("Segoe UI", 11, "bold"))
        
        # Button styling - more modern look with rounded corners where possible
        self.style.configure("TButton", 
                            background=self.theme["control_bg"], 
                            foreground=self.theme["fg"],
                            font=("Segoe UI", 10),
                            padding=5)
        self.style.map("TButton",
                      background=[('active', self.theme["hover"])],
                      foreground=[('active', self.theme["fg"])])
        
        # Accent button - prominent primary action button
        self.style.configure("Accent.TButton", 
                            background=self.theme["accent"], 
                            foreground=self.theme["accent_fg"], 
                            font=("Segoe UI", 12, "bold"),
                            padding=8)
        self.style.map("Accent.TButton",
                      background=[('active', self.theme["control_active"])],
                      foreground=[('active', self.theme["accent_fg"])])
        
        # Success button - for positive actions
        self.style.configure("Success.TButton", 
                            background=self.theme["success"], 
                            foreground=self.theme["accent_fg"], 
                            font=("Segoe UI", 11),
                            padding=5)
        self.style.map("Success.TButton",
                      background=[('active', self.theme["success"])])
        
        # Info button - for neutral actions
        self.style.configure("Info.TButton", 
                            background=self.theme["info"], 
                            foreground=self.theme["accent_fg"], 
                            font=("Segoe UI", 11),
                            padding=5)
        
        # Danger button - for destructive actions
        self.style.configure("Danger.TButton", 
                            background=self.theme["danger"], 
                            foreground=self.theme["accent_fg"], 
                            font=("Segoe UI", 11),
                            padding=5)
        
        # ComboBox styling
        self.style.configure("TCombobox", 
                            fieldbackground=self.theme["control_bg"],
                            background=self.theme["control_bg"],
                            foreground=self.theme["fg"])
        
        # Scale styling
        self.style.configure("TScale", 
                           background=self.theme["bg"],
                           troughcolor=self.theme["secondary"],
                           sliderrelief="flat")
        
        # Radiobutton styling
        self.style.configure("TRadiobutton", 
                           background=self.theme["bg"],
                           foreground=self.theme["fg"],
                           font=("Segoe UI", 10))
        
        # Status bar styling
        self.style.configure("Status.TLabel", 
                           background=self.theme["header_bg"],
                           foreground=self.theme["fg"],
                           font=("Segoe UI", 9))
        
        # Section header styling
        self.style.configure("Header.TLabel", 
                           background=self.theme["bg"],
                           foreground=self.theme["accent"],
                           font=("Segoe UI", 12, "bold"))
        
        # Apply theme to root window
        self.root.configure(bg=self.theme["bg"])
    
    def create_menu(self):
        """Create the application menu"""
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        
        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        
        # Add file operations
        file_menu.add_command(label="Open Image... (Ctrl+O)", command=self.select_local_file)
        file_menu.add_command(label="Open from URL...", command=self.enter_url)
        
        # Recent files submenu
        self.recent_files_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self.recent_files_menu)
        self.update_recent_files_menu()
        
        file_menu.add_separator()
        file_menu.add_command(label="Save Settings (Ctrl+S)", command=self.save_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Draw menu
        draw_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Draw", menu=draw_menu)
        
        # Add drawing operations
        draw_menu.add_command(label="Start Drawing (F5)", command=self.start_drawing)
        draw_menu.add_separator()
        draw_menu.add_command(label="Set Drawing Area (F6)", command=self.select_canvas_area)
        draw_menu.add_command(label="Reset Drawing Area", command=self.reset_canvas_area)
        draw_menu.add_separator()
        draw_menu.add_command(label="Set Color Positions (F7)", command=self.set_color_positions)
        draw_menu.add_command(label="Reset Color Positions", command=self.reset_color_positions)
        
        # Settings menu
        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label=self.translations["settings"], menu=self.settings_menu)
        
        # Language submenu
        self.language_menu = tk.Menu(self.settings_menu, tearoff=0)
        self.settings_menu.add_cascade(label=self.translations["language"], menu=self.language_menu)
        
        # Add language options
        for lang_code, lang_name in LANGUAGES.items():
            self.language_menu.add_command(label=lang_name, command=lambda lc=lang_code: self.change_language(lc))
        
        # Theme submenu
        self.theme_menu = tk.Menu(self.settings_menu, tearoff=0)
        self.settings_menu.add_cascade(label=self.translations["theme"], menu=self.theme_menu)
        
        # Add theme options
        self.theme_menu.add_command(label=f"{self.translations['light']} (Ctrl+T)", 
                                     command=lambda: self.change_theme("light"))
        self.theme_menu.add_command(label=f"{self.translations['dark']} (Ctrl+T)", 
                                     command=lambda: self.change_theme("dark"))
        
        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        
        # Add help options
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_command(label="About", command=self.show_about)
    
    def change_language(self, lang_code):
        """Change the UI language"""
        if lang_code != self.lang:
            self.lang = lang_code
            self.translations = TRANSLATIONS[self.lang]
            self.drawing_area_selector = DrawingAreaSelector(self.lang)
            
            # Recreate the widgets with new language
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.create_widgets()
            self.create_menu()
    
    def change_theme(self, theme_mode):
        """Change the UI theme"""
        if theme_mode != self.theme_mode:
            self.theme_mode = theme_mode
            self.apply_theme()
            
            # Recreate the widgets with new theme
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.create_widgets()
            self.create_menu()
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About AutoDraw",
            self.translations["version"].format(VERSION, AUTHOR)
        )
    
    def show_shortcuts(self):
        """Show keyboard shortcuts dialog"""
        shortcuts = [
            ("Ctrl+O", "Open image file"),
            ("Ctrl+S", "Save settings"),
            ("F5", "Start drawing"),
            ("F6", "Set drawing area"),
            ("F7", "Set color positions"),
            ("Ctrl+T", "Toggle theme"),
            ("Esc", "Stop drawing (while drawing)")
        ]
        
        shortcut_text = "\n".join([f"{key:<10} : {desc}" for key, desc in shortcuts])
        
        messagebox.showinfo(
            "Keyboard Shortcuts",
            f"Available keyboard shortcuts:\n\n{shortcut_text}"
        )
    
    def create_widgets(self):
        """Create the GUI widgets with improved controls for speed and precision"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create left panel (controls)
        controls_frame = ttk.LabelFrame(main_frame, text=self.translations["controls"], padding=10)
        controls_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Create scrollable controls frame
        controls_canvas = tk.Canvas(controls_frame)
        controls_scrollbar = ttk.Scrollbar(controls_frame, orient="vertical", command=controls_canvas.yview)
        controls_scrollable = ttk.Frame(controls_canvas)

        controls_scrollable.bind(
            "<Configure>",
            lambda e: controls_canvas.configure(scrollregion=controls_canvas.bbox("all"))
        )

        controls_canvas.create_window((0, 0), window=controls_scrollable, anchor="nw")
        controls_canvas.configure(yscrollcommand=controls_scrollbar.set)

        # Configure scrolling with mousewheel
        def _on_mousewheel(event):
            controls_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        controls_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        controls_canvas.pack(side="left", fill="both", expand=True)
        controls_scrollbar.pack(side="right", fill="y")

        # Control sections
        current_row = 0
        
        # Image source section
        current_row = self.create_section_header(controls_scrollable, self.translations["image_source"], current_row)
        
        # Local file button
        ttk.Button(
            controls_scrollable, 
            text=self.translations["local_file"], 
            command=self.select_local_file
        ).grid(row=current_row, column=0, sticky="ew", padx=5, pady=2)
        
        # URL button
        ttk.Button(
            controls_scrollable, 
            text=self.translations["url"], 
            command=self.enter_url
        ).grid(row=current_row, column=1, sticky="ew", padx=5, pady=2)
        
        current_row += 1
        
        # Target application section
        current_row = self.create_section_header(controls_scrollable, self.translations["target_app"], current_row)
        
        # Target app dropdown
        self.target_var = tk.StringVar(value="mspaint")
        target_combo = ttk.Combobox(
            controls_scrollable, 
            textvariable=self.target_var,
            values=["mspaint", "gartic", self.translations["custom"]]
        )
        target_combo.grid(row=current_row, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        target_combo.bind("<<ComboboxSelected>>", self.on_target_change)
        
        current_row += 1
        
        # Custom target button (initially hidden)
        self.custom_target_button = ttk.Button(
            controls_scrollable,
            text=self.translations["custom_target"],
            command=self.select_target_window
        )
        
        # Show if "custom" is selected
        if self.target_var.get() == self.translations["custom"]:
            self.custom_target_button.grid(row=current_row, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
            current_row += 1
        
        # Drawing area section
        current_row = self.create_section_header(controls_scrollable, self.translations["drawing_area"], current_row)
        
        # Set drawing area button
        ttk.Button(
            controls_scrollable, 
            text=self.translations["set_drawing_area"], 
            command=self.select_canvas_area
        ).grid(row=current_row, column=0, sticky="ew", padx=5, pady=2)
        
        # Reset button
        ttk.Button(
            controls_scrollable, 
            text=self.translations["reset"], 
            command=self.reset_canvas_area
        ).grid(row=current_row, column=1, sticky="ew", padx=5, pady=2)
        
        current_row += 1
        
        # Drawing area info
        self.canvas_info_var = tk.StringVar(value=self.translations["not_set"])
        ttk.Label(
            controls_scrollable, 
            textvariable=self.canvas_info_var,
            font=("Arial", 9)
        ).grid(row=current_row, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        
        current_row += 1
        
        # Color positions section
        current_row = self.create_section_header(controls_scrollable, self.translations["color_positions"], current_row)
        
        # Set color positions button
        ttk.Button(
            controls_scrollable, 
            text=self.translations["set_color_positions"], 
            command=self.set_color_positions
        ).grid(row=current_row, column=0, sticky="ew", padx=5, pady=2)
        
        # Reset color positions button
        ttk.Button(
            controls_scrollable, 
            text=self.translations["reset"], 
            command=self.reset_color_positions
        ).grid(row=current_row, column=1, sticky="ew", padx=5, pady=2)
        
        current_row += 1
        
        # Color positions info
        self.color_pos_info_var = tk.StringVar(value=self.translations["not_set"])
        ttk.Label(
            controls_scrollable, 
            textvariable=self.color_pos_info_var,
            font=("Arial", 9)
        ).grid(row=current_row, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        
        current_row += 1
        
        # Drawing style section
        current_row = self.create_section_header(controls_scrollable, self.translations["drawing_style"], current_row)
        
        # Style options
        self.style_var = tk.StringVar(value="pixel")
        ttk.Radiobutton(
            controls_scrollable, 
            text=self.translations["pixel"], 
            variable=self.style_var, 
            value="pixel"
        ).grid(row=current_row, column=0, sticky="w", padx=5, pady=2)
        
        ttk.Radiobutton(
            controls_scrollable, 
            text=self.translations["outline"], 
            variable=self.style_var, 
            value="outline"
        ).grid(row=current_row, column=1, sticky="w", padx=5, pady=2)
        
        current_row += 1
        
        # Resolution section
        current_row = self.create_section_header(controls_scrollable, self.translations["resolution"], current_row)
        
        # Resolution slider
        self.resolution_var = tk.DoubleVar(value=1.0)
        resolution_scale = ttk.Scale(
            controls_scrollable,
            from_=0.25,
            to=2.0,
            variable=self.resolution_var,
            orient="horizontal"
        )
        resolution_scale.grid(row=current_row, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        
        current_row += 1
        
        # Resolution label
        resolution_label = ttk.Label(
            controls_scrollable,
            text="1.0x"
        )
        resolution_label.grid(row=current_row, column=0, columnspan=2, sticky="e", padx=5, pady=2)
        
        # Update resolution label on slider change
        def update_resolution_label(*args):
            resolution_label.config(text=f"{self.resolution_var.get():.2f}x")
        
        self.resolution_var.trace("w", update_resolution_label)
        
        current_row += 1
        
        # Drawing speed section
        current_row = self.create_section_header(controls_scrollable, self.translations["drawing_speed"], current_row)
        
        # Speed slider
        self.speed_var = tk.DoubleVar(value=0.001)
        speed_scale = ttk.Scale(
            controls_scrollable,
            from_=0.000,
            to=0.01,
            variable=self.speed_var,
            orient="horizontal"
        )
        speed_scale.grid(row=current_row, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        
        current_row += 1
        
        # Speed label
        speed_label = ttk.Label(
            controls_scrollable,
            text="0.001s"
        )
        speed_label.grid(row=current_row, column=0, columnspan=2, sticky="e", padx=5, pady=2)
        
        # Update speed label on slider change
        def update_speed_label(*args):
            speed_label.config(text=f"{self.speed_var.get():.4f}s")
        
        self.speed_var.trace("w", update_speed_label)
        
        current_row += 1
        
        # Performance optimization frame (NEW)
        current_row = self.create_section_header(controls_scrollable, "Drawing Optimizations", current_row)
        
        # Skip white pixels option
        self.skip_white_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls_scrollable,
            text="Skip white pixels",
            variable=self.skip_white_var,
        ).grid(row=current_row, column=0, sticky="w", padx=5, pady=2)
        
        # Color optimization option
        self.optimize_colors_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls_scrollable,
            text="Optimize color changes",
            variable=self.optimize_colors_var,
        ).grid(row=current_row, column=1, sticky="w", padx=5, pady=2)
        
        current_row += 1
        
        # Drawing strategy dropdown (NEW)
        ttk.Label(
            controls_scrollable,
            text="Drawing Strategy:"
        ).grid(row=current_row, column=0, sticky="w", padx=5, pady=2)
        
        self.strategy_var = tk.StringVar(value="optimized")
        strategy_combo = ttk.Combobox(
            controls_scrollable,
            textvariable=self.strategy_var,
            values=["optimized", "line-by-line", "color-by-color"],
            width=15
        )
        strategy_combo.grid(row=current_row, column=1, sticky="ew", padx=5, pady=2)
        
        current_row += 1
        
        # Precision vs. Speed slider (NEW)
        ttk.Label(
            controls_scrollable,
            text="Precision vs. Speed:"
        ).grid(row=current_row, column=0, sticky="w", padx=5, pady=2)
        
        self.precision_var = tk.IntVar(value=50)
        precision_scale = ttk.Scale(
            controls_scrollable,
            from_=0,
            to=100,
            variable=self.precision_var,
            orient="horizontal"
        )
        precision_scale.grid(row=current_row, column=1, sticky="ew", padx=5, pady=2)
        
        current_row += 1
        
        # Add description of slider
        precision_label = ttk.Label(
            controls_scrollable,
            text="Balanced",
            font=("Arial", 9)
        )
        precision_label.grid(row=current_row, column=1, sticky="e", padx=5, pady=2)
        
        # Update label on slider change
        def update_precision_label(*args):
            value = self.precision_var.get()
            if value < 30:
                precision_label.config(text="Faster")
            elif value > 70:
                precision_label.config(text="More precise")
            else:
                precision_label.config(text="Balanced")
        
        self.precision_var.trace("w", update_precision_label)
        
        current_row += 1
        
        # Color palette section
        current_row = self.create_section_header(controls_scrollable, self.translations["color_palette"], current_row)
        
        # Palette frame
        palette_frame = ttk.Frame(controls_scrollable)
        palette_frame.grid(row=current_row, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        palette_frame.columnconfigure(0, weight=1)
        palette_frame.columnconfigure(1, weight=1)
        
        # Default palette button
        ttk.Button(
            palette_frame, 
            text=self.translations["default"], 
            command=self.use_default_palette
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        
        # Custom palette button
        ttk.Button(
            palette_frame, 
            text=self.translations["custom"], 
            command=self.select_palette_file
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))
        
        current_row += 1
        
        # Draw button
        draw_button = ttk.Button(
            controls_scrollable,
            text=self.translations["draw"],
            command=self.start_drawing,
            style="Accent.TButton"
        )
        draw_button.grid(row=current_row, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        
        # Create custom style for the accent button
        self.style.configure("Accent.TButton", font=("Arial", 12, "bold"))
        
        current_row += 1
        
        # Status label
        self.status_var = tk.StringVar(value=self.translations["ready"])
        status_label = ttk.Label(
            controls_scrollable,
            textvariable=self.status_var,
            font=("Arial", 10)
        )
        status_label.grid(row=current_row, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        
        current_row += 1
        
        # Create right panel (preview)
        preview_frame = ttk.LabelFrame(main_frame, text=self.translations["preview"], padding=10)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Preview canvas
        self.preview_canvas = tk.Canvas(
            preview_frame, 
            bg=self.theme_colors["canvas_bg"],
            highlightthickness=1,
            highlightbackground=self.theme_colors["border"]
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # No image label
        self.no_image_label = ttk.Label(
            self.preview_canvas,
            text=self.translations["no_image"],
            font=("Arial", 12),
            background=self.theme_colors["canvas_bg"],
            foreground=self.theme_colors["fg"]
        )
        self.no_image_label.pack(expand=True)

        # Set up event for canvas resize
        self.preview_canvas.bind("<Configure>", self.display_preview)
    
    def create_section_header(self, parent, text, row):
        """Create a section header with modern styling"""
        header = ttk.Label(parent, text=text, style="Header.TLabel")
        header.grid(row=row, column=0, sticky=tk.W, pady=(15, 5), padx=10)
        
        # Add subtle separator line
        separator = ttk.Separator(parent, orient="horizontal")
        separator.grid(row=row+1, column=0, sticky=tk.W+tk.E, padx=10)
        
        return header
    
    def save_settings(self):
        """Save current settings to file"""
        # Update auto_draw settings from GUI
        self.auto_draw.target_app = self.get_target_app()
        self.auto_draw.style = self.style_var.get()
        self.auto_draw.resolution = self.resolution_var.get()
        self.auto_draw.speed = self.speed_var.get()
        
        # Add optimization settings if they exist
        if hasattr(self, 'skip_white_var'):
            self.auto_draw.skip_white = self.skip_white_var.get()
        
        if hasattr(self, 'optimize_colors_var'):
            self.auto_draw.optimize_colors = self.optimize_colors_var.get()
            
        if hasattr(self, 'strategy_var'):
            self.auto_draw.drawing_strategy = self.strategy_var.get()
            
        if hasattr(self, 'precision_var'):
            self.auto_draw.precision_value = self.precision_var.get()
        
        # Save settings
        if self.auto_draw.save_settings():
            self.status_var.set(self.translations["settings_saved"])
        else:
            self.status_var.set(self.translations["settings_save_error"])
            messagebox.showerror(self.translations["error"], self.translations["settings_save_error"])
    
    def select_target_window(self):
        """Improved method to select target window by showing a list"""
        self.status_var.set("Selecting target window...")
        self.root.update_idletasks()
        
        try:
            # Use the improved find_target_window method from auto_draw
            window_info = self.auto_draw.find_target_window()
            
            if window_info:
                # Set window title as target app
                self.target_var.set("Custom...")
                self.custom_target_var.set(window_info["title"])
                self.custom_target_entry.grid()  # Show the entry
                self.target_info_var.set(f"Selected window: {window_info['title']}")
                self.auto_draw.target_app = window_info["title"]
                self.status_var.set("Target window set")
            else:
                self.status_var.set("Window selection cancelled")
        except Exception as e:
            messagebox.showerror(self.translations["error"], f"{self.translations['error_window']} {str(e)}")
            self.status_var.set("Window selection failed")
    
    def select_local_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.svg"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            # Add to recent files
            self.add_to_recent_files(file_path)
            # Load and preview the image
            self.load_and_preview_image(file_path)
    
    def enter_url(self):
        """Load image from URL with improved reliability and user feedback
        
        Prompts user for URL input, validates the URL format, and attempts to load
        the image with appropriate error handling and status updates.
        """
        try:
            # Show input dialog with descriptive instructions
            url = simpledialog.askstring(
                "Load Image from URL", 
                "Enter the URL of an image to load:\n\n"
                "For example: https://example.com/image.jpg\n\n"
                "Make sure the URL points directly to an image file."
            )
            
            if not url:
                return  # User cancelled
                
            # Basic URL validation and correction
            if not re.match(r'^https?://', url):
                # Try to add https:// prefix if missing
                url = "https://" + url
                
            self.status_var.set(f"Downloading image from {url}...")
            self.root.update_idletasks()
            
            # Use thread to prevent UI freezing during download
            def download_thread():
                try:
                    # Prepare request headers to mimic a browser
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': 'https://www.google.com/'
                    }
                    
                    # Perform the request with a reasonable timeout
                    response = requests.get(url, headers=headers, timeout=15)
                    
                    # Check for HTTP errors
                    response.raise_for_status()
                    
                    # Check if the content is actually an image
                    content_type = response.headers.get('Content-Type', '')
                    
                    if content_type.startswith('image/'):
                        # It's an image, load it directly
                        image_data = BytesIO(response.content)
                        
                        # Schedule UI update in the main thread
                        self.root.after(0, lambda: self.load_and_preview_image(image_data))
                    else:
                        # Not an image, check if it's HTML that might contain an image
                        self.root.after(0, lambda: messagebox.showerror(
                            "Error", 
                            f"URL does not point to an image (Content-Type: {content_type}).\n\n"
                            "Please provide a direct link to an image file."
                        ))
                        self.root.after(0, lambda: self.status_var.set("Ready"))
                        
                except requests.exceptions.RequestException as e:
                    # Network-related errors
                    self.root.after(0, lambda: messagebox.showerror(
                        "Network Error", 
                        f"Failed to download image from URL:\n{str(e)}"
                    ))
                    self.root.after(0, lambda: self.status_var.set("Ready"))
                    
                except Exception as e:
                    # Other unexpected errors
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", 
                        f"Unexpected error processing URL:\n{str(e)}"
                    ))
                    self.root.after(0, lambda: self.status_var.set("Ready"))
            
            # Start download in background thread
            threading.Thread(target=download_thread, daemon=True).start()
                
        except Exception as e:
            messagebox.showerror("Error", f"Error processing URL: {str(e)}")
            self.status_var.set("Ready")
    
    def on_target_change(self, event):
        if self.target_var.get() == "Custom...":
            self.custom_target_entry.grid()
        else:
            self.custom_target_entry.grid_remove()
    
    def use_default_palette(self):
        target = self.get_target_app()
        self.auto_draw.palette = self.auto_draw.get_default_palette(target)
        self.status_var.set(f"Default palette for {target} loaded")
    
    def select_palette_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Palette File",
            filetypes=[
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            if self.auto_draw.load_palette(file_path):
                self.status_var.set(f"Palette loaded from {file_path}")
            else:
                messagebox.showerror(self.translations["error"], "Failed to load palette file")
            
    @error_handler
    def load_and_preview_image(self, source):
        """تحسين دالة تحميل الصورة للعمل مع الملفات المحلية روابط URL والبيانات الثنائية"""
        self.status_var.set(f"جارِ تحميل الصورة...")
        self.root.update_idletasks()
        
        try:
            if self.auto_draw.load_image(source):
                self.display_preview()
                img_width, img_height = self.auto_draw.image.size
                self.status_var.set(f"تم تحميل الصورة بنجاح - الأبعاد: {img_width}×{img_height}")
            else:
                messagebox.showerror(self.translations["error"], "فشل تحميل الصورة")
                self.status_var.set(self.translations["ready"])
        except Exception as e:
            messagebox.showerror(self.translations["error"], f"حدث خطأ أثناء تحميل الصورة: {str(e)}")
            self.status_var.set(self.translations["ready"])
    
    @error_handler
    def display_preview(self):
        if self.auto_draw.image:
            # Resize image to fit canvas while maintaining aspect ratio
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Make sure we have actual dimensions
            if canvas_width < 10:
                canvas_width = 400
            if canvas_height < 10:
                canvas_height = 400
            
            img_width, img_height = self.auto_draw.image.size
            
            # Calculate scale factor
            scale = min(canvas_width / img_width, canvas_height / img_height)
            
            # Resize image for display
            display_width = int(img_width * scale)
            display_height = int(img_height * scale)
            
            display_img = self.auto_draw.image.resize((display_width, display_height), Image.LANCZOS)
            
            # Convert to PhotoImage for display
            self.photo_img = ImageTk.PhotoImage(display_img)
            
            # Clear previous image
            self.canvas.delete("all")
            
            # Display new image
            self.canvas.create_image(
                canvas_width // 2,
                canvas_height // 2,
                image=self.photo_img,
                anchor=tk.CENTER
            )
    
    def get_target_app(self):
        if self.target_var.get() == "Custom...":
            return self.custom_target_var.get()
        else:
            return self.target_var.get()
    
    @error_handler
    def select_canvas_area(self):
        """Allow user to select the drawing canvas area"""
        self.status_var.set("Setting drawing area...")
        self.root.update_idletasks()
        
        try:
            # Minimize our window temporarily to make selection easier
            self.root.iconify()
            time.sleep(0.5)  # Give time for the window to minimize
            
            # Use the drawing area selector to get the canvas area
            canvas_area = self.drawing_area_selector.select_drawing_area()
            
            # Restore our window
            self.root.deiconify()
            
            if canvas_area:
                self.auto_draw.set_canvas_area(canvas_area)
                x1, y1, x2, y2 = canvas_area
                self.canvas_info_var.set(f"Canvas area: ({x1}, {y1}) to ({x2}, {y2})\nSize: {x2-x1}×{y2-y1}")
                self.status_var.set(self.translations["status_area_set"])
            else:
                self.status_var.set("Drawing area selection cancelled")
        except Exception as e:
            # Restore our window
            self.root.deiconify()
            messagebox.showerror(self.translations["error"], f"{self.translations['error_area']} {str(e)}")
            self.status_var.set("Drawing area setting failed")
    
    def reset_canvas_area(self):
        """Reset the drawing canvas area to default (center of screen)"""
        self.auto_draw.set_canvas_area(None)
        self.canvas_info_var.set(self.translations["not_set"])
        self.status_var.set(self.translations["status_area_reset"])
    
    @error_handler
    def set_color_positions(self):
        """Allow user to set positions for each color in the palette"""
        if not self.auto_draw.palette:
            self.use_default_palette()
        
        self.status_var.set("Setting color positions...")
        self.root.update_idletasks()
        
        try:
            # Minimize our window temporarily to make selection easier
            self.root.iconify()
            time.sleep(0.5)  # Give time for the window to minimize
            
            # Use the drawing area selector to get color positions
            color_positions = self.drawing_area_selector.select_color_positions(self.auto_draw.palette)
            
            # Restore our window
            self.root.deiconify()
            
            if color_positions:
                self.auto_draw.set_color_positions(color_positions)
                self.color_pos_info_var.set(f"Set {len(color_positions)} color positions")
                self.status_var.set(self.translations["status_colors_set"])
            else:
                self.status_var.set("Color position setting cancelled")
        except Exception as e:
            # Restore our window
            self.root.deiconify()
            messagebox.showerror(self.translations["error"], f"{self.translations['error_colors']} {str(e)}")
            self.status_var.set("Color position setting failed")
    
    def reset_color_positions(self):
        """Reset color positions"""
        self.auto_draw.set_color_positions({})
        self.color_pos_info_var.set(self.translations["not_set"])
        self.status_var.set(self.translations["status_colors_reset"])
    
    @error_handler
    def start_drawing(self):
        if not self.auto_draw.image:
            messagebox.showerror(self.translations["error"], "No image loaded")
            return
        
        # Update auto_draw settings from GUI
        self.auto_draw.style = self.style_var.get()
        self.auto_draw.resolution = self.resolution_var.get()
        self.auto_draw.speed = self.speed_var.get()
        self.auto_draw.target_app = self.get_target_app()
        
        # Make sure we have a palette
        if not self.auto_draw.palette:
            self.auto_draw.palette = self.auto_draw.get_default_palette(self.auto_draw.target_app)
        
        # Process the image
        self.status_var.set("Processing image...")
        self.root.update_idletasks()
        
        if not self.auto_draw.process_image():
            messagebox.showerror(self.translations["error"], "Failed to process image")
            self.status_var.set(self.translations["ready"])
            return
        
        # Show message before drawing
        result = messagebox.askokcancel(
            "Ready to Draw",
            "The application will now draw the image in the target application.\n\n" +
            "Please make sure the target application is open and ready.\n" +
            "Do not move the mouse or use the keyboard during drawing.\n\n" +
            "Press ESC at any time to stop drawing immediately.\n\n" +
            "Press OK to begin drawing."
        )
        
        if not result:
            self.status_var.set("Drawing cancelled")
            return
        
        # Create a countdown
        for i in range(3, 0, -1):
            self.status_var.set(f"Drawing will begin in {i} seconds...")
            self.root.update_idletasks()
            time.sleep(1)
        
        # Start drawing
        self.status_var.set("Drawing in progress... Press ESC to stop.")
        self.root.update_idletasks()
        
        if self.auto_draw.draw_image():
            if self.auto_draw.stop_drawing:
                self.status_var.set("Drawing stopped by user")
            else:
                self.status_var.set("Drawing completed successfully")
        else:
            messagebox.showerror(self.translations["error"], "Failed to draw image")
            self.status_var.set("Drawing failed")


def parse_arguments():
    parser = argparse.ArgumentParser(description="AutoDraw - Automatically draw images in target applications")
    
    parser.add_argument("image", nargs="?", help="Path to image file or URL")
    parser.add_argument("--target", "-t", default="mspaint", help="Target application (mspaint, gartic, or custom window title)")
    parser.add_argument("--style", "-s", choices=["pixel", "outline", "vector"], default="pixel", help="Drawing style")
    parser.add_argument("--resolution", "-r", type=float, default=1.0, help="Output resolution multiplier (0.5, 1, 2, 4)")
    parser.add_argument("--speed", "-p", type=float, default=0.001, help="Drawing speed (delay in seconds)")
    parser.add_argument("--palette", "-l", help="Path to palette file (JSON or CSV)")
    parser.add_argument("--nogui", action="store_true", help="Run in command-line mode (no GUI)")
    
    return parser.parse_args()


def main():
    args = parse_arguments()
    
    logger.info("AutoDraw main function started")
    logger.info(f"Command line arguments: {args}")
    
    # If no image is provided or GUI mode is not explicitly disabled, launch GUI
    if args.image is None or not args.nogui:
        try:
            logger.info("Starting in GUI mode")
            root = tk.Tk()
            
            # Set window icon (if available)
            try:
                # Try to set an icon
                icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
                if os.path.exists(icon):
                    img = ImageTk.PhotoImage(file=icon)
                    root.iconphoto(True, img)
                    logger.debug("Icon set successfully")
            except Exception as e:
                logger.debug(f"Failed to set icon: {e}")
                pass
                
            # Create and run the GUI application
            app = AutoDrawGUI(root)
            
            # If image is provided, load it
            if args.image:
                logger.info(f"Loading initial image from command line: {args.image}")
                app.load_and_preview_image(args.image)
            
            # Run the GUI
            logger.info("GUI initialized, starting mainloop")
            root.mainloop()
            logger.info("GUI mainloop terminated")
        except Exception as e:
            logger.error(f"Error in GUI mode: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.info("Falling back to CLI mode...")
            print(f"Error in GUI mode: {e}")
            print("Falling back to CLI mode...")
            run_cli_mode(args)
    else:
        logger.info("Starting in CLI mode")
        run_cli_mode(args)
    
    logger.info("AutoDraw terminated")


def run_cli_mode(args):
    """Run in command-line mode"""
    print("AutoDraw - CLI Mode")
    print("-" * 40)
    logger.info("Running in CLI mode")
    
    auto_draw = AutoDraw()
    
    # Load image
    print(f"Loading image from {args.image}...")
    logger.info(f"CLI: Loading image from {args.image}")
    if not auto_draw.load_image(args.image):
        logger.error("CLI: Failed to load image")
        print("Error: Failed to load image")
        return
    
    # Load palette
    if args.palette:
        print(f"Loading palette from {args.palette}...")
        logger.info(f"CLI: Loading palette from {args.palette}")
        if not auto_draw.load_palette(args.palette):
            logger.warning("CLI: Failed to load palette, using default")
            print("Warning: Failed to load palette, using default")
            auto_draw.palette = auto_draw.get_default_palette(args.target)
    else:
        print(f"Using default palette for {args.target}...")
        logger.info(f"CLI: Using default palette for {args.target}")
        auto_draw.palette = auto_draw.get_default_palette(args.target)
    
    # Set parameters
    auto_draw.style = args.style
    auto_draw.resolution = args.resolution
    auto_draw.speed = args.speed
    auto_draw.target_app = args.target
    logger.info(f"CLI: Parameters set - style: {args.style}, resolution: {args.resolution}, speed: {args.speed}, target: {args.target}")
    
    # Process image
    print("Processing image...")
    logger.info("CLI: Processing image")
    if not auto_draw.process_image():
        logger.error("CLI: Failed to process image")
        print("Error: Failed to process image")
        return
    
    # Confirm before drawing
    print("\nReady to draw!")
    print(f"Target application: {args.target}")
    print(f"Style: {args.style}")
    print(f"Resolution: {args.resolution}x")
    print(f"Speed: {args.speed}s")
    print("\nPress ESC at any time to stop drawing immediately.")
    logger.info("CLI: Ready to draw, waiting for user confirmation")
    
    confirmation = input("\nMake sure the target application is open and ready.\nPress Enter to begin drawing or Ctrl+C to cancel...")
    logger.info("CLI: User confirmed, starting drawing countdown")
    
    # Countdown
    for i in range(3, 0, -1):
        print(f"Drawing will begin in {i} seconds...")
        logger.info(f"CLI: Drawing countdown {i}")
        time.sleep(1)
    
    # Draw image
    print("Drawing in progress... Do not move the mouse or use the keyboard.")
    print("Press ESC to stop drawing immediately.")
    logger.info("CLI: Starting drawing process")
    if auto_draw.draw_image():
        if auto_draw.stop_drawing:
            logger.info("CLI: Drawing stopped by user")
            print("Drawing stopped by user.")
        else:
            logger.info("CLI: Drawing completed successfully")
            print("Drawing completed successfully!")
    else:
        logger.error("CLI: Drawing failed")
        print("Error: Drawing failed.")
    
    logger.info("CLI: Drawing process finished")


if __name__ == "__main__":
    main() 