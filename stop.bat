@echo off
title Shelflick Durdurucu
color 0c

echo ========================================================
echo               S H E L F L I C K
echo             Sunuculari Durdurma
echo ========================================================
echo.

echo [1/3] Port 8000 (Backend / FastAPI) durduruluyor...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
echo [OK] Backend durduruldu.

echo [2/3] Port 3000 (Frontend / Next.js) durduruluyor...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
echo [OK] Frontend durduruldu.

echo [3/3] PostgreSQL (WSL) servisi kapatiliyor...
taskkill /FI "WINDOWTITLE eq Shelflick - PostgreSQL (WSL)*" /T /F >nul 2>&1
wsl -d Ubuntu -u root -- service postgresql stop >nul 2>&1
echo [OK] PostgreSQL servisi durduruldu.

echo.
echo ========================================================
echo   Shelflick Servisleri Basariyla Durduruldu!
echo ========================================================
echo Bu pencere birazdan kapanacaktir...
ping 127.0.0.1 -n 3 >nul
exit
