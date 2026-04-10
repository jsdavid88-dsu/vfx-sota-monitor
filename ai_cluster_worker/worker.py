"""AI Cluster Worker — Gemma 4 26B를 사용한 배치 스코어링.

Phase 3에서 완성 예정. 현재는 스텁.

사용법:
    python worker.py --once                  # 1회 실행
    python worker.py --interval 300          # 5분마다 폴링
"""
import argparse
import sys
import time
from pathlib import Path

import httpx
import yaml

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"[ERROR] config.yaml not found. Copy config.example.yaml first.", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_pending(cfg: dict) -> list[dict]:
    """메인 PC에서 스코어링 대기 아이템 가져오기."""
    headers = {"X-Admin-Token": cfg["ADMIN_TOKEN"]}
    url = f"{cfg['MAIN_PC_URL']}/api/admin/pending-scoring"
    try:
        r = httpx.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch pending: {e}", file=sys.stderr)
        return []


def score_items(items: list[dict], cfg: dict) -> list[dict]:
    """Phase 3에서 실제 Gemma 호출 구현.

    현재는 스텁으로 모든 아이템에 score=0 반환.
    """
    print(f"[STUB] Would score {len(items)} items via Gemma 4 26B")
    return [
        {
            "id": item["id"],
            "llm_score": 0,
            "llm_reason": "[STUB] Phase 3에서 구현",
            "priority": None,
        }
        for item in items
    ]


def post_updates(updates: list[dict], cfg: dict) -> bool:
    """스코어 업데이트를 메인 PC로 전송."""
    if not updates:
        return True
    headers = {"X-Admin-Token": cfg["ADMIN_TOKEN"]}
    url = f"{cfg['MAIN_PC_URL']}/api/admin/score-update"
    try:
        r = httpx.post(url, headers=headers, json=updates, timeout=30)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to post updates: {e}", file=sys.stderr)
        return False


def run_once(cfg: dict) -> int:
    """1회 실행. 처리한 아이템 수 반환."""
    print(f"[INFO] Connecting to {cfg['MAIN_PC_URL']}")
    pending = fetch_pending(cfg)
    print(f"[INFO] Fetched {len(pending)} pending items")

    if not pending:
        return 0

    updates = score_items(pending, cfg)
    success = post_updates(updates, cfg)
    if success:
        print(f"[OK] Updated {len(updates)} items")
        return len(updates)
    return 0


def main():
    parser = argparse.ArgumentParser(description="VFX SOTA AI Cluster Worker")
    parser.add_argument("--once", action="store_true", help="1회 실행 후 종료")
    parser.add_argument("--interval", type=int, default=0, help="폴링 간격(초), 0이면 1회만")
    args = parser.parse_args()

    cfg = load_config()

    if args.once or args.interval == 0:
        run_once(cfg)
    else:
        print(f"[INFO] Polling every {args.interval}s (Ctrl+C to stop)")
        try:
            while True:
                run_once(cfg)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[INFO] Stopped")


if __name__ == "__main__":
    main()
