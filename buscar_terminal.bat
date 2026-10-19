@echo off
title Radar de Achados - Terminal CLI
chcp 65001 >nul
cd /d "%~dp0"
cls

set PYTHON_CMD=python
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    ) else (
        if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
            set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        )
    )
)

%PYTHON_CMD% main.py

echo.
echo Pressione qualquer tecla para fechar...
pause >nul
