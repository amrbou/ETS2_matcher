@echo off
cd /d "%~dp0"
pip install pycryptodome --quiet
python main.py
if errorlevel 1 (
    echo.
    echo ERREUR : Python 3.10+ requis. Installez-le depuis python.org
    pause
)
