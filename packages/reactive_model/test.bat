@echo off
cd /d %~dp0

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -e .
python -m unittest discover -s tests -p "test*.py" -v