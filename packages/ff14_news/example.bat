@echo off
cd /d %~dp0

if not exist .venv (
    call update.bat
)

call .venv\Scripts\activate.bat
python -m pip install -e ".[example]" -q
python -m example.ensure_browser
python -m example -n 5 %*
