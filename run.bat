@echo off
REM Ajan OCR Annotation Tool - Run Script for Windows
REM Quick launcher for the application

REM Check if virtual environment exists
if not exist "venv" (
    echo [ERROR] Virtual environment not found!
    echo Please run install.bat first
    pause
    exit /b 1
)

REM Activate virtual environment and run
echo [INFO] Starting Ajan OCR Annotation Tool...
call venv\Scripts\activate.bat
python main.py

REM Deactivate when done
call venv\Scripts\deactivate.bat 2>nul
