# Firecrawl 셀프 호스팅 가이드

VFX SOTA Monitor의 **피드 기능**에서 웹 검색/스크래핑에 사용합니다. 뉴스, 블로그, 튜토리얼 등을 긁어오는 역할.

## 왜 셀프호스팅?

- 무료, 크레딧 제한 없음
- Playwright로 JS 무거운 사이트도 긁음
- 팀 프로덕션에서 쿼터 걱정 없이 매일 수백 페이지 수집 가능

## 요구사항

- Docker Desktop (또는 Docker Engine) 설치
- 디스크 약 2GB (이미지)
- RAM 2-4GB 상시 사용
- 이 프로젝트의 `backend`와 **다른 포트** 사용 (3002, 6379, 3100)

## 설치

### 1단계: Docker Desktop 설치
https://www.docker.com/products/docker-desktop 에서 Windows용 다운로드

### 2단계: Firecrawl 시작
```powershell
cd G:\다른 컴퓨터\AIClusterPC\DSU\2026_1\가기연\sota-monitor
docker compose -f docker/firecrawl-compose.yml up -d
```

첫 실행 시 이미지 다운로드 (약 1GB, 5-10분)

### 3단계: 헬스체크
```powershell
curl http://localhost:3002/v1/health
```
응답이 오면 성공. `{"status":"ok"}` 같은 형태.

### 4단계: 테스트 검색
```powershell
curl -X POST http://localhost:3002/v1/search ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"comfyui workflow tutorial\", \"limit\": 5}"
```

## 관리

### 중지
```powershell
docker compose -f docker/firecrawl-compose.yml down
```

### 로그 확인
```powershell
docker compose -f docker/firecrawl-compose.yml logs -f api
```

### 업데이트
```powershell
docker compose -f docker/firecrawl-compose.yml pull
docker compose -f docker/firecrawl-compose.yml up -d
```

## 트러블슈팅

### 포트 충돌
기본 포트 3002가 이미 쓰이면 `firecrawl-compose.yml`의 api 서비스 ports를 변경:
```yaml
ports:
  - "3003:3002"
```
그 후 `backend/.env`의 `FIRECRAWL_BASE_URL=http://localhost:3003`

### 이미지 pull 실패
`trieve/firecrawl` 이미지가 공개되지 않았거나 이름이 바뀐 경우,
공식 저장소 https://github.com/mendableai/firecrawl 에서 직접 빌드:
```powershell
git clone https://github.com/mendableai/firecrawl.git
cd firecrawl
docker compose up -d
```

### 메모리 부족
Docker Desktop → Settings → Resources → Memory를 최소 4GB로

## 대안: Firecrawl 없이 쓰기

VFX SOTA Monitor는 Firecrawl이 **없어도 동작**합니다. 이 경우:
- Reddit 소스만 사용
- 웹 검색 기반 피드 아이템은 수집 안 됨
- 기능 축소 모드

Backend의 `.env`에 `FIRECRAWL_BASE_URL`을 비워두면 자동으로 Reddit만 씁니다.
