@echo off
setlocal EnableExtensions

cd /d "%~dp0"
set "ROOT_DIR=%CD%"
set "VENV_DIR=%ROOT_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

echo [AIENSS-Teleop] Windows installer

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [AIENSS-Teleop] Python was not found.
        echo Install Python 3.10 or newer from https://www.python.org/downloads/windows/
        echo During installation, enable "Add Python to PATH" or install the Python Launcher.
        exit /b 1
    )
    set "PYTHON_CMD=python"
)

%PYTHON_CMD% -c "import sys; print('[AIENSS-Teleop] Python', sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo [AIENSS-Teleop] Python 3.10 or newer is required.
    exit /b 1
)

set "RECREATE_VENV=0"
if exist "%VENV_PYTHON%" (
    rem A failed pip self-upgrade on Windows may leave ~ip* directories.
    if exist "%VENV_DIR%\Lib\site-packages\~ip*" set "RECREATE_VENV=1"
    "%VENV_PYTHON%" -m pip --version >nul 2>nul
    if errorlevel 1 set "RECREATE_VENV=1"
)

if "%RECREATE_VENV%"=="1" (
    echo [AIENSS-Teleop] Existing .venv has an invalid pip state. Recreating it...
    rmdir /s /q "%VENV_DIR%"
    if exist "%VENV_DIR%" (
        echo [AIENSS-Teleop] Failed to remove the old .venv.
        echo Close terminals or programs using files under .venv and run install.bat again.
        exit /b 1
    )
)

if not exist "%VENV_PYTHON%" (
    echo [AIENSS-Teleop] Creating virtual environment: .venv
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [AIENSS-Teleop] Failed to create .venv.
        exit /b 1
    )
)

if not exist "%VENV_PYTHON%" (
    echo [AIENSS-Teleop] Virtual environment Python not found: "%VENV_PYTHON%"
    exit /b 1
)

echo [AIENSS-Teleop] Checking pip...
"%VENV_PYTHON%" -m pip --version
if errorlevel 1 (
    echo [AIENSS-Teleop] pip is unavailable. Trying ensurepip...
    "%VENV_PYTHON%" -m ensurepip
    if errorlevel 1 (
        echo [AIENSS-Teleop] Failed to initialize pip.
        exit /b 1
    )
    "%VENV_PYTHON%" -m pip --version
    if errorlevel 1 exit /b 1
)

rem Do NOT upgrade pip here. On Windows, self-upgrading pip can hit WinError 32
rem because pip may attempt to replace files currently in use by its own process.
echo [AIENSS-Teleop] Installing project and runtime dependencies...
"%VENV_PYTHON%" -m pip install -e .
if errorlevel 1 (
    echo [AIENSS-Teleop] Installation failed.
    exit /b 1
)

echo.
echo [AIENSS-Teleop] Installation complete.
echo.
echo Next:
echo   1. Edit config\arm.yaml and set robot.port / teleop.port to the correct COM ports.
echo   2. Optional read-only checks:
echo        .venv\Scripts\python.exe scripts\leader_test.py
echo        .venv\Scripts\python.exe scripts\follower_test.py
echo   3. Start teleoperation:
echo        launch.bat

echo.
exit /b 0
