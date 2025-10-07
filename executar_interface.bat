@echo off
title Sistema de Automacao de Sinistros AON - Interface Grafica
echo.
echo =====================================================================
echo    SISTEMA DE AUTOMACAO DE SINISTROS AON - V2.0
echo    Interface Grafica Desktop
echo =====================================================================
echo.
echo [INFO] Iniciando interface grafica...
echo.

REM Verificar se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale o Python 3.8+ e tente novamente.
    pause
    exit /b 1
)

REM Executar interface grafica
echo [INFO] Carregando interface...
python gui_launcher.py

REM Se chegou aqui, a interface foi fechada
echo.
echo [INFO] Interface fechada.
echo.
pause