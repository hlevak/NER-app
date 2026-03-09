@echo off
chcp 65001 >nul
echo ============================================
echo  NER-app: Offline Installation
echo ============================================
echo.

set APP_DIR=%~dp0..
set WHEELS_DIR=%APP_DIR%\wheels
set VENV_DIR=%APP_DIR%\venv

if not exist "%WHEELS_DIR%" (
    echo ERROR: Wheels directory not found: %WHEELS_DIR%
    echo Please copy the 'wheels' folder from the download machine first.
    pause
    exit /b 1
)

echo Step 1: Creating Python virtual environment...
python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    echo Make sure Python 3.10 or 3.11 is installed
    pause
    exit /b 1
)

echo Step 2: Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

echo Step 3: Upgrading pip from local wheels...
python -m pip install --upgrade pip --no-index --find-links="%WHEELS_DIR%"

echo Step 4: Installing all packages from local wheels...
python -m pip install ^
    spacy==3.7.2 ^
    flask==3.0.3 ^
    flask-cors==4.0.1 ^
    gunicorn==21.2.0 ^
    label-studio-ml==1.0.9 ^
    label-studio==1.22.0 ^
    psycopg2-binary==2.9.9 ^
    sqlalchemy==2.0.31 ^
    requests==2.31.0 ^
    python-dotenv==1.0.1 ^
    pydantic==2.7.4 ^
    thinc==8.2.4 ^
    cymem==2.0.8 ^
    preshed==3.0.9 ^
    murmurhash==1.0.10 ^
    blis==0.7.11 ^
    srsly==2.4.8 ^
    catalogue==2.0.10 ^
    weasel==0.3.4 ^
    confection==0.1.4 ^
    typer==0.9.4 ^
    wasabi==1.1.3 ^
    smart-open==7.0.4 ^
    --no-index --find-links="%WHEELS_DIR%"

if errorlevel 1 (
    echo ERROR: Package installation failed
    echo Check that all required wheel files are present in %WHEELS_DIR%
    pause
    exit /b 1
)

echo Step 5: Installing spaCy Russian model...
set SM_WHEEL=%WHEELS_DIR%\ru_core_news_sm-3.7.0-py3-none-any.whl
if exist "%SM_WHEEL%" (
    pip install "%SM_WHEEL%" --no-index --find-links="%WHEELS_DIR%"
    echo ru_core_news_sm installed
) else (
    echo WARNING: ru_core_news_sm wheel not found at %SM_WHEEL%
    echo Download it manually from:
    echo https://github.com/explosion/spacy-models/releases/download/ru_core_news_sm-3.7.0/ru_core_news_sm-3.7.0-py3-none-any.whl
)

set LG_WHEEL=%WHEELS_DIR%\ru_core_news_lg-3.7.0-py3-none-any.whl
if exist "%LG_WHEEL%" (
    pip install "%LG_WHEEL%" --no-index --find-links="%WHEELS_DIR%"
    echo ru_core_news_lg installed
)

echo Step 6: Creating required directories...
mkdir "%APP_DIR%\logs" 2>nul
mkdir "%APP_DIR%\models\fine_tuned" 2>nul
mkdir "%APP_DIR%\data" 2>nul

echo Step 7: Verifying installation...
python -c "import spacy; print('spaCy:', spacy.__version__)"
python -c "import flask; print('Flask:', flask.__version__)"
python -c "import label_studio_ml; print('label-studio-ml: OK')"
python -c "import psycopg2; print('psycopg2: OK')"

echo.
echo ============================================
echo  Installation complete!
echo.
echo  Next steps:
echo  1. Set up PostgreSQL (run setup_database.bat)
echo  2. Edit config\label-studio.env and config\ml-backend.env
echo  3. Start services with start_all.bat
echo ============================================
pause
