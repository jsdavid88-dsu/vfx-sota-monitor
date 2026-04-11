@echo off
chcp 65001 > nul
title VFX SOTA - Worker 지속 실행

set PROJECT_ROOT=%~dp0..
cd /d "%PROJECT_ROOT%\ai_cluster_worker"

if not exist config.yaml (
    echo [ERROR] config.yaml이 없습니다. 먼저 install-worker.bat 실행
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8

echo =====================================================
echo   Gemma 4 26B Worker - 5분마다 폴링
echo =====================================================
echo.
echo 새 아이템이 생기면 5분 이내에 자동 스코어링됩니다.
echo 중지: Ctrl+C
echo.
.venv\Scripts\python.exe worker.py --interval 300
