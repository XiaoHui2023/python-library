@echo off
cd /d %~dp0

py-auto-deps.exe "packages" --cache ".git/auto_deps"