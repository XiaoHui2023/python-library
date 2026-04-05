@echo off
cd /d %~dp0

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py"