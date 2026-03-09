@echo off
chcp 65001 >nul
echo ============================================
echo  Starting Label Studio
echo ============================================
echo.

set APP_DIR=%~dp0..
set VENV_DIR=%APP_DIR%\venv
set ENV_FILE=%APP_DIR%\config\label-studio.env

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found at %VENV_DIR%
    echo Run install_offline.bat first
    pause
    exit /b 1
)

echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

echo Loading configuration from %ENV_FILE%...
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
        if not "%%A"=="" if not "%%A:~0,1%"=="#" (
            set "%%A=%%B"
        )
    )
) else (
    echo WARNING: Config file not found, using defaults
)

echo.
echo Label Studio URL: %LABEL_STUDIO_HOST%
echo Database: %POSTGRE_HOST%:%POSTGRE_PORT%/%POSTGRE_NAME%
echo.

mkdir "%APP_DIR%\logs" 2>nul
mkdir "%APP_DIR%\data" 2>nul

label-studio start ^
    --host 0.0.0.0 ^
    --port %LABEL_STUDIO_PORT% ^
    --database postgresql ^
    --db-name %POSTGRE_NAME% ^
    --db-user %POSTGRE_USER% ^
    --db-password %POSTGRE_PASSWORD% ^
    --db-host %POSTGRE_HOST% ^
    --db-port %POSTGRE_PORT% ^
    --log-level INFO ^
    2>&1 | tee "%APP_DIR%\logs\label-studio.log"

if errorlevel 1 (
    echo.
    echo ERROR: Label Studio failed to start
    echo Check logs at: %APP_DIR%\logs\label-studio.log
    pause
)
