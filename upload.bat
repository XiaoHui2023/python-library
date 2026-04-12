@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=py"

%PYTHON% "%ROOT%upload.py" %*
exit /b %ERRORLEVEL%