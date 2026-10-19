@echo off
title Shelflick Baslatici
color 0b

echo ========================================================
echo               S H E L F L I C K
echo             Otomatik Baslatma
echo ========================================================
echo.

REM 1. Proje dizini tespiti
set "PROJ_DIR=C:\Users\Enes\Desktop\Shelflick0.1\Shelflick"
if not exist "%PROJ_DIR%\backend" set "PROJ_DIR=C:\Users\Enes\Desktop\Shelflick"
if not exist "%PROJ_DIR%\backend" set "PROJ_DIR=%~dp0"
if not exist "%PROJ_DIR%\backend" set "PROJ_DIR=%~dp0Shelflick"
if not exist "%PROJ_DIR%\backend" set "PROJ_DIR=%~dp0Shelflick0.1\Shelflick"

if not exist "%PROJ_DIR%\backend" (
    echo [HATA] Proje klasoru bulunamadi!
    pause
    exit /b 1
)

set "BACKEND_DIR=%PROJ_DIR%\backend"
set "FRONTEND_DIR=%PROJ_DIR%\frontend"

echo [BILGI] Proje: %PROJ_DIR%
echo.

REM 2. WSL PostgreSQL Servisi (WSL'in kapanmasini engelleyen acik terminal)
echo [1/3] PostgreSQL (WSL) baslatiliyor...
taskkill /FI "WINDOWTITLE eq Shelflick - PostgreSQL (WSL)*" /T /F >nul 2>&1
start "Shelflick - PostgreSQL (WSL)" cmd /k "title Shelflick - PostgreSQL (WSL) && echo ============================================ && echo   S H E L F L I C K  -  P o s t g r e S Q L   && echo   Bu pencereyi kapatmayiniz!                && echo   (WSL oturumunu canli tutar)                && echo ============================================ && wsl -d Ubuntu -u root -- service postgresql start && wsl -d Ubuntu -u root -- bash"

echo PostgreSQL hazirlaniyor (3 saniye)...
ping 127.0.0.1 -n 4 >nul
echo [OK] PostgreSQL servisi aktif.
echo.

REM 3. Backend (FastAPI / Uvicorn)
echo [2/3] Backend baslatiliyor (Port 8000)...
if exist "%BACKEND_DIR%\.venv\Scripts\python.exe" (
    start "Shelflick - Backend" cmd /k "cd /d "%BACKEND_DIR%" && title Shelflick - Backend && echo Backend Calisiyor... && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
) else (
    start "Shelflick - Backend" cmd /k "cd /d "%BACKEND_DIR%" && title Shelflick - Backend && echo Backend Calisiyor... && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)
echo [OK] Backend yeni pencerede acildi.
echo.

REM 4. Frontend (Next.js)
echo [3/3] Frontend baslatiliyor (Port 3000)...
start "Shelflick - Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && title Shelflick - Frontend && echo Frontend Calisiyor... && npm run dev"
echo [OK] Frontend yeni pencerede acildi.
echo.

REM 5. Tarayiciyi Ac
echo Servislerin hazir olmasi bekleniyor (4 saniye)...
ping 127.0.0.1 -n 5 >nul

echo Tarayici aciliyor: http://localhost:3000
start http://localhost:3000

echo.
echo ========================================================
echo   Shelflick Basariyla Baslatildi!
echo   - PostgreSQL: WSL Terminalinde Acik Tutuluyor
echo   - Frontend  : http://localhost:3000
echo   - Backend   : http://127.0.0.1:8000
echo   - Docs      : http://127.0.0.1:8000/docs
echo ========================================================
echo Bu ana pencere birazdan kapanacaktir...
ping 127.0.0.1 -n 4 >nul
exit
