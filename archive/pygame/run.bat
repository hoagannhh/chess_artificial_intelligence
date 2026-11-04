@echo off
cd /d "%~dp0..\.."
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" archive/pygame/main.py
) else (
    py archive/pygame/main.py
)
if errorlevel 1 pause
