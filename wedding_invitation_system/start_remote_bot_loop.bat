@echo off
REM Continuous loop every 15 minutes
SETLOCAL ENABLEDELAYEDEXPANSION
if not defined BOT_API_KEY echo BOT_API_KEY not set. Set it via: set BOT_API_KEY=YOUR_KEY & pause & exit /b 1
python whatsapp_bot_remote.py loop --interval 900 --limit 20 --headless
