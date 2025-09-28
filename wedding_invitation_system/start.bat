@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo 🎉 מערכת ניהול הזמנות חתונה
echo ================================
echo.

:menu
echo בחר אפשרות:
echo 1. הפעל את האתר
echo 2. שלח הזמנות לכל האורחים
echo 3. שלח תזכורות
echo 4. יצר רשימת קישורים
echo 5. יציאה
echo.
set /p choice="הבחירה שלך (1-5): "

if "%choice%"=="1" goto start_website
if "%choice%"=="2" goto send_invitations
if "%choice%"=="3" goto send_reminders
if "%choice%"=="4" goto generate_links
if "%choice%"=="5" goto exit
goto menu

:start_website
echo.
echo 🌐 מפעיל את האתר...
echo האתר יהיה זמין בכתובת: http://localhost:5000
echo לעצירה לחץ Ctrl+C
echo.
C:/Users/hod71/AppData/Local/Programs/Python/Python313/python.exe app.py
pause
goto menu

:send_invitations
echo.
echo 📱 מפעיל בוט שליחת הזמנות...
echo ודא שיש לך ווצאפ פעיל בטלפון!
echo.
pause
C:/Users/hod71/AppData/Local/Programs/Python/Python313/python.exe whatsapp_bot.py send_all
pause
goto menu

:send_reminders
echo.
echo 🔔 מפעיל בוט שליחת תזכורות...
echo.
pause
C:/Users/hod71/AppData/Local/Programs/Python/Python313/python.exe whatsapp_bot.py send_reminders
pause
goto menu

:generate_links
echo.
echo 🔗 יוצר רשימת קישורים...
echo.
C:/Users/hod71/AppData/Local/Programs/Python/Python313/python.exe get_links.py
pause
goto menu

:exit
echo.
echo 👋 ביי! בהצלחה עם החתונה!
echo.
pause
exit