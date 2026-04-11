# 설치/실행 스크립트

이 폴더에는 **두 역할**로 분리된 설치/실행 배치 파일이 있습니다.

## 역할 분리

| 역할 | 실행 PC | 하는 일 | 24/7 |
|------|---------|---------|------|
| **Web Server** | 구린 Windows PC (GPU 불필요) | FastAPI + SQLite + 웹 UI + 가벼운 크롤러 (arXiv/GitHub/HF) | ✅ |
| **Worker** | RTX 4090/5080/5090 같은 GPU PC | Gemma 4 26B LLM 배치 스코어링 | ❌ (필요할 때만) |

두 역할은 HTTP API로 통신합니다. Worker가 Web Server에 `GET /admin/pending-scoring`으로 미스코어 아이템을 가져가고, `POST /admin/score-update`로 결과를 돌려보냅니다.

## 네트워크 시나리오

### 시나리오 A: 같은 PC
Web Server와 Worker가 같은 PC (예: 개발/테스트)
```
Worker config.yaml:
  MAIN_PC_URL: http://127.0.0.1:8001
```

### 시나리오 B: 같은 LAN
Web Server (구린 PC) + Worker (GPU PC) 같은 공유기
```
Web Server: 192.168.1.100:8001
Worker config.yaml:
  MAIN_PC_URL: http://192.168.1.100:8001
```
Web Server의 Windows 방화벽에서 포트 8001 허용 필요.

### 시나리오 C: 다른 네트워크 (Tailscale)
두 PC가 서로 다른 네트워크
```
두 PC에 Tailscale 설치 + 같은 계정
Web Server Tailscale IP: 100.x.x.x
Worker config.yaml:
  MAIN_PC_URL: http://100.x.x.x:8001
```

### 시나리오 D: Cloudflare Tunnel
Web Server가 Cloudflare Tunnel로 외부 공개 (팀원 접속용)
```
Worker config.yaml:
  MAIN_PC_URL: https://vfx-sota.yourdomain.com
```

---

## Web Server PC에서

### 최초 1회 설치
```
scripts\install-webserver.bat
```
- Python/Node 확인
- .env 파일 자동 생성 (ADMIN_TOKEN 수동 편집)
- Backend venv + 의존성
- DB 마이그레이션 + 카테고리 시드 + SOTA 시드
- Frontend 의존성 + 빌드

### 실행
```
scripts\start-webserver.bat
```
- Backend (포트 8001) + Frontend (포트 3001) 각각 새 창에서 실행
- 브라우저 자동 오픈
- 매일 09:00 KST 자동 크롤 (APScheduler)
- 중지: 각 창 닫기

### 24/7 자동 실행 (선택)
NSSM으로 Windows 서비스 등록하거나 Task Scheduler 사용. `docs/DEPLOYMENT.md` 참고.

### 외부 팀원 접근 (선택)
Cloudflare Tunnel 설치. `docs/DEPLOYMENT.md` 참고.

---

## Worker PC에서 (GPU 머신)

### 필요한 것
- NVIDIA GPU (VRAM 16GB+)
- Python 3.12+
- [Ollama](https://ollama.com/download)
- `gemma4:26b` 모델 (설치 스크립트가 자동 다운로드)
- Web Server PC에 네트워크 접근 가능

### 최초 1회 설치
```
scripts\install-worker.bat
```
- Ollama + gemma4:26b 확인 (없으면 자동 다운로드)
- Worker venv + 의존성
- `ai_cluster_worker/config.yaml` 생성 (MAIN_PC_URL + ADMIN_TOKEN 입력 받음)

### 실행

**1회만 돌리고 종료:**
```
scripts\run-worker-once.bat
```
→ 미스코어 아이템 최대 50개 처리하고 종료

**지속 실행 (5분마다 폴링):**
```
scripts\start-worker.bat
```
→ 창 닫기 전까지 새 아이템 들어오면 자동 처리

**자동 실행 (컴퓨터 켜질 때 + 30분마다):**
```
scripts\install-worker-schedule.bat (관리자 권한)
```
→ Windows Task Scheduler에 등록. 5090 PC 가끔 켤 때 자동으로 밀린 작업 처리.

### 새벽에만 몰래 쓸 때
5090/5080 작업용 PC를 새벽에 쓸 수 있을 때:
1. `scripts\install-worker.bat` 한 번만 실행 (Ollama/venv/config 세팅)
2. `scripts\run-worker-once.bat` 실행
3. 끝나면 창 닫기
4. 원래 작업하던 PC로 복귀

`install-worker-schedule.bat`를 쓰면 자동화되지만, **공용 PC에서는 수동 실행이 안전**합니다.

---

## 삭제

### Worker 자동 실행 해제
```
schtasks /delete /tn VFX_SOTA_Worker /f
```

### 전체 삭제
- `backend/.venv/` 삭제
- `frontend/node_modules/` 삭제
- `ai_cluster_worker/.venv/`, `config.yaml` 삭제
- `backend/data/vfx_sota.db` 백업 후 삭제

---

## 트러블슈팅

### npm install 에러 (EBADF)
Google Drive "다른 컴퓨터" 경로에서는 npm이 깨집니다. 프로젝트를 `C:\Users\<user>\dev\` 같은 **로컬 경로**로 clone해서 설치하세요.

### Worker가 401 Unauthorized
`config.yaml`의 `ADMIN_TOKEN`이 Web Server의 `.env`와 다릅니다. 두 값을 일치시키세요.

### Worker가 Connection refused
- Web Server가 안 돌고 있거나
- 방화벽이 포트 8001 막거나
- `MAIN_PC_URL`이 잘못됨
- 같은 PC가 아니면 `127.0.0.1` 대신 실제 IP 사용

### Gemma 4 응답 없음 / OOM
- VRAM 부족 (gemma4:26b는 Q4 기준 16GB 필요)
- `config.yaml`의 `BATCH_SIZE`를 2로 줄이세요
- 다른 GPU 프로세스 종료
