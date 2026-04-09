# VFX SOTA Monitor 구현 플랜

## Context
Red Cat Gang VFX팀의 60+ AI 모델 SOTA 로드맵을 자동 모니터링하는 시스템 구축. ArxivDigest를 베이스로 arXiv + GitHub + HuggingFace를 매일 스캔하고, Gemma 4 26B(Ollama)로 관련성을 판단하여 일일 리포트 생성 및 로드맵 자동 업데이트.

## 핵심 결정

1. **ArxivDigest 포크가 아닌 새 프로젝트**: 원본이 `openai==0.27.8` (폐기 API) 사용, 스크래핑 로직(40줄)만 차용
2. **GitHub Actions는 keyword_only 모드**: GPU 없으므로 키워드 필터링만, LLM 스코어링은 로컬 전용
3. **단일 일일 마크다운 리포트**: 10개 카테고리 섹션으로 구분
4. **로드맵은 append-only**: 수동 편집 보존, 날짜별 섹션 추가

## 프로젝트 구조

```
vfx-sota-monitor/               ← G:/다른 컴퓨터/.../가기연/sota-monitor/vfx-sota-monitor/
├── config.yaml                  # 10개 VFX 카테고리 + 키워드 + 설정
├── requirements.txt
├── .env.example
├── .github/workflows/
│   └── daily_monitor.yaml       # 매일 01:00 UTC (10:00 KST) 크론
├── src/
│   ├── main.py                  # 오케스트레이터
│   ├── config.py                # 설정 로더
│   ├── sources/
│   │   ├── arxiv.py             # arXiv 스크래핑 (ArxivDigest에서 차용)
│   │   ├── github_source.py     # GitHub 레포 검색 (PyGithub)
│   │   └── huggingface.py       # HuggingFace 모델 검색
│   ├── scoring/
│   │   ├── keyword.py           # 키워드 매칭 (GPU 불필요)
│   │   └── llm.py               # Ollama Gemma 4 26B 스코어링
│   ├── storage/
│   │   └── db.py                # SQLite 중복 방지
│   └── reporting/
│       ├── daily_report.py      # 일일 마크다운 생성
│       └── roadmap_updater.py   # 로드맵 자동 업데이트
├── data/
│   ├── seen.db                  # SQLite (gitignored)
│   └── reports/                 # 일일 리포트 (커밋됨)
├── roadmap.md                   # 마스터 로드맵
└── tests/
```

## 데이터 흐름

```
매일 크론 (GitHub Actions 또는 로컬)
  │
  ▼
소스 수집: arXiv(BS4) + GitHub(PyGithub) + HuggingFace(hf_hub)
  │
  ▼
카테고리별 처리 (10개 VFX 카테고리 루프):
  키워드 필터 → SQLite 중복 제거 → [LLM 스코어링 (로컬만)]
  │
  ▼
출력: 일일 리포트 .md + 로드맵 append (score ≥ 8만)
  │
  ▼
GitHub Actions: git commit + push
```

## 주요 모듈 상세

### 1. `sources/arxiv.py`
- ArxivDigest `download_new_papers.py` 11-48줄 BeautifulSoup 파서 차용
- `fetch_new_papers(field="cs") -> list[dict]`
- 표준화 스키마: `{source, id, title, authors, abstract, url, date, subjects}`

### 2. `sources/github_source.py`
- PyGithub로 카테고리별 키워드+토픽 검색
- `fetch_new_repos(keywords, topics, lookback_days=1) -> list[dict]`
- 레이트 리밋: 카테고리간 2.5초 sleep

### 3. `sources/huggingface.py`
- `HfApi().list_models(search=keyword, sort="lastModified")`
- `fetch_new_models(keywords, tags, lookback_days=1) -> list[dict]`

### 4. `scoring/keyword.py`
- 제목+초록에서 키워드 매칭 (word boundary regex)
- `score_by_keywords(items, keywords) -> list[dict]` — keyword_score 필드 추가

### 5. `scoring/llm.py`
- `openai.OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")`
- 모델: `gemma4:26b`, 배치 4개씩, temperature 0.3
- 프롬프트: VFX 도메인 특화 관련성 판단
- `score_by_llm(items, category, config) -> list[dict]` — llm_score 필드 추가

### 6. `storage/db.py`
- SQLite 3개 테이블 (papers, repos, models)
- 복합키: `(source, id, category)` — 같은 아이템이 여러 카테고리에 나올 수 있음
- `filter_unseen(conn, items) -> list[dict]`

### 7. `reporting/daily_report.py`
- 한국어 일일 마크다운 — 카테고리별 테이블
- `data/reports/YYYY-MM-DD.md`

### 8. `reporting/roadmap_updater.py`
- score ≥ 8인 아이템만 `roadmap.md` 하단에 날짜 섹션 append

## config.yaml 카테고리 (10개)

| ID | 이름 | 핵심 키워드 |
|----|------|-------------|
| video_matting | 비디오 매팅 | video matting, alpha matte, trimap-free |
| video_removal | 비디오 리무벌 | video inpainting, object removal, VOID |
| face_parsing | 페이스 파싱 | face parsing, face segmentation, SegFace |
| point_tracking | 포인트 트래킹 | point tracking, TAP, CoTracker |
| head_swap | 헤드 스왑 | head swap, face swap, face reenactment |
| 3dgs | 3D 가우시안 | gaussian splatting, 3DGS, neural rendering |
| beauty | 뷰티 보정 | face restoration, skin retouching, beauty |
| korean_text_edit | 한글 텍스트 | scene text editing, korean OCR, hangul |
| ref_search | Ref 검색 | image retrieval, visual search, CLIP |
| qc_program | QC 프로그램 | video quality, artifact detection, IQA |

## GitHub Actions Workflow

- 크론: `0 1 * * 1-5` (월-금 10:00 KST)
- `python src/main.py --mode keyword_only`
- seen.db는 `actions/cache`로 유지
- 리포트를 자동 커밋+푸시
- 리포 주인: `jsdavid88-dsu`

## 구현 순서

| Phase | 기간 | 작업 |
|-------|------|------|
| **1. MVP** | Day 1-2 | config + arxiv 스크래핑 + 키워드 스코어링 + SQLite + 리포트 + main.py |
| **2. 소스 확장** | Day 3-4 | GitHub + HuggingFace 소스 추가 |
| **3. LLM** | Day 5 | Ollama Gemma 4 연동 + 프롬프트 튜닝 |
| **4. 마무리** | Day 6 | 로드맵 업데이터 + 풀 config + 에러처리 |
| **5. 배포** | Day 7 | GitHub Actions + 리포 세팅 + 테스트 |

## 참조 파일 (ArxivDigest에서 차용)

- `ArxivDigest-base/src/download_new_papers.py:11-48` — BS4 스크래핑 코어
- `ArxivDigest-base/src/relevancy.py:20-35` — 프롬프트 인코딩 패턴
- `ArxivDigest-base/src/relevancy.py:38-78` — 응답 파싱 패턴
- `ArxivDigest-base/src/relevancy_prompt.txt` — 프롬프트 템플릿 참조

## 검증 방법

1. `python src/main.py --mode keyword_only` — 키워드만으로 전체 파이프라인 테스트
2. `python src/main.py --mode ollama` — Gemma 4 로컬 스코어링 테스트
3. `data/reports/YYYY-MM-DD.md` 파일 확인 — 카테고리별 결과 존재 여부
4. `roadmap.md` 하단 — append 정상 동작 확인
5. GitHub Actions `workflow_dispatch` — 수동 실행 후 커밋 확인
6. 2회차 실행 시 중복 아이템 없는지 확인 (SQLite dedup)

## 의존성

```
PyYAML>=6.0
beautifulsoup4>=4.12
openai>=1.0
PyGithub>=2.0
huggingface-hub>=0.20
tqdm>=4.65
pytz>=2023.3
python-dotenv>=1.0
```
