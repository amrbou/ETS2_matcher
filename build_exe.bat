@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo  ETS2 Mod Synchronizer - Build EXE
echo ===================================================
echo.

:: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Installez Python 3.10+ depuis https://python.org
    pause & exit /b 1
)

:: Install dependencies
echo Installation des dependances...
pip install pycryptodome pyinstaller --quiet
if errorlevel 1 (
    echo [ERREUR] pip a echoue. Verifiez votre connexion internet.
    pause & exit /b 1
)

echo.
echo Construction de l'executable...
echo.

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "ETS2_ModSync" ^
  --clean ^
  main.py

if errorlevel 1 (
    echo.
    echo [ERREUR] La compilation a echoue. Consultez les messages ci-dessus.
    pause & exit /b 1
)

echo.
echo ===================================================
echo  Termine !  dist\ETS2_ModSync.exe est pret.
echo ===================================================
echo.
echo L'exe est autonome : aucune installation requise pour l'utilisateur final.
pause
