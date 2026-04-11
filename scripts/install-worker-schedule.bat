@echo off
chcp 65001 > nul
title VFX SOTA - Worker 자동 실행 등록

set PROJECT_ROOT=%~dp0..

echo =====================================================
echo   Worker 자동 실행 등록 (Windows Task Scheduler)
echo =====================================================
echo.
echo 로그온 시 + 30분마다 Worker를 자동으로 1회 실행합니다.
echo 컴퓨터가 켜져 있을 때만 동작하며, 꺼져 있는 동안은 안 돕니다.
echo.
pause

set TASK_NAME=VFX_SOTA_Worker
set BAT_PATH=%PROJECT_ROOT%\scripts\run-worker-once.bat

schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if not errorlevel 1 (
    echo 기존 작업 발견. 삭제합니다...
    schtasks /delete /tn "%TASK_NAME%" /f
)

echo.
echo 새 작업 등록...
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%BAT_PATH%\"" ^
    /sc onstart ^
    /ri 30 ^
    /du 9999:59 ^
    /rl highest ^
    /f

if errorlevel 1 (
    echo.
    echo [ERROR] 등록 실패. 관리자 권한으로 다시 실행하세요.
    pause
    exit /b 1
)

echo.
echo =====================================================
echo   등록 완료: %TASK_NAME%
echo =====================================================
echo.
echo   - 컴퓨터 켜질 때 자동 실행
echo   - 이후 30분마다 반복
echo   - 중지/삭제: schtasks /delete /tn %TASK_NAME% /f
echo.
echo 확인: schtasks /query /tn %TASK_NAME% /v
echo.
pause
