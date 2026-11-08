@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First, complete the one-time setup in README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run visual_app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
if errorlevel 1 pause
