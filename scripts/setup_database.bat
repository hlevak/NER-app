@echo off
chcp 65001 >nul
echo ============================================
echo  NER-app: PostgreSQL Database Setup
echo ============================================
echo.

set APP_DIR=%~dp0..
set PGBIN=C:\Program Files\PostgreSQL\15\bin
set PGDATA=C:\Program Files\PostgreSQL\15\data
set PGHOST=localhost
set PGPORT=5432
set PGUSER=postgres

REM Try to find PostgreSQL bin directory
if not exist "%PGBIN%\psql.exe" (
    echo Searching for PostgreSQL installation...
    for /d %%D in ("C:\Program Files\PostgreSQL\*") do (
        if exist "%%D\bin\psql.exe" (
            set PGBIN=%%D\bin
            echo Found PostgreSQL at: %%D
            goto :found_pg
        )
    )
    echo ERROR: PostgreSQL not found.
    echo Please install PostgreSQL 15+ from https://www.postgresql.org/download/windows/
    echo Or set PGBIN variable to your PostgreSQL bin directory.
    pause
    exit /b 1
)
:found_pg

echo PostgreSQL bin: %PGBIN%
echo.

REM Check if PostgreSQL service is running
sc query postgresql-x64-15 >nul 2>&1
if errorlevel 1 (
    echo Starting PostgreSQL service...
    net start postgresql-x64-15 >nul 2>&1
    if errorlevel 1 (
        echo Trying to start postgresql service...
        net start postgresql >nul 2>&1
    )
    timeout /t 3 /nobreak >nul
)

echo Checking PostgreSQL connection...
"%PGBIN%\psql.exe" -U %PGUSER% -h %PGHOST% -p %PGPORT% -c "SELECT version();" postgres
if errorlevel 1 (
    echo ERROR: Cannot connect to PostgreSQL.
    echo Make sure:
    echo   1. PostgreSQL service is running
    echo   2. pg_hba.conf allows local connections
    echo   3. The postgres user password is configured
    pause
    exit /b 1
)

echo.
echo Running database initialization script...
"%PGBIN%\psql.exe" -U %PGUSER% -h %PGHOST% -p %PGPORT% -f "%APP_DIR%\config\postgresql-init.sql" postgres

if errorlevel 1 (
    echo WARNING: Some SQL commands may have failed (this is OK if database already exists)
)

echo.
echo Verifying database setup...
"%PGBIN%\psql.exe" -U label_studio_user -h %PGHOST% -p %PGPORT% -d label_studio -c "SELECT current_database(), current_user, version();"

if errorlevel 1 (
    echo ERROR: Database verification failed.
    echo Check the SQL output above for errors.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Database setup complete!
echo.
echo  Connection details:
echo    Host: %PGHOST%:%PGPORT%
echo    Database: label_studio
echo    User: label_studio_user
echo    Password: LabelStudio2024!
echo.
echo  IMPORTANT: Change the password in production!
echo  Edit: config\label-studio.env
echo        config\postgresql-init.sql
echo ============================================
pause
