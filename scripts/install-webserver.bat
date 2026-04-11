@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul
title VFX SOTA - Web Server 설치

echo =====================================================
echo   VFX SOTA Monitor - Web Server 설치
echo   (웹 호스팅 + DB + 가벼운 크롤러)
echo =====================================================
echo.

REM Check prerequisites
echo [확인] Python...
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.12+ 가 필요합니다. https://python.org
    pause
    exit /b 1
)
python --version

echo [확인] Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 22+ 가 필요합니다. https://nodejs.org
    pause
    exit /b 1
)
node --version

set PROJECT_ROOT=%~dp0..
cd /d "%PROJECT_ROOT%"

REM .env 생성
if not exist .env (
    echo.
    echo [1/5] .env 파일 생성...
    copy .env.example .env > nul
    echo.
    echo *** 중요 ***
    echo %PROJECT_ROOT%\.env 파일을 열어서 ADMIN_TOKEN 값을 랜덤 문자열로 변경하세요.
    echo 이 값이 Worker와 공유할 비밀번호입니다.
    echo.
    pause
)

REM Backend venv
echo.
echo [2/5] Backend 가상환경 생성...
cd backend
if not exist .venv (
    python -m venv .venv
)

echo [2/5] Backend 의존성 설치...
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Backend 의존성 설치 실패
    pause
    exit /b 1
)

REM DB init
echo.
echo [3/5] DB 마이그레이션...
set DISABLE_SCHEDULER=1
set PYTHONIOENCODING=utf-8
python -m alembic upgrade head
if errorlevel 1 (
    echo [ERROR] 마이그레이션 실패
    pause
    exit /b 1
)

echo [3/5] 카테고리 시드 + SOTA 시드...
python seed.py
python seed_sota.py

REM Frontend install
echo.
echo [4/5] Frontend 의존성 설치...
cd /d "%PROJECT_ROOT%\frontend"
call npm install
if errorlevel 1 (
    echo [ERROR] npm install 실패
    echo 구글 드라이브 경로이면 C:\Users\<user>\dev\ 에 clone한 뒤 거기서 설치하세요.
    pause
    exit /b 1
)

REM Frontend build
echo.
echo [5/5] Frontend 프로덕션 빌드...
call npm run build
if errorlevel 1 (
    echo [WARN] build 실패 — dev 모드로 실행 가능합니다.
)

echo.
echo =====================================================
echo   설치 완료
echo =====================================================
echo.
echo 실행: scripts\start-webserver.bat
echo 외부 접근: docs\DEPLOYMENT.md 참고 (Cloudflare Tunnel)
echo.
pause
