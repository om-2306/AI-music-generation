@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" (
  call .venv\Scripts\activate.bat
)
python src\web_app.py
pause
