@echo off
cd /d %~dp0

if not exist .venv (
    call update.bat
)

call .venv\Scripts\activate.bat
python -m pip install -e . -q
python -m example.ensure_browser --proxy 127.0.0.1:7897
python -m example -c all -n 2 --proxy 127.0.0.1:7897 %*
