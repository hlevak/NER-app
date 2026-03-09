@echo off
chcp 65001 >nul
echo ============================================
echo  NER-app: Download Wheels for Offline Setup
echo ============================================
echo.

set PYTHON_VERSION=3.11
set OUTPUT_DIR=%~dp0..\wheels

if "%1"=="--python-version" (
    set PYTHON_VERSION=%2
)

echo Python version: %PYTHON_VERSION%
echo Output dir: %OUTPUT_DIR%
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python %PYTHON_VERSION% and add it to PATH
    pause
    exit /b 1
)

echo Upgrading pip...
python -m pip install --upgrade pip wheel setuptools

echo.
echo Starting download...
python "%~dp0download_wheels.py" --python-version %PYTHON_VERSION% --output-dir "%OUTPUT_DIR%"

if errorlevel 1 (
    echo.
    echo ERROR: Download failed. Check internet connection and try again.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Download complete!
echo  Transfer the 'wheels' folder to the
echo  isolated machine and run install_offline.bat
echo ============================================
pause
