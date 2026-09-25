@echo off
setlocal
chcp 65001 >nul
title Radar Tracker - Servidor
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo Ambiente nao instalado. Executando instalar.bat primeiro...
    call instalar.bat || exit /b 1
)

echo Iniciando o servidor (feche esta janela para encerrar)...
.venv\Scripts\python run.py %*
pause
