@echo off
REM Starts the ScamShield dashboard and opens it in your browser (http://localhost:8501).
REM Close this window to stop the dashboard.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Run setup.bat first. & pause & exit /b 1)
REM Open the browser a few seconds from now, once the server is up.
start "" /b cmd /c "timeout /t 4 /nobreak >nul & start http://localhost:8501"
REM --server.address localhost: only this computer can open the dashboard (no login on it).
.venv\Scripts\python -m streamlit run app.py --server.address localhost
