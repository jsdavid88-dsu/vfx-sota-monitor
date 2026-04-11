@echo off
chcp 65001 > nul
title VFX SOTA - Worker 1회 실행

set PROJECT_ROOT=%~dp0..
cd /d "%PROJECT_ROOT%\ai_cluster_worker"

if not exist config.yaml (
    echo [ERROR] config.yaml이 없습니다. 먼저 install-worker.bat 실행
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8

echo =====================================================
echo   Gemma 4 26B 배치 스코어링 1회 실행
echo =====================================================
echo.
.venv\Scripts\python.exe worker.py --once
echo.
echo 완료. Ctrl+C 누르지 말고 창 닫으세요.
pause
