@echo off
cd /d %~dp0

if not exist .venv (
    call update.bat
)

call .venv\Scripts\activate.bat

pip install python-dotenv
python examples/get_devices