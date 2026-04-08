@echo off
cd /d %~dp0

if not exist .venv (
    call update.bat
)

call .venv\Scripts\activate.bat

python examples/simple