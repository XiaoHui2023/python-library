@echo off
cd /d "%~dp0..\.."
if not exist .venv call update.bat
call .venv\Scripts\activate.bat
set "PYTHONPATH=%CD%"
python -m examples.search %*
