@echo off
setlocal
chcp 65001 >nul
title Radar Tracker - Instalacao
cd /d "%~dp0"

echo ==========================================
echo   Instalacao - Rastreamento de Motoboys
echo ==========================================

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
    echo [ERRO] Python 3.10+ nao encontrado. Instale em https://www.python.org/downloads/
    echo        e marque a opcao "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist .venv (
    echo Criando ambiente virtual .venv ...
    %PY% -m venv .venv || goto :erro
)

echo Instalando dependencias ...
.venv\Scripts\python -m pip install --upgrade pip >nul
.venv\Scripts\python -m pip install -r requirements.txt || goto :erro

if not exist .env copy .env.example .env >nul
if not exist config\motoboys.json copy config\motoboys.example.json config\motoboys.json >nul

.venv\Scripts\python scripts\seed_demo.py

echo.
echo [OK] Instalacao concluida. Execute iniciar.bat para abrir o sistema.
pause
exit /b 0

:erro
echo [ERRO] Falha na instalacao. Verifique a mensagem acima.
pause
exit /b 1
