@echo off
setlocal
chcp 65001 >nul
title Radar Tracker - Tunel ngrok
cd /d "%~dp0..\.."

rem Le NGROK_DOMAIN e PORT do arquivo .env
for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
if not defined PORT set "PORT=5000"

set "NGROK=ngrok"
if exist tools\ngrok.exe set "NGROK=tools\ngrok.exe"

if defined NGROK_DOMAIN (
    echo Publicando http://localhost:%PORT% em https://%NGROK_DOMAIN%
    "%NGROK%" http --domain=%NGROK_DOMAIN% %PORT%
) else (
    echo NGROK_DOMAIN nao definido no .env - usando endereco temporario.
    "%NGROK%" http %PORT%
)
pause
