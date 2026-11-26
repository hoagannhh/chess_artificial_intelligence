@echo off
setlocal
cd /d "%~dp0"
if not defined CHESS_AZ_PLAIN_MODEL set "CHESS_AZ_PLAIN_MODEL=%~dp0.local\models\alphazero\current.pt"
if not defined CHESS_AZ_TEACHER_MODEL set "CHESS_AZ_TEACHER_MODEL=%~dp0.local\models\alphazero-teacher-01\current.pt"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py %*
) else (
    py app.py %*
)
if errorlevel 1 pause
