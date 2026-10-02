@echo off
echo Stopping bot...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Restricted Content DL Bot" >nul 2>&1
echo Bot stopped.
pause
