@echo off
cd /d %~dp0

if not exist .venv (
    call update.bat
)

call .venv\Scripts\activate.bat
python -m pip install -e . -q
python -m example %*
