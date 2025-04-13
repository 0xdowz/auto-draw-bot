@echo off
echo =======================================
echo  تشغيل برنامج الرسم التلقائي
echo =======================================
echo.
echo سيتم تشغيل البرنامج مع تخطي اللون الأبيض لتسريع عملية الرسم
echo.

python auto_draw_cli.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo فشل تشغيل البرنامج. تأكد من تثبيت Python وجميع المكتبات المطلوبة:
    echo pip install pillow pyautogui numpy keyboard
    echo.
)

echo.
echo اضغط أي مفتاح للخروج...
pause > nul 