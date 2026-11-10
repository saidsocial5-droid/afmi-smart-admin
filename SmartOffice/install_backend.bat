@echo off
title AFMI Smart Admin - Installation du moteur Smart Office
chcp 65001 > nul
cd /d "%~dp0"
echo ===================================================================
echo   Installation des dependances Python du module Smart Office
echo ===================================================================
python -m pip install -r requirements.txt
pause
