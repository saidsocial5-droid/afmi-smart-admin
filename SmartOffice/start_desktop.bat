@echo off
title AFMI-SmartOffice (Bureau Electron)
chcp 65001 > nul
cd /d "%~dp0"
echo ===================================================================
echo   🌲 AFMI-SmartOffice - المكتب الذكي للجمعية (إفران - أزرو)
echo   Lancement de l'application de bureau Electron...
echo ===================================================================
python run_app.py
pause
