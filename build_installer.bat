@echo off
title AFMI Smart Admin - Construction de l'installateur Windows
chcp 65001 > nul
setlocal
cd /d "%~dp0"
set VERSION=1.3.0

echo ===================================================================
echo   AFMI Smart Admin %VERSION% - construction de l'installateur
echo ===================================================================

echo [1/6] Tests de l'application de bureau...
dotnet test "AFMI Smart Admin.sln" --nologo -v q || goto :error

echo [2/6] Tests du backend Smart Office...
python -m pytest SmartOffice\tests -q -p no:cacheprovider || goto :error

echo [3/6] Compilation de l'interface Smart Office...
pushd SmartOffice\frontend
if not exist node_modules call npm install || (popd & goto :error)
call npm run build || (popd & goto :error)
popd

echo [4/6] Compilation du backend Smart Office (PyInstaller)...
call SmartOffice\build_backend.bat || goto :error
rem build_backend.bat changes the current directory
cd /d "%~dp0"

echo [5/6] Publication de l'application de bureau (.NET autonome)...
if exist build\app rmdir /s /q build\app
dotnet publish "Desktop\AFMI Smart Admin.csproj" -c Release -r win-x64 --self-contained true -p:Version=%VERSION% -o build\app --nologo || goto :error
xcopy /e /i /q /y "SmartOffice\build\dist\smartoffice-backend" "build\app\SmartOffice\smartoffice-backend" > nul || goto :error

echo [6/6] Création de l'installateur (Inno Setup)...
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
