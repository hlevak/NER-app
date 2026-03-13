@echo off
chcp 65001 >nul
echo ============================================
echo  NER-app: Setup Script
echo ============================================
echo.

set APP_DIR=%~dp0..
set VENV_DIR=%APP_DIR%\venv

echo App directory: %APP_DIR%
echo.

:: Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

echo Creating virtual environment...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    python -m venv "%VENV_DIR%"
    echo Virtual environment created at %VENV_DIR%
) else (
    echo Virtual environment already exists at %VENV_DIR%
)

echo.
echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

echo Upgrading pip...
pip install --upgrade pip

echo.
echo Installing dependencies...
pip install -r "%APP_DIR%\requirements.txt"

echo.
echo Creating necessary directories...
mkdir "%APP_DIR%\logs" 2>nul
mkdir "%APP_DIR%\data" 2>nul
mkdir "%APP_DIR%\models\fine_tuned" 2>nul
mkdir "%APP_DIR%\wheels" 2>nul

echo.
echo ============================================
echo  Setup complete!
echo.
echo  Next steps:
echo  1. Configure database in config\label-studio.env
echo  2. Configure ML backend in config\ml-backend.env
echo  3. Run: scripts\start_all.bat
echo.
echo  Or start services separately:
echo   - scripts\start_ml_backend.bat
echo   - scripts\start_label_studio.bat
echo ============================================
pause
