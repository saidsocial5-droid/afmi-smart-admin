@echo off
title AFMI GESTION - COMPILATION ET PACKAGING EXECUTABLE
echo ======================================================================
echo             AFMI GESTION - COMPILATION EXECUTABLE AUTONOME
echo ======================================================================
echo.
echo Ce script va generer un fichier unique executable autonome (.exe)
echo pour Windows x64. L'application contiendra son propre runtime .NET 10
echo et pourra s'executer sur n'importe quelle machine Windows 10 ou 11
echo sans aucun pre-requis d'installation.
echo.
echo En cours de compilation...
echo.

:: Execute dotnet publish with single-file and ready-to-run optimizations
dotnet publish "AFMI Smart Admin.csproj" -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:PublishReadyToRun=true -o "publish"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ======================================================================
    echo COMPILATION REUSSIE AVEC SUCCES !
    echo ======================================================================
    echo.
    echo Le fichier unique executable a ete genere dans le dossier :
    echo   %~dp0publish\AFMI Smart Admin.exe
    echo.
    echo Pour distribuer l'application :
    echo   1. Vous pouvez copier directement le fichier "AFMI Smart Admin.exe"
    echo      sur n'importe quelle machine Windows 10 ou 11 64 bits.
    echo   2. Optionnel : Pour generer un installeur Windows officiel ^(.exe/.msi^),
    echo      vous pouvez utiliser l'utilitaire gratuit "Inno Setup" ou "WiX Toolset"
    echo      en ciblant le fichier "publish\AFMI Smart Admin.exe".
    echo.
) else (
    echo.
    echo ======================================================================
    echo ECHEC DE LA COMPILATION. VEUILLEZ VERIFIER LES ERREURS CI-DESSUS.
    echo ======================================================================
    echo.
)

pause
