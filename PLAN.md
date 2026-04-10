# VFX SOTA Monitor — 최종 구현 플랜 v2

## Context

Red Cat Gang VFX팀(20-30명)이 매일 AI 관련 SOTA를 자동 추적하는 시스템. **나중에 [glocal30Hub](https://github.com/jsdavid88-dsu/glocal30Hub) 통합 포털에 모듈로 편입 예정**이므로 스택을 완전히 일치시킴.

## 확정된 결정사항

1. ✅ **스택**: glocal30Hub와 100% 동일 (React 19 + FastAPI + PostgreSQL)
2. ✅ **인증**: 자체 구현 X → 나중에 Hub의 OAuth 재사용
3. ✅ **호스팅**: 같은 서버 (Docker Compose 패턴 동일)
4. ✅ **댓글**: DB 스키마는 지금 준비, UI는 나중 phase
5. ✅ **개발 방식**: 백엔드 + 프론트엔드 병렬
6. ✅ **데이터**: 메타데이터만 (코드/논문 본문 X, 링크만)
7. ✅ **소스**: arXiv, GitHub, HuggingFace, Reddit(PRAW), X(fxtwitter)
8. ✅ **LLM**: Gemma 4 26B via Ollama (RTX 4090 로컬)

## 기술 스택 (glocal30Hub 일치)

### Frontend
- React 19 + Vite 7 + TypeScript 5.9
- Tailwind CSS 4 + @tailwindcss/vite
- react-router-dom 7
- 추가: @tanstack/react-query, reactflow, recharts, lucide-react

### Backend
- FastAPI 0.115 + uvicorn
- SQLAlchemy 2 async + asyncpg + Alembic
- pydantic 2 + pydantic-settings
- 추가: apscheduler, beautifulsoup4, PyGithub, huggingface-hub, praw, openai>=1.0

### Infrastructure
- PostgreSQL 16 (Docker)
- Docker Compose (glocal30Hub 패턴)
- Ollama (호스트, RTX 4090)

## 프로젝트 구조

```
vfx-sota-monitor/
├── docker-compose.yml
├── .env.example
├── README.md
├── PLAN.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── seed.py
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models/
│       │   ├── category.py
│       │   ├── item.py
│       │   ├── lineage.py
│       │   └── comment.py
│       ├── schemas/
│       ├── routers/
│       │   ├── categories.py
│       │   ├── items.py
│       │   ├── lineage.py
│       │   ├── comments.py
│       │   ├── stats.py
│       │   └── search.py
│       ├── sources/
│       │   ├── base.py
│       │   ├── arxiv_src.py
│       │   ├── github_src.py
│       │   ├── huggingface_src.py
│       │   ├── reddit_src.py
│       │   └── x_fxtwitter.py
│       ├── scoring/
│       │   ├── keyword.py
│       │   └── llm_ollama.py
│       └── tasks/
│           ├── scheduler.py
│           └── daily_monitor.py
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
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
│       ├── components/
│       └── types/
│
└── .github/workflows/
    └── daily_monitor.yaml
```

## DB 스키마 (핵심)

- `categories` — 10개 VFX 카테고리 (slug, name_ko, keywords, github_topics, subreddits, x_accounts)
- `items` — 통합 아이템 (source: arxiv/github/huggingface/reddit/x), keyword_score, llm_score, priority
- `item_categories` — M:N 연결
- `lineage_edges` — 기술 계보 (parent_id, child_id, relationship)
- `comments` — Phase 2 UI용 (스키마만 준비)
- `crawl_runs` — 크롤 이력

## 프론트엔드 페이지

1. `/` — 대시보드 (카테고리 그리드 + 이번 주 하이라이트)
2. `/category/:slug` — 카테고리 상세 (SOTA + 타임라인 + 아이템 리스트)
3. `/item/:id` — 아이템 상세 (메타 + 관련 + 소셜 반응)
4. `/timeline` — 전체 타임라인 (10개 레인)
5. `/graph` — 기술 계보 그래프 (reactflow)

## 구현 Phase (병렬 개발)

| Phase | 내용 |
|-------|------|
| **1. 뼈대 + MVP** | Docker + FastAPI + Vite + 기본 라우트 + Dashboard (가짜 데이터) + 10카테고리 시드 |
| **2. 데이터 수집** | 5개 소스 + 키워드 스코어링 + APScheduler |
| **3. LLM 통합** | Ollama Gemma 4 26B + 프롬프트 + 자동 분류/우선순위 |
| **4. 프론트 고도화** | CategoryDetail + ItemDetail + 필터 + 검색 + Timeline |
| **5. 기술 계보** | Semantic Scholar + reactflow + LineageGraph |
| **6. 댓글 UI + 마무리** | 댓글 + 에러 처리 + Hub 통합 어댑터 |

## Hub 통합 준비

- **인증 어댑터**: `backend/app/auth.py`에 JWT 검증만, 발급은 Hub
- **DB**: 같은 Postgres에 `vfx_` 접두사 테이블로 편입 가능
- **프론트**: Hub 내 탭으로 컴포넌트 이식 가능하도록 독립성 유지
- **API**: Hub의 `/modules/vfx/*` 프록시로 라우팅 가능
