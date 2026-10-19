@echo off
title Radar de Achados - OLX e Facebook Marketplace
chcp 65001 >nul
cd /d "%~dp0"
cls

echo ============================================================
echo   RADAR DE ACHADOS - OLX E FACEBOOK MARKETPLACE
echo ============================================================
echo.

:: Detectar executavel Python
set PYTHON_CMD=python
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    ) else (
        if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
            set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        ) else (
            echo [ERRO] Python nao foi encontrado no sistema!
            echo Certifique-se de que o Python esta instalado.
            pause
            exit /b 1
        )
    )
)

:: Garantir que a porta 8000 esteja livre antes de iniciar
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Usando: %PYTHON_CMD%
echo.
echo ============================================================
echo   Servidor pronto!
echo   Acesse no seu navegador: http://localhost:8000
echo   Para encerrar, pressione Ctrl + C nesta janela.
echo ============================================================
echo.

%PYTHON_CMD% app.py

if %errorlevel% neq 0 (
    echo.
    echo [AVISO] O servidor foi encerrado ou encontrou um erro.
)

pause
