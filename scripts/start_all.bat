@echo off
chcp 65001 >nul
echo ============================================
echo  NER-app: Starting All Services
echo ============================================
echo.

set APP_DIR=%~dp0..

echo Checking virtual environment...
if not exist "%APP_DIR%\venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Run install_offline.bat first
    pause
    exit /b 1
)

echo Starting ML Backend in a new window...
start "NER ML Backend" cmd /k "%~dp0start_ml_backend.bat"

echo Waiting 10 seconds for ML Backend to initialize...
timeout /t 10 /nobreak

echo Starting Label Studio in a new window...
start "Label Studio" cmd /k "%~dp0start_label_studio.bat"

echo.
echo ============================================
echo  All services started!
echo.
echo  Label Studio:  http://localhost:8080
echo  ML Backend:    http://localhost:9090
echo.
echo  Log files are in: %APP_DIR%\logs\
echo.
echo  To stop services: close the service windows
echo  or use Task Manager to end the processes
echo ============================================
echo.
pause
