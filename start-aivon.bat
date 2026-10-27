@echo off
chcp 65001 >nul
title Khoi dong AIVON
cd /d "%~dp0"

echo Bat AIVON chay NEN - khong con cua so den (port 7979)...
REM Viec tat instance cu + chay server AN giao het cho start-aivon.vbs (cua so an hoan toan).
REM Log ghi vao server\aivon.log (mo file do neu can xem loi). Tat server: stop-aivon.bat.
wscript //nologo start-aivon.vbs

echo.
echo Da bat. Cho ~10 giay roi mo http://localhost:7979 va bam Ctrl+Shift+R.
echo (Tat server: chay stop-aivon.bat. Xem loi: mo file server\aivon.log)
timeout /t 4 >nul
