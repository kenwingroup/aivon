@echo off
chcp 65001 >nul
title Dung AIVON
echo Dang tim va tat AIVON...
REM Logic giet nam trong stop-aivon.ps1 (giet theo dung python cua venv + chu port 7979).
REM KHONG dung timeout o day: chay an qua VBS se loi "Input redirection is not supported".
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-aivon.ps1"
REM Don cua so CMD den "AIVON" kieu cu con sot (flow moi chay an, khong tao cua so nay).
taskkill /F /FI "IMAGENAME eq cmd.exe" /FI "WINDOWTITLE eq AIVON*" >nul 2>&1
echo Xong.
exit /b 0
