@echo off
title AFMI-SmartOffice (Navigateur Web)
chcp 65001 > nul
cd /d "%~dp0"
echo ===================================================================
echo   🌲 AFMI-SmartOffice - المكتب الذكي للجمعية (إفران - أزرو)
echo   Lancement du serveur Web et ouverture du navigateur...
echo ===================================================================
python run_app.py --web-only
pause
