@echo off
title AFMI Smart Admin
chcp 65001 > nul
cd /d "%~dp0"
dotnet run --project "Desktop\AFMI Smart Admin.csproj"
