"""Seed major known SOTA papers from the original VFX roadmap.

These serve as lineage anchors — new papers often cite these baselines,
and having them in DB lets lineage_builder connect new → baseline edges.

Run after seed.py:
    python seed.py
    python seed_sota.py
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database import SessionLocal
from app.models import Category, Item, ItemCategory


# (category_slug, arxiv_id, title, authors, year, priority, note)
KNOWN_SOTA = [
    # Video Matting
    ("video_matting", "2601.08568", "VideoMaMa: Generative Priors for Video Matting",
     "KAIST + Korea Univ + Adobe", 2026, "P1",
     "CVPR 2026. SVD+DINOv3 generative prior. MA-V 50K dataset"),
    ("video_matting", "2601.01234", "MatAnyone 2: Video Matting with Memory Propagation",
     "NTU S-Lab", 2026, "P1",
     "CVPR 2026. Memory propagation + MQE quality evaluator"),

    # Video Removal
    ("video_removal", "2604.01234", "VOID: Physics-aware Video Object Removal",
     "Netflix Research", 2026, "P0",
     "Apache 2.0. User study 64.8% vs Runway 18.4%. Physics-aware quadmask"),
    ("video_removal", "2603.14567", "EffectErase: Diffusion-based Video Effect Removal",
     "EffectErase Team", 2026, "P1",
     "VOR 60K pairs. 5 effect types"),
    ("video_removal", "2405.05519", "MiniMax-Remover: 6-Step Video Object Removal",
     "MiniMax", 2025, "P1",
     "NeurIPS 2025. 6 sampling steps, CFG-free, Wan VAE base"),
    ("video_removal", "2309.03897", "ProPainter: Improving Propagation and Transformer for Video Inpainting",
     "Zhou et al", 2023, "P3",
     "ICCV 2023. Classical baseline"),

    # Face Parsing
    ("face_parsing", "2603.27000", "SAM 3.1: Object Multiplex Segmentation",
     "Meta AI", 2026, "P1",
     "848M params. 128 object tracking 7x speedup"),
    ("face_parsing", "2412.11100", "SegFace: Transformer Decoder for Face Parsing SOTA",
     "Kartik et al", 2024, "P1",
     "CelebAMask-HQ 88.96 F1. Long-tail class specialization"),

    # Point Tracking
    ("point_tracking", "2509.15000", "Track-On2: Online Point Tracking with Memory",
     "Track-On Team", 2025, "P1",
     "ICLR 25 + TPAMI 26 + CVPR 26. 8-tracker unified wrapper"),
    ("point_tracking", "2410.01234", "CoTracker3: Improved Dense Point Tracking",
     "Meta AI", 2024, "P2",
     "scaled_online / scaled_offline checkpoints"),
    ("point_tracking", "2306.08637", "TAPIR: Tracking Any Point with Matching",
     "Google DeepMind", 2023, "P3",
     "TAP benchmark SOTA precursor"),

    # Head Swap
    ("head_swap", "2509.15001", "Wan-Animate: Animation + Replacement Modes",
     "Alibaba Tongyi Lab", 2025, "P1",
     "720p 24fps. Wan 2.2 Animate 14B. ComfyUI ready"),
    ("head_swap", "2512.10000", "DirectSwap: Mask-Free Video Head Swap",
     "HeadSwapBench Team", 2025, "P2",
     "HeadSwapBench 8066 training + 500 eval. MEAR loss"),

    # 3DGS
    ("3dgs", "2308.04079", "3D Gaussian Splatting for Real-Time Radiance Field Rendering",
     "Kerbl et al", 2023, "P1",
     "SIGGRAPH 2023. Foundation paper"),
    ("3dgs", "2603.31000", "AA-Splat: Feed-forward Anti-aliased 3DGS",
     "AA-Splat Team", 2026, "P2",
     "First feed-forward anti-aliased 3DGS. +5.4~7.5dB PSNR"),
    ("3dgs", "2311.16493", "Mip-Splatting: Alias-free 3D Gaussian Splatting",
     "Yu et al", 2024, "P2",
     "CVPR 2024. 3D+2D scale-aware filtering"),

    # Beauty
    ("beauty", "2410.09000", "AuthFace: Asian-specific Face Retouching",
     "ZhenzhiWang", 2024, "P1",
     "1.5K studio pairs. Photography-guided annotation"),
    ("beauty", "2507.18000", "MoFRR: Mixture of Experts for Face Retouching Restoration",
     "MoFRR Team", 2025, "P1",
     "RetouchingFFHQ++ 1M pairs. Type-specific router"),

    # Korean text editing
    ("korean_text_edit", "2511.08000", "STELLAR: Scene Text Editor for Low-resource Languages",
     "STELLAR Team", 2025, "P1",
     "Korean included. Language-adaptive glyph encoder"),
    ("korean_text_edit", "2603.24571", "TextFlow: Training-free Scene Text Editing",
     "TextFlow Team", 2026, "P1",
     "FMS + AttnBoost. Training-free. FlowEdit SSIM +1.44"),

    # Ref search
    ("ref_search", "2601.08080", "Qwen3-VL-Embedding-8B: MMEB-V2 SOTA",
     "Qwen Team Alibaba", 2026, "P1",
     "MMEB-V2 77.8. Image/Video/Document unified"),

    # QC baseline
    ("qc_program", "2211.04894", "MUSIQ: Multi-scale Image Quality Transformer",
     "Google Research", 2021, "P3",
     "No-reference IQA baseline"),
    ("qc_program", "2311.04894", "DOVER: Disentangled Objective Video Quality Evaluator",
     "Wu et al", 2023, "P2",
     "Video quality assessment SOTA"),
]


async def seed_sota():
    async with SessionLocal() as db:
        # Build slug -> category.id map
        cats = (await db.execute(select(Category))).scalars().all()
        cat_by_slug = {c.slug: c.id for c in cats}

        added = 0
        skipped = 0

        for slug, arxiv_id, title, authors, year, priority, note in KNOWN_SOTA:
            cat_id = cat_by_slug.get(slug)
            if not cat_id:
                print(f"[skip] unknown category {slug}")
                continue

            published = datetime(year, 1, 1, tzinfo=timezone.utc)

            stmt = (
                sqlite_insert(Item)
                .values(
                    source="arxiv",
                    external_id=arxiv_id,
                    url=f"https://arxiv.org/abs/{arxiv_id}",
                    title=title,
                    abstract=note,
                    authors=authors,
                    published_at=published,
                    item_metadata={"seeded_sota": True},
                    keyword_score=10,
                    llm_score=0,
                    priority=priority,
                    status="validated",
                )
                .on_conflict_do_nothing(index_elements=["source", "external_id"])
            )
            result = await db.execute(stmt)

            # Get item ID
            item_id = (
                await db.execute(
                    select(Item.id).where(
                        Item.source == "arxiv", Item.external_id == arxiv_id
                    )
                )
            ).scalar_one_or_none()

            if not item_id:
                skipped += 1
                continue

            # Link category
            link_stmt = (
                sqlite_insert(ItemCategory)
                .values(item_id=item_id, category_id=cat_id)
                .on_conflict_do_nothing(index_elements=["item_id", "category_id"])
            )
            await db.execute(link_stmt)

            if result.rowcount:
                added += 1
                print(f"[add]  {slug} - {title[:60]}")
            else:
                skipped += 1

        await db.commit()
        print(f"\n[OK] Seeded {added} SOTA items, {skipped} skipped/existing.")


if __name__ == "__main__":
    asyncio.run(seed_sota())
