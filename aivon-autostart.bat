@echo off
chcp 65001 >nul
title Tu khoi dong AIVON
REM Tu khoi dong Aivon cung Windows. Dung: aivon-autostart.bat install | uninstall | status
REM Logic nam trong aivon-autostart.ps1 (tao/xoa shortcut trong thu muc Startup cua user,
REM khong can quyen admin). Bat roi thi dang nhap may la server tu chay nen.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0aivon-autostart.ps1" %1
