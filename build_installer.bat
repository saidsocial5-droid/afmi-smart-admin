@echo off
title AFMI Smart Admin - Construction de l'installateur Windows
chcp 65001 > nul
setlocal
cd /d "%~dp0"
set VERSION=2.3.3

echo ===================================================================
echo   AFMI Smart Admin %VERSION% - construction de l'installateur
echo ===================================================================

echo [0/8] Composants tiers (Tesseract fra/ara, police Amiri)...
powershell -NoProfile -ExecutionPolicy Bypass -File installer\prepare_third_party.ps1 || goto :error

echo [1/8] Tests de l'application de bureau...
dotnet test "AFMI Smart Admin.sln" --nologo -v q || goto :error

echo [2/8] Tests du backend Smart Office...
python -m pip install --quiet -r SmartOffice\requirements.txt pytest || goto :error
rem Tests de lecture des relevés avec le Tesseract qui sera livré
set "AFMI_TESSERACT=%~dp0third_party\tesseract\tesseract.exe"
pushd SmartOffice
python -m pytest tests -q -p no:cacheprovider || (popd & goto :error)
popd

echo [3/8] Compilation de l'interface Smart Office...
pushd SmartOffice\frontend
if not exist node_modules call npm install || (popd & goto :error)
call npm run build || (popd & goto :error)
popd

echo [4/8] Compilation du backend Smart Office (PyInstaller)...
call SmartOffice\build_backend.bat || goto :error
rem build_backend.bat changes the current directory
cd /d "%~dp0"

echo [5/8] Publication de l'application de bureau (.NET autonome)...
if exist build\app rmdir /s /q build\app
dotnet publish "Desktop\AFMI Smart Admin.csproj" -c Release -r win-x64 --self-contained true -p:Version=%VERSION% -o build\app --nologo || goto :error
xcopy /e /i /q /y "SmartOffice\build\dist\smartoffice-backend" "build\app\SmartOffice\smartoffice-backend" > nul || goto :error
rem Tesseract embarqué : trouvé par le backend dans son dossier (backend/tools/statements/ocr.py)
xcopy /e /i /q /y "third_party\tesseract" "build\app\SmartOffice\smartoffice-backend\tesseract" > nul || goto :error

echo [6/8] Base de démonstration (association fictive, construite par le pipeline réel)...
pushd SmartOffice
python -m demo.build_demo "..\build\app\demo" || (popd & goto :error)
popd

python docs\v2\captures\guide_html.py "build\app\docs\GUIDE_UTILISATEUR.html" || goto :error

echo [7/8] Contrôle du contenu...
if not exist "build\app\demo\database.db" goto :error
if not exist "build\app\SmartOffice\smartoffice-backend\tesseract\tessdata\ara.traineddata" goto :error

echo [8/8] Création de l'installateur (Inno Setup)...
set ISCC=
for %%P in ("%ProgramFiles%\Inno Setup 7\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe") do if exist %%P set ISCC=%%P
if not defined ISCC (
    echo [!] Inno Setup introuvable. Installez-le depuis https://jrsoftware.org/isinfo.php
    goto :error
)
%ISCC% /Q /DAppVersion=%VERSION% installer\AFMI_Smart_Admin.iss || goto :error

echo.
echo [OK] Installateur : build\installer\AFMI_Smart_Admin_Setup_%VERSION%.exe
exit /b 0

:error
echo.
echo [ECHEC] La construction s'est arrêtée sur une erreur (voir ci-dessus).
exit /b 1
