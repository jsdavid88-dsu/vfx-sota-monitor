# 배포 가이드

VFX SOTA Monitor를 Windows 메인 PC에 24/7 실행하고, 외부에서 팀원들이 접속 가능하게 만드는 방법.

## 목표 아키텍처

```
팀원 (외부)
  ↓ HTTPS
Cloudflare Tunnel
  ↓
Windows 메인 PC (24/7)
  ├── uvicorn (backend) :8001
  ├── vite preview or nginx (frontend) :3001
  ├── cloudflared
  └── SQLite backup task (daily)
         ↑
         │ Tailscale
         │
AI Cluster PC (on-demand)
  ├── Ollama + Gemma 4 26B
  └── worker.py --interval 300
```

---

## 1. 메인 PC 프로덕션 세팅

### 1-1. Python 가상환경
```powershell
cd G:\path\to\sota-monitor\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 1-2. 프로덕션 빌드 (프론트)
```powershell
cd ..\frontend
npm install
npm run build
# dist/ 폴더 생성
```

개발 모드가 아닌 정적 파일을 서빙하려면 `vite preview` 또는 nginx 사용:

**옵션 A: vite preview (간단)**
```powershell
npm run preview -- --port 3001 --host 0.0.0.0
```

**옵션 B: serve (더 가벼움)**
```powershell
npm install -g serve
serve -s dist -l 3001
```

### 1-3. 환경 변수
```powershell
copy .env.example .env
notepad .env
```

필수:
```
ADMIN_TOKEN=<팀 내부만 아는 랜덤 문자열>
GITHUB_TOKEN=ghp_...
VITE_API_URL=https://vfx-sota.yourdomain.com  # 프론트가 부를 API
```

### 1-4. DB 초기화
```powershell
alembic upgrade head
python seed.py
```

---

## 2. Windows 서비스 등록 (자동 시작)

### 옵션 A: NSSM (추천, 가장 간단)

1. [NSSM 다운로드](https://nssm.cc/download)
2. `nssm.exe` 를 `C:\Windows\System32\` 에 복사
3. Backend 서비스 등록:
```powershell
nssm install VFX-SOTA-Backend
# Path: G:\path\to\backend\.venv\Scripts\python.exe
# Startup directory: G:\path\to\backend
# Arguments: -m uvicorn app.main:app --host 0.0.0.0 --port 8001
nssm set VFX-SOTA-Backend AppStdout G:\logs\vfx-backend.log
nssm set VFX-SOTA-Backend AppStderr G:\logs\vfx-backend.err.log
nssm start VFX-SOTA-Backend
```

4. Frontend 서비스:
```powershell
nssm install VFX-SOTA-Frontend
# Path: C:\Program Files\nodejs\npx.cmd
# Startup directory: G:\path\to\frontend
# Arguments: serve -s dist -l 3001
nssm start VFX-SOTA-Frontend
```

### 옵션 B: Task Scheduler (순정)

```powershell
# Backend
schtasks /create /tn "VFX SOTA Backend" /tr "G:\path\to\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001" /sc onstart /ru SYSTEM /rl HIGHEST

# Frontend
schtasks /create /tn "VFX SOTA Frontend" /tr "cmd /c cd /d G:\path\to\frontend && npx serve -s dist -l 3001" /sc onstart /ru SYSTEM
```

---

## 3. Cloudflare Tunnel (외부 HTTPS 접근)

포트 포워딩 없이 외부에서 `https://vfx-sota.yourdomain.com`으로 접속 가능.

### 3-1. 설치
1. [cloudflared Windows](https://github.com/cloudflare/cloudflared/releases) 다운로드
2. `C:\Program Files\cloudflared\cloudflared.exe` 배치
3. PATH에 추가

### 3-2. Cloudflare 계정
1. [dash.cloudflare.com](https://dash.cloudflare.com) 가입 (무료)
2. 도메인 등록 또는 `trycloudflare.com` 서브도메인 사용 (임시)

### 3-3. 터널 생성
```powershell
cloudflared tunnel login
cloudflared tunnel create vfx-sota
# → 터널 ID 출력됨. credentials JSON이 ~\.cloudflared\<id>.json 에 저장됨
```

### 3-4. config.yml
`C:\Users\<user>\.cloudflared\config.yml`:

```yaml
tunnel: <your-tunnel-id>
credentials-file: C:\Users\<user>\.cloudflared\<your-tunnel-id>.json

ingress:
  # 프론트엔드
  - hostname: vfx-sota.yourdomain.com
    service: http://localhost:3001

  # API (CORS 설정 필요)
  - hostname: api.vfx-sota.yourdomain.com
    service: http://localhost:8001

  # Catch-all
  - service: http_status:404
```

### 3-5. DNS 레코드 생성
```powershell
cloudflared tunnel route dns vfx-sota vfx-sota.yourdomain.com
cloudflared tunnel route dns vfx-sota api.vfx-sota.yourdomain.com
```

### 3-6. 실행
```powershell
# 테스트
cloudflared tunnel run vfx-sota

# Windows 서비스로 영구 등록
cloudflared service install
```

### 3-7. 임시 URL (도메인 없이 테스트)
```powershell
cloudflared tunnel --url http://localhost:3001
# → https://xxxx-xxxx.trycloudflare.com 자동 생성
```

---

## 4. CORS 설정 (API 외부 접근 시)

`backend/.env`:
```
# Hub 통합 후에는 Hub 도메인도 포함
CORS_ORIGINS=["https://vfx-sota.yourdomain.com", "http://localhost:3001"]
```

또는 `backend/app/config.py`의 `cors_origins` 직접 수정.

---

## 5. AI Cluster PC 연결 (Tailscale)

두 PC가 다른 네트워크에 있어도 VPN으로 연결.

### 5-1. 메인 PC
1. [Tailscale Windows](https://tailscale.com/download/windows) 설치
2. 계정 생성 + 로그인
3. 설치 후 `tailscale ip -4` → 메인 PC의 100.x.x.x IP 확인

### 5-2. AI Cluster PC
1. 같은 Tailscale 계정으로 로그인
2. `ai_cluster_worker/config.yaml`:
```yaml
MAIN_PC_URL: http://100.101.102.103:8001  # 메인 PC Tailscale IP
ADMIN_TOKEN: <메인 PC의 .env와 동일>
```

### 5-3. Worker 자동 실행 (AI Cluster PC)
```powershell
# 5분마다 폴링
schtasks /create /tn "VFX SOTA Worker" /tr "G:\path\to\ai_cluster_worker\.venv\Scripts\python.exe G:\path\to\ai_cluster_worker\worker.py --once" /sc minute /mo 5
```

또는 NSSM으로 `--interval 300` 모드 서비스 등록.

---

## 6. SQLite 백업

매일 새벽 3시에 `data/vfx_sota.db` → `backup/YYYY-MM-DD.db` 로테이션.

`scripts/backup_db.ps1`:
```powershell
$src = "G:\path\to\backend\data\vfx_sota.db"
$backupDir = "G:\path\to\backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$date = Get-Date -Format "yyyy-MM-dd"
$dest = "$backupDir\vfx_sota_$date.db"
Copy-Item $src $dest -Force

# 30일보다 오래된 백업 삭제
Get-ChildItem $backupDir -Filter "vfx_sota_*.db" |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
  Remove-Item
```

Task Scheduler 등록:
```powershell
schtasks /create /tn "VFX SOTA Backup" /tr "powershell -File G:\path\to\scripts\backup_db.ps1" /sc daily /st 03:00
```

---

## 7. 헬스체크

```powershell
# Backend
curl http://localhost:8001/health

# Frontend
curl http://localhost:3001

# Cloudflare
curl https://vfx-sota.yourdomain.com/health

# 크롤 이력
curl -H "X-Admin-Token: xxx" http://localhost:8001/api/admin/runs
```

---

## 8. 운영 팁

- **수동 크롤**: `POST /api/admin/crawl` (X-Admin-Token 헤더 필수)
- **단일 소스 크롤**: `POST /api/admin/crawl/arxiv` 등
- **DB 백업 복원**: `Copy-Item backup/yyyy-mm-dd.db data/vfx_sota.db`
- **로그 확인**: NSSM 설정한 경로 또는 `G:\logs\`
- **Gemma 모델 업데이트**: `ollama pull gemma4:26b`
- **스케줄러 확인**: 매일 09:00 KST 자동 크롤 (APScheduler, main.py lifespan)

---

## 9. Hub 통합 마이그레이션 (나중에)

glocal30Hub에 편입할 때:

1. **DB**: SQLite → Hub의 Postgres로 덤프/로드 (Alembic)
   ```powershell
   # SQLite → SQL dump → Postgres 변환
   python scripts/export_to_postgres.py
   ```

2. **Frontend**: `frontend/src/` 컴포넌트를 Hub의 `frontend/src/modules/vfx/`로 이동

3. **Backend**: `backend/app/` 라우터를 Hub의 `backend/app/modules/vfx/`로 편입, prefix `/modules/vfx` 적용

4. **인증**: `backend/app/auth.py`를 Hub의 JWT 검증으로 교체 (이 파일 하나만 수정)

5. **포트**: 3001/8001 → Hub의 3000/8000으로 통합

6. **DNS**: `vfx-sota.yourdomain.com` → `hub.yourdomain.com/vfx`
