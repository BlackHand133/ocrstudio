@echo off
REM Ajan OCR Annotation Tool - Installation Script for Windows
REM This script automates the installation process

setlocal enabledelayedexpansion

echo.
echo ===============================================================
echo   Ajan OCR Annotation Tool - Installation Script
echo   Version 3.0.0
echo ===============================================================
echo.

REM Check if Python is installed
echo [INFO] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo [ERROR] Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [SUCCESS] Python %PYTHON_VERSION% detected

REM Check if virtual environment exists
if exist "venv" (
    echo [WARNING] Virtual environment already exists.
    choice /C YN /M "Do you want to recreate it"
    if errorlevel 2 (
        echo [INFO] Using existing virtual environment...
    ) else (
        echo [INFO] Removing existing virtual environment...
        rmdir /s /q venv
        goto create_venv
    )
    goto activate_venv
)

:create_venv
echo [INFO] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
echo [SUCCESS] Virtual environment created

:activate_venv
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [WARNING] Failed to upgrade pip, but continuing...
)

REM Install dependencies
echo [INFO] Installing dependencies from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM Ask about GPU support
echo.
choice /C YN /M "Do you want to install GPU support (CUDA required)"
if errorlevel 2 (
    echo [INFO] Skipping GPU support installation
) else (
    echo [INFO] Installing PaddlePaddle GPU version...
    pip uninstall -y paddlepaddle
    pip install paddlepaddle-gpu
    if errorlevel 1 (
        echo [WARNING] Failed to install GPU version. CPU version will be used.
    ) else (
        echo [SUCCESS] GPU support installed
    )
)

REM Install package in development mode
echo [INFO] Installing package in development mode...
pip install -e .
if errorlevel 1 (
    echo [WARNING] Failed to install package in development mode.
    echo [WARNING] You can still run the application with: python main.py
)

REM Create necessary directories
echo [INFO] Creating necessary directories...
if not exist "data\workspaces" mkdir "data\workspaces"
if not exist "output_det" mkdir "output_det"
if not exist "output_rec" mkdir "output_rec"
if not exist "logs" mkdir "logs"
if not exist "models" mkdir "models"
echo [SUCCESS] Directories created

REM Installation complete
echo.
echo ===============================================================
echo   Installation Complete!
echo ===============================================================
echo.
echo To run the application:
echo   1. Activate virtual environment: venv\Scripts\activate.bat
echo   2. Run: python main.py
echo      OR: run.bat
echo.
echo For more information, see README.md
echo.

REM Deactivate virtual environment
call venv\Scripts\deactivate.bat 2>nul

pause
