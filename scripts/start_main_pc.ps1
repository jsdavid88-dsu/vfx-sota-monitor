# 메인 PC 전체 스택 실행 스크립트 (개발/테스트용)
# 프로덕션은 NSSM으로 서비스 등록

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "[1/3] Backend starting..."
$backendJob = Start-Job -ScriptBlock {
    param($r)
    Set-Location "$r\backend"
    & ".venv\Scripts\activate.ps1"
    uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
} -ArgumentList $root

Start-Sleep -Seconds 3

Write-Host "[2/3] Frontend starting..."
$frontendJob = Start-Job -ScriptBlock {
    param($r)
    Set-Location "$r\frontend"
    npm run dev -- --port 3001 --host 0.0.0.0
} -ArgumentList $root

Write-Host ""
Write-Host "========================================"
Write-Host "  VFX SOTA Monitor is starting..."
Write-Host ""
Write-Host "  Backend:   http://localhost:8001"
Write-Host "  API docs:  http://localhost:8001/docs"
Write-Host "  Frontend:  http://localhost:3001"
Write-Host ""
Write-Host "  Press Ctrl+C to stop both."
Write-Host "========================================"

try {
    while ($true) {
        Receive-Job $backendJob -Keep
        Receive-Job $frontendJob -Keep
        Start-Sleep -Seconds 2
    }
} finally {
    Stop-Job $backendJob, $frontendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob, $frontendJob -ErrorAction SilentlyContinue
}
