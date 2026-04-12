# VFX SOTA Monitor — 최종 구현 플랜 v3

## Context

Red Cat Gang VFX팀(20-30명)이 매일 AI SOTA를 자동 추적하는 시스템.

- **glocal30Hub와 통합 예정** — 같은 스택, 같은 Windows 메인 PC에서 운영
- **분산 구조** — 약한 메인 PC(24/7)에서 수집/웹 제공, 강한 AI Cluster PC(RTX 4090)에서 LLM 스코어링
- **외부 접근 필요** — 팀원들이 학교 밖에서도 접속 가능해야 함

## 확정된 결정사항 (최종)

1. ✅ **Docker 미사용** (Windows 네이티브) — 메인 PC가 약해서 Docker 부담됨
2. ✅ **SQLite** — 파일 기반, 설치 불필요, 20-30명/하루 수백 아이템 규모 충분
3. ✅ **스택 glocal30Hub 100% 일치** — FastAPI + React 19 + Vite 7 + Tailwind 4
4. ✅ **인증 생략** — 추후 Hub의 OAuth 재사용
5. ✅ **2-PC 분산 아키텍처**:
   - **메인 PC** (Windows, 24/7): FastAPI + SQLite + Vite, 수집/웹/키워드 스코어링
   - **AI Cluster PC** (RTX 4090, 필요할 때만): Ollama Gemma 4 26B + worker.py
6. ✅ **외부 접근**: Cloudflare Tunnel (무료, 포트 포워딩 불필요)
7. ✅ **PC 간 통신**: Tailscale (두 PC가 각각 IP, 서로 다른 네트워크 가정)
8. ✅ **소스**: arXiv, GitHub, HuggingFace, Reddit(PRAW), X(fxtwitter)
9. ✅ **댓글**: DB 스키마는 준비, UI는 Phase 6

## 최종 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│  팀원 20-30명 (외부)                                       │
│  https://vfx-sota.yourdomain.trycloudflare.com           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ HTTPS (Cloudflare Tunnel, 무료)
                   │
┌──────────────────▼──────────────────────────────────────┐
│  메인 PC (Windows, 24/7, 약한 컴퓨터)                       │
│  ┌────────────────────────────────────────────┐         │
│  │  glocal30Hub (기존)                          │         │
│  │  - frontend :3000 / backend :8000            │         │
│  └────────────────────────────────────────────┘         │
│  ┌────────────────────────────────────────────┐         │
│  │  VFX SOTA Monitor (신규)                      │         │
│  │  - frontend (Vite) :3001                     │         │
│  │  - backend (FastAPI + SQLite) :8001          │         │
│  │  - APScheduler → 5개 소스 매일 크롤          │         │
│  │  - 키워드 스코어링 (CPU, 즉시)                 │         │
│  │  - SQLite 파일: ./data/vfx_sota.db           │         │
│  └────────────────────────────────────────────┘         │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ Tailscale VPN (100.x.x.x, 무료)
                   │
┌──────────────────▼──────────────────────────────────────┐
│  AI Cluster PC (RTX 4090, 필요할 때만 가동)                │
│  ┌────────────────────────────────────────────┐         │
│  │  Ollama + Gemma 4 26B                        │         │
│  │  + worker.py (Python 스크립트)                │         │
│  │                                               │         │
│  │  실행 흐름 (수동 또는 스케줄):                   │         │
│  │  1. 메인 PC API 호출 (Tailscale 경유)          │         │
│  │     GET /api/admin/pending-scoring            │         │
│  │  2. 미스코어 아이템 가져옴                       │         │
│  │  3. Ollama로 배치 스코어링                      │         │
│  │  4. 결과 전송                                  │         │
│  │     POST /api/admin/score-update              │         │
│  └────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

## 프로젝트 구조 (최종)

```
vfx-sota-monitor/
├── PLAN.md                         # 이 파일
├── README.md                       # 네이티브 실행 가이드
├── .env.example
├── .gitignore
├── docker-compose.yml              # 옵션 (prod 배포 시만, 지금은 안 씀)
│
├── backend/                        # 메인 PC에서 실행
│   ├── requirements.txt            # aiosqlite, FastAPI, etc.
│   ├── alembic.ini
│   ├── alembic/
│   ├── seed.py                     # 10개 카테고리 시드
│   ├── data/
│   │   └── vfx_sota.db             # SQLite 파일 (gitignored)
│   └── app/
│       ├── main.py
│       ├── config.py               # SQLite URL
│       ├── database.py
│       ├── models/
│       ├── schemas/
│       ├── routers/
│       │   ├── categories.py
│       │   ├── items.py
│       │   ├── stats.py
│       │   ├── admin.py            # 🆕 pending-scoring, score-update
│       │   └── search.py
│       ├── sources/                # Phase 2
│       │   ├── arxiv_src.py
│       │   ├── github_src.py
│       │   ├── huggingface_src.py
│       │   ├── reddit_src.py
│       │   └── x_fxtwitter.py
│       ├── scoring/
│       │   └── keyword.py          # LLM은 worker에서
│       └── tasks/
│           └── scheduler.py        # APScheduler
│
├── frontend/                       # 메인 PC에서 실행
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── CategoryDetail.tsx
│       │   ├── ItemDetail.tsx
│       │   ├── Timeline.tsx
│       │   └── LineageGraph.tsx
│       └── components/
│
└── ai_cluster_worker/              # 🆕 AI Cluster PC에서 실행
    ├── README.md                   # 설치/실행 가이드
    ├── requirements.txt            # openai, httpx만
    ├── worker.py                   # 메인 워커
    ├── prompts.py                  # Gemma 프롬프트
    └── config.example.yaml         # MAIN_PC_URL 등
```

## 주요 포트 (glocal30Hub 충돌 회피)

| 서비스 | 포트 | 비고 |
|--------|------|------|
| glocal30Hub frontend | 3000 | 기존 |
| glocal30Hub backend | 8000 | 기존 |
| **VFX Monitor frontend** | **3001** | 신규 |
| **VFX Monitor backend** | **8001** | 신규 |
| Ollama (AI Cluster PC) | 11434 | 기본 |

## 네트워크 설정

### 1. Tailscale (두 PC 연결, 무료)
```
1. 두 PC 모두 tailscale.com에서 설치
2. 같은 계정으로 로그인
3. 각 PC에 100.x.x.x 내부 IP 자동 할당
4. 방화벽 설정 불필요, 자동 연결
5. AI Cluster Worker의 MAIN_PC_URL을 이 IP로
```

### 2. Cloudflare Tunnel (외부 접근, 무료)
```
1. 메인 PC에 `cloudflared` 설치
2. Cloudflare 계정 (무료) + 도메인 연결 (또는 trycloudflare.com 서브도메인)
3. cloudflared tunnel create vfx-sota
4. config.yml로 :3001 → https://vfx-sota.yourdomain.com 매핑
5. Windows 서비스로 등록 (부팅 시 자동 실행)
```

**장점:**
- 포트 포워딩 X (공유기 설정 불필요)
- HTTPS 자동 (Let's Encrypt 불필요)
- DDoS 방어 기본
- 완전 무료

## DB 스키마 (SQLite 호환)

기존 스키마 그대로, `JSON` 컬럼은 `TEXT`로 자동 매핑 (SQLAlchemy가 처리).

핵심 테이블:
- `categories` — 10개 VFX 카테고리
- `items` — 수집된 모든 아이템 (arxiv/github/hf/reddit/x)
- `item_categories` — M:N
- `lineage_edges` — 기술 계보 관계
- `comments` — Phase 6 UI용
- `crawl_runs` — 크롤 이력

## API 엔드포인트

```
# 조회 (프론트 + 외부 공개)
GET  /api/categories
GET  /api/categories/{slug}
GET  /api/items?source=&priority=&category=&since=&limit=&offset=
GET  /api/items/{id}
GET  /api/stats/summary
GET  /api/search?q=

# 관리 (AI Cluster Worker 및 수동 크롤용)
GET  /api/admin/pending-scoring          # llm_score=0 아이템 50개
POST /api/admin/score-update             # [{id, llm_score, llm_reason, priority}]
POST /api/admin/crawl/{source}           # 수동 크롤 트리거
GET  /api/admin/runs                     # 크롤 이력

# 댓글 (Phase 6)
GET  /api/items/{id}/comments
POST /api/items/{id}/comments
```

## 구현 Phase (병렬)

### Phase 1 ✅ 완료
뼈대 (FastAPI + React + 10 카테고리 시드 + 5개 페이지)

### Phase 1.5 🔄 (지금)
Docker 걷어내기 + SQLite 전환 + 네이티브 실행 가이드

### Phase 2 — 데이터 수집
- sources/arxiv_src.py (BeautifulSoup, arXiv 리스트 파싱)
- sources/github_src.py (PyGithub)
- sources/huggingface_src.py (huggingface_hub)
- sources/reddit_src.py (praw)
- sources/x_fxtwitter.py (httpx + api.fxtwitter.com)
- scoring/keyword.py (정규식 매칭)
- tasks/scheduler.py (APScheduler, 매일 아침 9시)
- routers/admin.py (크롤 트리거)

### Phase 3 — LLM 스코어링 (AI Cluster PC)
- ai_cluster_worker/ 전체 구현
- 백엔드: routers/admin.py에 pending-scoring, score-update
- Gemma 4 프롬프트 엔지니어링
- Tailscale 연결 가이드 문서

### Phase 4 — 프론트 고도화
- 검색 (클라이언트 사이드 fuzzy + 서버 ILIKE)
- 필터 패널 (source/priority/category/date)
- 정렬 (score/date/stars)
- 반응형 모바일 대응

### Phase 5 — 기술 계보 그래프
- Semantic Scholar API 통합 (인용 관계)
- LLM 관계 판단 (baseline/extends/replaces/competes)
- reactflow 그래프 뷰 (LineageGraph 페이지)
- 카테고리별 계보 서브그래프

### Phase 6 — 댓글 + Hub 통합 준비
- 댓글 CRUD UI
- 인증 어댑터 (Hub JWT 검증만 구현)
- glocal30Hub에 VFX 탭 추가 가이드

### Phase 7 — 배포
- Cloudflare Tunnel 설정 및 문서화
- Windows 서비스 등록 (백엔드/프론트/cloudflared)
- 백업 스크립트 (SQLite 일일 백업)
- 모니터링 (간단한 헬스체크)

### Phase B ✅ 완료
실전 피드 탭 (Firecrawl + Reddit) → Crawl4AI로 교체 완료

### Phase C — Item Groups + 모듈화 ✅ 완료
- 교차 소스 그룹핑 (arxiv↔github↔hf fingerprint 매칭)
- 대시보드 중복 제거, 상세 siblings 패널
- constants.py/serializers.py 중앙화, grouper 분리

### Phase D — 아르카 에이전트 + Crawl4AI ✅ 완료
- Firecrawl(Docker) → Crawl4AI(pip) 교체
- 아르카 풀 에이전트: Gemma4 tool calling (web_search/crawl_page/finish)
- GitHub 크롤러 검색 쿼리 수정 (괄호 버그, topic qualifier)
- seed_sota.py 가짜 arxiv ID 13개 → 실제 ID 교체

### Phase E — 제보 시스템 + 카테고리 진화

#### E-1: 제보 탭 ✅ 완료
#### E-2: 미분류 태그 + 카테고리 승격 ✅ 완료  
#### E-3: 야간 배치 파이프라인 ✅ 완료

<details>
<summary>Phase E 상세 설계 (접기)</summary>

#### E-1: 제보 탭 ("이거 봐봐")
팀원 누구나 URL/키워드를 던지면 큐에 쌓이고, 야간 배치로 아르카가 조사.

**백엔드:**
- `submissions` 테이블: id, submitted_by, input_type(url/keyword), input_value, status(pending/processing/done/rejected), created_at, processed_at, result_item_id
- `POST /api/submit` — URL 또는 키워드 제출 (인증 불필요, rate limit만)
- `GET /api/submissions` — 제보 목록 + 처리 상태
- `POST /api/admin/process-submissions` — 야간 배치 트리거

**프론트:**
- Submit 탭 (사이드바) — URL 입력 / 키워드 입력 / 제출 히스토리
- 처리 상태 표시: 대기 → 조사중 → 완료(아이템 링크) / 거절(사유)

**야간 배치 흐름:**
```
pending submissions
  → URL이면: Crawl4AI로 크롤 → 아르카가 분석 → items에 삽입 + 스코어링
  → 키워드면: Crawl4AI로 Google 검색 → 상위 결과 크롤 → 아르카 판단 → 유의미한 것만 items에
  → submission.status = done, result_item_id 연결
```

#### E-2: 미분류 태그 + 카테고리 승격

**자동 태그:**
- 아이템이 기존 10개 카테고리 어디에도 안 맞으면 → `uncategorized` 태그
- 아르카가 자유 태그 부여 (예: "comfyui-workflow", "lora-training", "audio-driven")

**승격 감지:**
- `tag_counts` 집계 뷰: 미분류 태그별 아이템 수
- 같은 태그가 N개(기본 5) 이상 쌓이면 → 승격 후보
- `POST /api/admin/suggest-categories` → 아르카가 후보 태그 분석:
  - 태그명 → 한/영 카테고리명 제안
  - 키워드/토픽 자동 생성
  - 기존 카테고리와 중복/포함 관계 판단

**승격 워크플로:**
```
미분류 아이템 쌓임
  → tag_counts에서 threshold 초과 감지
  → 아르카가 카테고리 제안 JSON 생성
  → 관리자 대시보드에 "새 카테고리 제안" 알림
  → 승인 → categories 테이블에 추가 + 기존 아이템 재분류
  → 거절 → 태그 유지, 다음 threshold까지 대기
```

**프론트:**
- Admin 페이지에 "카테고리 제안" 섹션
- 제안 카드: 태그명, 아이템 수, 아르카 추천 이유, 승인/거절 버튼

#### E-3: 야간 배치 파이프라인

**스케줄 (APScheduler):**
```
09:00 KST — 정규 크롤 (arxiv/github/hf/reddit) + 키워드 스코어링
21:00 KST — 야간 배치:
  1. 제보 처리 (submissions 큐)
  2. 아르카 리서처 (미분석 아이템 deep 조사)
  3. 그룹핑 갱신
  4. 미분류 태그 집계 → 승격 후보 감지
  5. (향후) TurboQuant + Gemma4 31B 전환
```

#### E-4: TurboQuant + Gemma4 31B (5090 도입 후)

**목표:** 26B → 31B 업그레이드, KV 캐시 3비트 압축으로 VRAM 절감

**준비 사항:**
- llama.cpp TurboQuant 포크 빌드 또는 Ollama 공식 지원 대기
- `--cache-type-k turbo3 --cache-type-v turbo3` 플래그
- config.yaml에 `OLLAMA_MODEL: gemma4:31b` 변경만으로 전환
- 벤치마크: 26B vs 31B tool calling 정확도/속도 비교

**예상 VRAM (RTX 5090 32GB):**
- 모델 Q4: ~18GB
- KV 캐시 (TurboQuant 3bit, 128K): ~5GB
- 여유: ~9GB

**구현 단계:**
1. Ollama 또는 llama.cpp에서 TurboQuant 공식 지원 확인 (PR 추적)
   - llama.cpp 포크: TheTom, spiritbuun, Aaryan-Kapoor 등
   - 플래그: `--cache-type-k turbo3 --cache-type-v turbo3`
2. RTX 5090에 Gemma4 31B Q4 모델 다운로드
   - `ollama pull gemma4:31b` 또는 GGUF 수동 변환
3. TurboQuant 활성화 후 벤치마크
   - 측정 항목: VRAM 사용량, 초당 토큰, tool calling 성공률
   - 비교: 26B 기본 vs 31B+TurboQuant vs 31B 기본
4. researcher.py 테스트 — 5턴 에이전트 루프에서 KV 캐시 절감 효과 확인
5. config.yaml 변경만으로 전환: `OLLAMA_MODEL: gemma4:31b`
6. 안정성 확인 후 야간 배치에 31B 적용

**연구 기록 (가기연 과제용):**
- TurboQuant 논문: ICLR 2026, Google DeepMind
- 핵심: training-free, data-oblivious vector quantization
- KV 캐시 3.25 bits/value → ~4.9x 압축 (FP16 대비)
- 정확도 손실: 제로 (벤치마크에서 FP16과 동일)
- VFX SOTA Monitor에서의 적용 의의:
  - 에이전트 멀티턴 대화(5+ turns)에서 KV 캐시가 급격히 증가
  - TurboQuant으로 동일 VRAM에서 더 긴 컨텍스트 / 더 큰 모델 운용 가능
  - 실무 VFX 파이프라인에서 로컬 LLM 에이전트의 실용성 입증

</details>

## 검증 방법

### 메인 PC 로컬 테스트
```powershell
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 8001

# Frontend (다른 터미널)
cd frontend
npm install
npm run dev -- --port 3001

# 접속
# http://localhost:3001
```

### AI Cluster PC 워커 테스트
```powershell
cd ai_cluster_worker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# config.yaml 편집: MAIN_PC_URL=http://100.x.x.x:8001
python worker.py --once
```

### 외부 접근 테스트
```powershell
cloudflared tunnel --url http://localhost:3001
# → https://xxxx.trycloudflare.com 확인
```

## Hub 통합 시 (나중)

1. **DB 마이그레이션**: SQLite → glocal30Hub의 Postgres로 이전 (Alembic 덤프/로드)
2. **Frontend**: React 컴포넌트를 Hub 프론트엔드로 이식
3. **Backend**: FastAPI 라우터를 Hub 백엔드에 편입 (prefix `/modules/vfx`)
4. **인증**: Hub의 OAuth JWT를 Depends로 받아 사용
5. **포트 통합**: 3001/8001 → Hub의 3000/8000으로 합침
