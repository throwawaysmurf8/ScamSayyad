@echo off
REM One-time setup: creates the .venv folder and installs the libraries.
cd /d "%~dp0"
python -m venv .venv || (echo Python not found. Install Python 3.12+ from python.org & pause & exit /b 1)
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
echo.
echo Setup done. Double-click run.bat to start ScamShield.
pause
