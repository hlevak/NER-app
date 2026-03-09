@echo off
chcp 65001 >nul
echo ============================================
echo  Starting NER ML Backend
echo ============================================
echo.

set APP_DIR=%~dp0..
set VENV_DIR=%APP_DIR%\venv
set ENV_FILE=%APP_DIR%\config\ml-backend.env

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found at %VENV_DIR%
    echo Run install_offline.bat first
    pause
    exit /b 1
)

echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

echo Loading configuration...
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
        if not "%%A"=="" if not "%%A:~0,1%"=="#" (
            set "%%A=%%B"
        )
    )
)

set ML_BACKEND_HOST=0.0.0.0
if "%ML_BACKEND_PORT%"=="" set ML_BACKEND_PORT=9090

mkdir "%APP_DIR%\logs" 2>nul
mkdir "%APP_DIR%\models\fine_tuned" 2>nul

echo.
echo ML Backend starting on http://%ML_BACKEND_HOST%:%ML_BACKEND_PORT%
echo spaCy model: %SPACY_MODEL%
echo Logs dir: %LOGS_DIR%
echo.

cd /d "%APP_DIR%"

python -m ml_backend.wsgi 2>&1 | tee "%APP_DIR%\logs\ml-backend.log"

if errorlevel 1 (
    echo.
    echo ERROR: ML Backend failed to start
    echo Check logs at: %APP_DIR%\logs\ml-backend.log
    pause
)
