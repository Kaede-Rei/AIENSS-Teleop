@echo off
setlocal EnableExtensions

cd /d "%~dp0"
set "ROOT_DIR=%CD%"
set "VENV_PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe"
set "TELEOP_SCRIPT=%ROOT_DIR%\scripts\teleop.py"

if not exist "%VENV_PYTHON%" (
    echo [AIENSS-Teleop] Local virtual environment not found.
    echo Run install.bat first.
    exit /b 1
)

if not exist "%TELEOP_SCRIPT%" (
    echo [AIENSS-Teleop] Teleoperation script not found: "%TELEOP_SCRIPT%"
    exit /b 1
)

"%VENV_PYTHON%" "%TELEOP_SCRIPT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
exit /b %EXIT_CODE%
