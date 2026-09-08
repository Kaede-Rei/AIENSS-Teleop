@echo off
setlocal EnableExtensions

cd /d "%~dp0"
set "ROOT_DIR=%CD%"
set "VENV_PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe"
set "RESET_SCRIPT=%ROOT_DIR%\scripts\reset.py"

if not exist "%VENV_PYTHON%" (
    echo [AIENSS-Teleop] Local virtual environment not found
    echo Run install.bat first
    exit /b 1
)

"%VENV_PYTHON%" "%RESET_SCRIPT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
exit /b %EXIT_CODE%
