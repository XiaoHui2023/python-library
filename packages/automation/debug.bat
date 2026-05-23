@echo off
cd /d "%~dp0"

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat

rem Parent of this folder is python_library\packages
for %%I in ("%~dp0..") do set "PKG_ROOT=%%~fI"

python -m pip install -U pip
python -m pip install -e "%PKG_ROOT%\reactive_model" -e "%PKG_ROOT%\tree_model" -e "%PKG_ROOT%\registry" -e "%PKG_ROOT%\observer" -e "%PKG_ROOT%\express_evaluator" -e .
