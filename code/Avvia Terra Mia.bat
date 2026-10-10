@echo off
chcp 65001 >nul
title Terra Mia – Gestione Sito Web

:: Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRORE: Python non trovato.
    echo Scaricalo da https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Installa dipendenze se non presenti
python -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo Installazione Pillow in corso...
    pip install Pillow --quiet
)

python -c "import git" >nul 2>&1
if errorlevel 1 (
    echo Installazione gitpython in corso...
    pip install gitpython --quiet
)

:: Avvia lo strumento
echo Avvio Terra Mia...
python "%~dp0terra_mia_tool.py"

if errorlevel 1 (
    echo.
    echo Si e verificato un errore. Premi un tasto per chiudere.
    pause >nul
)
