"""Gemma 4 prompts for VFX SOTA relevance scoring."""
from __future__ import annotations

import json

CATEGORIES_INFO = """
10개 VFX 카테고리:
1. video_matting (비디오 매팅) — 알파 매트, 트라이맵-프리, 모발 경계
2. video_removal (비디오 리무벌) — 객체/그림자 제거, 인페인팅, VOID
3. face_parsing (페이스 파싱) — 얼굴 세그멘테이션, SegFace, SAM
4. point_tracking (포인트 트래킹) — TAP, CoTracker, TAPIR
5. head_swap (헤드/페이스 스왑) — DFL 대체, Wan-Animate
6. 3dgs (3D 가우시안) — Gaussian Splatting, NeRF, Nerfstudio
7. beauty (뷰티/피부 보정) — face retouching, AuthFace
8. korean_text_edit (한글 텍스트 편집) — Scene Text Editing, STELLAR
9. ref_search (Ref 영상 검색) — CLIP, Qwen-VL-Embedding
10. qc_program (QC) — video quality, IQA, DaVinci API
""".strip()

SYSTEM_PROMPT = f"""당신은 VFX 파이프라인 전문가다. 주어진 논문/저장소/모델/게시물이 다음 카테고리에 얼마나 관련 있는지 판단한다.

{CATEGORIES_INFO}

각 아이템을 평가하여 JSON 배열로 응답해라. 각 요소는 정확히 다음 형식:
{{"id": <아이템번호>, "relevancy_score": <1-10>, "priority": "<P0|P1|P2|P3|WATCH>", "category": "<카테고리_slug>", "reason": "<한국어 1-2문장>"}}

**우선순위 기준:**
- P0: 즉시 검증 필요, SOTA 갱신급, 이번 주 안에 돌려봐야 함
- P1: 이번 달 POC 해볼 만함, 안정적인 SOTA
- P2: 다음 분기 또는 2순위 후보
- P3: 장기 모니터링, 졸업 논문 주제
- WATCH: 참고만, 직접 쓸 일 없음

**점수 기준 (1-10):**
- 9-10: 우리 10개 카테고리에 직접 대응하는 명확한 SOTA
- 7-8: 카테고리에 관련 있고 실무 가치 있음
- 5-6: 간접적으로 관련, 참고 가치 있음
- 3-4: 약한 연관, WATCH 수준
- 1-2: 관련 거의 없음

**category 선택:** 10개 slug 중 가장 적합한 하나. 여러 개 걸쳐도 가장 핵심인 것 하나만 선택.

반드시 JSON 배열만 출력해라. 설명/주석/markdown 금지."""


def build_user_prompt(items: list[dict]) -> str:
    """Build the batched user message containing items to score."""
    parts = ["다음 아이템들을 평가하라:\n"]
    for i, item in enumerate(items, 1):
        parts.append(f"### 아이템 {i}")
        parts.append(f"소스: {item.get('source', '?')}")
        parts.append(f"제목: {item.get('title', '(제목 없음)')}")
        if item.get("category_slugs"):
            parts.append(f"키워드 매칭 카테고리: {', '.join(item['category_slugs'])}")
        abstract = (item.get("abstract") or "").strip()
        if abstract:
            parts.append(f"내용: {abstract[:800]}")
        parts.append("")
    parts.append("JSON 배열로만 응답:")
    return "\n".join(parts)


def parse_response(raw: str, items: list[dict]) -> list[dict]:
    """Parse Gemma's JSON response, tolerating common mistakes.

    Returns list of update dicts matching the backend's ScoreUpdate schema:
      [{"id": int, "llm_score": int, "llm_reason": str, "priority": str}, ...]
    """
    raw = (raw or "").strip()

    # Strip common wrappers: markdown fences, leading text
    if raw.startswith("```"):
        # Remove first line (```json or ```) and last line (```)
        lines = raw.splitlines()
        if len(lines) >= 2:
            lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            raw = "\n".join(lines)

    # Find the first `[` and last `]`
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []

    json_text = raw[start : end + 1]

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        # Attempt to repair trailing commas or missing brackets
        fixed = json_text.replace(",\n]", "\n]").replace(",]", "]")
        try:
            parsed = json.loads(fixed)
        except json.JSONDecodeError:
            return []

    if not isinstance(parsed, list):
        return []

    updates: list[dict] = []
    for idx, entry in enumerate(parsed):
        if not isinstance(entry, dict):
            continue

        # Map back to real item ID by position (Gemma uses 1-based "id" within prompt)
        prompt_id = entry.get("id")
        real_item = None
        if isinstance(prompt_id, int) and 1 <= prompt_id <= len(items):
            real_item = items[prompt_id - 1]
        elif idx < len(items):
            real_item = items[idx]

        if not real_item:
            continue

        score = entry.get("relevancy_score") or entry.get("score") or 0
        try:
            score = int(score)
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(10, score))

        priority = entry.get("priority") or ""
        if priority not in ("P0", "P1", "P2", "P3", "WATCH"):
            # Infer from score if missing/invalid
            if score >= 9:
                priority = "P0"
            elif score >= 7:
                priority = "P1"
            elif score >= 5:
                priority = "P2"
            elif score >= 3:
                priority = "P3"
            else:
                priority = "WATCH"

        reason = str(entry.get("reason") or "")[:2000]
        category = entry.get("category") or ""
        if category:
            reason = f"[{category}] {reason}".strip()

        updates.append(
            {
                "id": real_item["id"],
                "llm_score": score,
                "llm_reason": reason,
                "priority": priority,
            }
        )

    return updates
