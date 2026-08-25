@echo off
cd /d "%~dp0"
title WDI Visit Analytics

echo.
echo   WDI Visit Analytics Engine
echo   ==========================
echo.

echo   [1/3] Stopping any previous instance ...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*streamlit*run*app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

echo   [2/3] Clearing cached bytecode ...
if exist "__pycache__" rd /s /q "__pycache__" 2>nul

echo   [3/3] Starting the app ...
echo.
echo        This computer :  http://localhost:8501
echo        On the network:  http://YOUR-IP:8501     ( run  ipconfig  to see YOUR-IP )
echo.
echo        Close this window to stop the app.
echo.

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
) else (
    python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
)

echo.
echo   App stopped.
pause
