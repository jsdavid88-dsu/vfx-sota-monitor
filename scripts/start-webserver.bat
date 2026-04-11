@echo off
chcp 65001 > nul
title VFX SOTA - Web Server 실행

set PROJECT_ROOT=%~dp0..
cd /d "%PROJECT_ROOT%"

if not exist .env (
    echo [ERROR] .env 파일이 없습니다. 먼저 install-webserver.bat 실행
    pause
    exit /b 1
)

echo =====================================================
echo   VFX SOTA Monitor - Web Server 시작
echo =====================================================
echo.
echo   Backend API:  http://localhost:8001
echo   Frontend UI:  http://localhost:3001
echo   API Docs:     http://localhost:8001/docs
echo.
echo   매일 09:00 KST 자동 크롤 (APScheduler)
echo =====================================================
echo.
echo 백엔드와 프론트엔드가 각각 새 창에서 실행됩니다.
echo 각 창을 닫으면 해당 서비스가 중지됩니다.
echo.
pause

REM Backend in new window
start "VFX-Backend (port 8001)" cmd /k "cd /d %PROJECT_ROOT%\backend && set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001"

REM Frontend in new window — prefer built dist, fall back to dev
if exist "%PROJECT_ROOT%\frontend\dist\index.html" (
    start "VFX-Frontend (port 3001, built)" cmd /k "cd /d %PROJECT_ROOT%\frontend && npx serve -s dist -l 3001"
) else (
    echo dist 폴더 없음 — dev 모드로 실행합니다
    start "VFX-Frontend (port 3001, dev)" cmd /k "cd /d %PROJECT_ROOT%\frontend && npm run dev -- --port 3001 --host 0.0.0.0"
)

echo.
echo 3초 후 브라우저를 엽니다...
timeout /t 3 /nobreak > nul
start http://localhost:3001
