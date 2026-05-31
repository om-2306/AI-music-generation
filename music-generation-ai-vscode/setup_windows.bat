@echo off
cd /d "%~dp0"
python -c "import sys; raise SystemExit(0 if sys.version_info < (3,13) else 1)"
if errorlevel 1 (
  echo.
  echo Your current Python is too new for TensorFlow.
  echo Please install Python 3.11 or 3.12, then run:
  echo.
  echo   py -3.11 -m venv .venv
  echo   .\.venv\Scripts\activate
  echo   pip install -r requirements.txt
  echo   python src\web_app.py
  echo.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Setup complete.
pause
