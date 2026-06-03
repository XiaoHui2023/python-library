@echo off
cd /d %~dp0

if "%~1"=="" (
  echo Usage: run.bat examples/xxx
  echo   PowerShell: .\run.bat examples/xxx  或  cmd /c run.bat examples/xxx
  exit /b 1
)

if not exist .venv (
  call update.bat
  if errorlevel 1 exit /b 1
)

call .venv\Scripts\activate.bat
set "PYTHONPATH=%~dp0"

set "MOD=%~1"
set "MOD=%MOD:/=.%
set "MOD=%MOD:\=.%
:strip_mod_dot
if not "%MOD:~0,1%"=="." goto mod_ready
set "MOD=%MOD:~1%"
goto strip_mod_dot
:mod_ready
shift
python -m %MOD% %*
exit /b %ERRORLEVEL%
