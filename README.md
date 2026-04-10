# VFX SOTA Monitor

Red Cat Gang VFX팀을 위한 AI SOTA 자동 모니터링 시스템.

**통합 예정**: [glocal30Hub](https://github.com/jsdavid88-dsu/glocal30Hub) 통합 포털의 모듈로 편입.

## 개요

매일 아침 **arXiv / GitHub / HuggingFace / Reddit / X**에서 VFX 관련 최신 연구/모델/저장소/논의를 자동 수집하고, 로컬 Gemma 4 26B로 관련성을 판단하여 팀 대시보드에 표시합니다.

## 아키텍처 (2-PC 분산)

```
           ┌─── 팀원 20-30명 (외부) ───┐
           │                         │
           │  HTTPS via Cloudflare    │
           │       Tunnel (무료)       │
           ▼                         │
┌──────────────────────┐             │
│ 메인 PC (Windows 24/7)  │             │
│ - FastAPI + SQLite     │             │
│ - Vite React          │◀────────────┘
│ - APScheduler 크롤     │
│ - 키워드 스코어링       │
└──────────┬───────────┘
           │
           │ Tailscale VPN
           │ (PC 간 내부 통신)
           ▼
┌──────────────────────┐
│ AI Cluster PC          │
│ (RTX 4090, 필요시)      │
│ - Ollama Gemma 4 26B   │
│ - worker.py (배치)     │
└──────────────────────┘
```

## 스택

- **Frontend**: React 19 + Vite 7 + TypeScript 5.9 + Tailwind CSS 4
- **Backend**: FastAPI + SQLAlchemy 2 async + SQLite + Alembic
- **LLM**: Ollama + Gemma 4 26B (별도 PC)
- **Deploy**: 네이티브 실행 (Docker 불필요)
- **External**: Cloudflare Tunnel
- **PC Link**: Tailscale VPN

> glocal30Hub와 스택 100% 일치 — 추후 통합 시 코드 이식 쉬움

## 추적 카테고리 (10개)

| ID | 한글 | 주요 기술 |
|----|------|-----------|
| video_matting | 비디오 매팅 | VideoMaMa, MatAnyone 2 |
| video_removal | 비디오 리무벌 | VOID (Netflix), EffectErase |
| face_parsing | 페이스 파싱 | SAM 3.1, SegFace |
| point_tracking | 포인트 트래킹 | Track-On, CoTracker3 |
| head_swap | 헤드 스왑 | Wan-Animate, DirectSwap |
| 3dgs | 3D 가우시안 | Nerfstudio, AA-Splat |
| beauty | 뷰티 보정 | AuthFace, MoFRR |
| korean_text_edit | 한글 텍스트 | STELLAR, TextFlow |
| ref_search | Ref 검색 | Qwen3-VL-Embedding |
| qc_program | QC 프로그램 | DaVinci API |

---

## 설치 및 실행

### 사전 요구사항

- **메인 PC**: Python 3.12+, Node.js 22+
- **AI Cluster PC** (선택): Ollama + `ollama pull gemma4:26b`

### 1. 메인 PC — Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# .env 생성
copy ..\.env.example ..\.env
# .env 편집 (최소 ADMIN_TOKEN만 바꾸면 시작 가능)

# DB 초기화
alembic upgrade head
python seed.py

# 실행
uvicorn app.main:app --reload --port 8001 --host 0.0.0.0
```

API 문서: http://localhost:8001/docs

### 2. 메인 PC — Frontend

```powershell
cd frontend
npm install
npm run dev -- --port 3001 --host 0.0.0.0
```

브라우저: http://localhost:3001

### 3. AI Cluster PC — Worker (Phase 3 이후)

```powershell
cd ai_cluster_worker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# config.yaml 편집 → MAIN_PC_URL, ADMIN_TOKEN
python worker.py --once
```

---

## 외부 접근 설정 (Cloudflare Tunnel)

팀원들이 외부에서 `https://vfx-sota.yourdomain.com` 같은 주소로 접속 가능하게 하려면:

### 테스트용 (임시 URL)
```powershell
# cloudflared 설치: https://github.com/cloudflare/cloudflared/releases
cloudflared tunnel --url http://localhost:3001
# → https://xxxx-xxxx.trycloudflare.com URL 출력됨
```

### 영구 도메인 (무료)

1. Cloudflare 계정 가입 + 도메인 등록 (또는 무료 도메인 사용)
2. `cloudflared tunnel login`
3. `cloudflared tunnel create vfx-sota`
4. `config.yml` 작성:
   ```yaml
   tunnel: <tunnel-id>
   credentials-file: C:\Users\...\.cloudflared\<tunnel-id>.json
   ingress:
     - hostname: vfx-sota.yourdomain.com
       service: http://localhost:3001
     - service: http_status:404
   ```
5. `cloudflared tunnel route dns vfx-sota vfx-sota.yourdomain.com`
6. `cloudflared tunnel run vfx-sota`
7. Windows 서비스 등록: `cloudflared service install`

## PC 간 연결 (Tailscale)

두 PC가 같은 네트워크가 아니어도 작동:

1. 두 PC에 [Tailscale](https://tailscale.com/download) 설치
2. 같은 계정으로 로그인
3. 각 PC에 `100.x.x.x` 내부 IP 자동 할당됨
4. AI Cluster Worker의 `config.yaml`:
   ```yaml
   MAIN_PC_URL: http://100.101.102.103:8001  # 메인 PC의 Tailscale IP
   ```

---

## 구조

```
vfx-sota-monitor/
├── backend/              # FastAPI + SQLite
│   ├── app/
│   │   ├── models/       # SQLAlchemy 모델
│   │   ├── schemas/      # Pydantic
│   │   ├── routers/      # API 엔드포인트
│   │   ├── sources/      # 5개 수집기 (Phase 2)
│   │   ├── scoring/      # 키워드 스코어링
│   │   └── tasks/        # APScheduler
│   ├── alembic/
│   ├── data/
│   │   └── vfx_sota.db   # SQLite 파일
│   └── seed.py
├── frontend/             # React 19 + Vite
│   └── src/
│       ├── pages/        # 5개 페이지
│       ├── components/
│       └── api/
├── ai_cluster_worker/    # AI Cluster PC용 (Phase 3)
│   └── worker.py
├── docker-compose.yml    # 옵션 (지금은 안 씀)
└── PLAN.md               # 상세 구현 플랜
```

## Phase

| Phase | 상태 | 내용 |
|-------|------|------|
| 1. 뼈대 | ✅ 완료 | Backend + Frontend 기본 구조 |
| 1.5. 네이티브화 | ✅ 완료 | Docker → 네이티브 + SQLite |
| 2. 데이터 수집 | 🔜 | arXiv/GitHub/HF/Reddit/X 수집기 |
| 3. LLM 스코어링 | 🔜 | AI Cluster Worker + Gemma 4 |
| 4. 프론트 고도화 | 🔜 | 검색/필터/정렬 |
| 5. 기술 계보 | 🔜 | Semantic Scholar + reactflow |
| 6. 댓글 + Hub 통합 | 🔜 | 댓글 UI + OAuth 어댑터 |
| 7. 배포 | 🔜 | Cloudflare Tunnel + Windows 서비스 |

## 라이선스

Internal use — Red Cat Gang / Dongseo University
