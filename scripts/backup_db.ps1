# VFX SOTA Monitor — SQLite 백업 스크립트
# Task Scheduler로 매일 새벽 3시 실행

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root "backend\data\vfx_sota.db"
$backupDir = Join-Path $root "backups"

if (-not (Test-Path $src)) {
    Write-Error "Source DB not found: $src"
    exit 1
}

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$date = Get-Date -Format "yyyy-MM-dd_HHmm"
$dest = Join-Path $backupDir "vfx_sota_$date.db"

# SQLite는 running 상태에서도 복사 가능 (WAL 모드)
# 안전하게 하려면 .backup 커맨드 사용
Copy-Item $src $dest -Force
Write-Host "[backup] $dest"

# 30일 이전 백업 정리
$cutoff = (Get-Date).AddDays(-30)
Get-ChildItem $backupDir -Filter "vfx_sota_*.db" |
    Where-Object { $_.LastWriteTime -lt $cutoff } |
    ForEach-Object {
        Remove-Item $_.FullName
        Write-Host "[prune] $($_.Name)"
    }

Write-Host "[done]"
