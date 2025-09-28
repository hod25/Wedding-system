@echo off
REM First-time run (scan QR) and send pending invitations once
SETLOCAL ENABLEDELAYEDEXPANSION
if not defined BOT_API_KEY echo BOT_API_KEY not set. Set it via: set BOT_API_KEY=YOUR_KEY & pause & exit /b 1
python whatsapp_bot_remote.py send_all --limit 15
pause
