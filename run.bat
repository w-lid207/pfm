@echo off
title Collecte Agadir - Serveur
chcp 65001 >nul 2>&1

echo ========================================================
echo   Systeme de Collecte Agadir - Lancement
echo ========================================================
echo.

cd /d "%~dp0"

REM ── Environnement virtuel ──
if exist ".venv\Scripts\activate.bat" (
    echo [1/3] Activation de l environnement virtuel...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [1/3] Activation de l environnement virtuel...
    call venv\Scripts\activate.bat
) else (
    echo [!] Aucun environnement virtuel trouve.
    echo     Creation en cours...
    python -m venv .venv
    call .venv\Scripts\activate.bat
)

REM ── Installation des dependances ──
echo [2/3] Verification des dependances...
pip install -r requirements.txt --quiet 2>nul

REM ── Lancement ──
echo [3/3] Demarrage du serveur sur le port 5050...
echo.
echo ========================================================
echo   URL  : http://localhost:5050
echo   Login: admin / admin123
echo   Tests: http://localhost:5050/tests
echo   Ctrl+C pour arreter
echo ========================================================
echo.

python -m webapp.app

echo.
echo Serveur arrete.
pause
