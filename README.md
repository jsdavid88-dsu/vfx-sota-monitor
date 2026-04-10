# VFX SOTA Monitor

Red Cat Gang VFX팀을 위한 AI SOTA 자동 모니터링 시스템.

## 개요

매일 arXiv, GitHub, HuggingFace, Reddit, X에서 VFX 관련 최신 연구/모델/저장소를 자동 수집하고, 로컬 LLM(Gemma 4 26B)으로 관련성을 판단하여 웹 대시보드에 표시합니다.

**통합 예정**: [glocal30Hub](https://github.com/jsdavid88-dsu/glocal30Hub) 통합 포털에 모듈로 편입.

## 스택

- **Frontend**: React 19 + Vite 7 + TypeScript + Tailwind CSS 4
- **Backend**: FastAPI + SQLAlchemy 2 async + PostgreSQL + Alembic
- **LLM**: Gemma 4 26B (Ollama, 로컬 RTX 4090)
- **Infra**: Docker Compose

## 추적 카테고리 (10개)

| ID | 한글명 | 주요 기술 |
|----|--------|-----------|
| video_matting | 비디오 매팅 | VideoMaMa, MatAnyone 2 |
| video_removal | 비디오 리무벌 | VOID, EffectErase |
| face_parsing | 페이스 파싱 | SAM 3.1, SegFace |
| point_tracking | 포인트 트래킹 | Track-On, CoTracker3 |
| head_swap | 헤드 스왑 | Wan-Animate, DirectSwap |
| 3dgs | 3D 가우시안 스플래팅 | Nerfstudio, AA-Splat |
| beauty | 뷰티 / 피부 보정 | AuthFace, MoFRR |
| korean_text_edit | 한글 텍스트 편집 | STELLAR, TextFlow |
| ref_search | Ref 영상 검색 | Qwen3-VL-Embedding |
| qc_program | QC 프로그램 | OpenCV, DaVinci API |

## 실행

```bash
# 1. 환경 변수 세팅
cp .env.example .env
# .env 파일 편집

# 2. Ollama 실행 (호스트에서)
ollama pull gemma4:26b
ollama serve

# 3. Docker Compose 실행
docker compose up -d

# 4. DB 마이그레이션
docker compose exec backend alembic upgrade head

# 5. 시드 데이터 (10개 카테고리)
docker compose exec backend python seed.py

# 6. 접속
# Frontend: http://localhost:3001
# Backend API: http://localhost:8001/docs
```

## 구조

```
vfx-sota-monitor/
├── backend/       # FastAPI + SQLAlchemy
├── frontend/      # React 19 + Vite
├── docker-compose.yml
└── PLAN.md        # 상세 구현 플랜
```

## 라이선스

Internal use — Red Cat Gang / Dongseo University
