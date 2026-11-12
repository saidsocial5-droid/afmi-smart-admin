@echo off
title AFMI Smart Admin - Compilation du backend Smart Office
chcp 65001 > nul
cd /d "%~dp0"
echo ===================================================================
echo   Compilation du backend Python en executable autonome (PyInstaller)
echo ===================================================================

python -m pip install --quiet -r requirements.txt pyinstaller || goto :error

if not exist "frontend\dist\index.html" (
    echo [!] frontend\dist introuvable : executez "npm install" puis "npm run build" dans SmartOffice\frontend.
    goto :error
)

python -m PyInstaller --noconfirm --clean --console ^
    --name smartoffice-backend ^
    --distpath "%~dp0build\dist" --workpath "%~dp0build\work" --specpath "%~dp0build" ^
    --collect-submodules backend ^
    --collect-submodules uvicorn ^
    --collect-all pdfplumber ^
    --collect-all pymupdf ^
    --hidden-import multipart ^
    --collect-data docx ^
    --collect-all cv2 ^
    --add-data "%~dp0backend\config\*.json;backend\config" ^
    --collect-submodules lxml ^
    --add-data "%~dp0backend\plugins;backend\plugins" ^
    --add-data "%~dp0frontend\dist;frontend\dist" ^
    "%~dp0server.py" || goto :error

echo.
echo [OK] Backend compile : build\dist\smartoffice-backend\smartoffice-backend.exe
exit /b 0

:error
echo [ECHEC] La compilation du backend a echoue.
exit /b 1
