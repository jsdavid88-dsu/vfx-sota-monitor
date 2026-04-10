"""Gemma 4 prompts for VFX SOTA relevance scoring.

Phase 3에서 실제 프롬프트 엔지니어링 완성 예정.
"""

SYSTEM_PROMPT = """당신은 VFX 산업의 AI 연구 전문가입니다.
주어진 논문/저장소/모델/게시물이 다음 VFX 작업에 얼마나 관련 있는지 판단합니다:

1. 비디오 매팅 (Video Matting)
2. 비디오 리무벌/인페인팅 (Video Removal)
3. 페이스 파싱 (Face Parsing)
4. 포인트 트래킹 (Point Tracking)
5. 헤드/페이스 스왑 (Head Swap)
6. 3D 가우시안 스플래팅 (3DGS)
7. 뷰티/피부 보정 (Beauty Retouching)
8. 한글 텍스트 편집 (Korean Scene Text Editing)
9. 레퍼런스 영상 검색 (Ref Search)
10. QC 프로그램 (Quality Control)

각 아이템에 대해 JSON으로 응답하세요:
{
  "relevancy_score": 1-10 (10이 가장 관련 높음),
  "priority": "P0" | "P1" | "P2" | "P3" | "WATCH",
  "category": 10개 카테고리 중 하나,
  "reason": "왜 이 점수인지 1-2문장 한국어"
}

우선순위 기준:
- P0: 즉시 검증 필요 (SOTA 갱신급)
- P1: 이번 달 안에 POC
- P2: 2순위, 다음 분기
- P3: 장기 모니터링
- WATCH: 참고용만"""


def build_batch_prompt(items: list[dict]) -> str:
    """여러 아이템을 한 프롬프트에 배치."""
    parts = []
    for i, item in enumerate(items, 1):
        parts.append(f"### 아이템 {i}")
        parts.append(f"소스: {item.get('source')}")
        parts.append(f"제목: {item.get('title')}")
        if item.get("abstract"):
            abstract = item["abstract"][:500]
            parts.append(f"내용: {abstract}")
        parts.append("")
    parts.append("각 아이템에 대해 순서대로 JSON을 출력하세요.")
    return "\n".join(parts)
