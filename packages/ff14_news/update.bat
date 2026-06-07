@echo off
cd /d %~dp0

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install -e .
python -m example.ensure_browser --proxy 127.0.0.1:7897
