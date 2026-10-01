"""Audit real BDD100K validation split for multi-class CAPTCHA candidates."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from challenge_engine.datasets.bdd100k import (
    CLASS_PROFILES,
    CONFUSABLE_DISTRACTORS,
    load_bdd100k_dataset,
)


def run_audit() -> dict[str, dict[str, int]]:
    ds = load_bdd100k_dataset()
    classes = ["motorcycle", "bicycle", "bus", "truck", "pedestrian", "traffic light"]

    results: dict[str, dict[str, int]] = {}
    for cls in classes:
        profile = CLASS_PROFILES[cls]
        stats = {
            "pos_frames": 0,
            "easy_pos": 0,
            "hard_pos": 0,
            "microscopic_only": 0,
            "borderline_small": 0,
            "clear_neg": 0,
            "confusable_neg": 0,
            "ambiguous_neg": 0,
            "total_neg": 0,
        }
        for frame in ds.frames:
            eval_res = frame.evaluate_for_target(cls, class_profile=profile)
            if eval_res["is_positive"]:
                stats["pos_frames"] += 1
                if eval_res["is_easy_positive"]:
                    stats["easy_pos"] += 1
                elif eval_res["is_hard_positive"]:
                    stats["hard_pos"] += 1
                elif eval_res["is_microscopic_positive"]:
                    stats["microscopic_only"] += 1
                elif eval_res["is_borderline_small_positive"]:
                    stats["borderline_small"] += 1
            else:
                stats["total_neg"] += 1
                if eval_res["is_clear_negative"]:
                    stats["clear_neg"] += 1
                if eval_res["is_confusable_negative"]:
                    stats["confusable_neg"] += 1
                if eval_res["is_ambiguous_negative"]:
                    stats["ambiguous_neg"] += 1
        results[cls] = stats

    print(f"Total BDD100K validation frames evaluated: {len(ds.frames)}\n")
    print("=" * 75)
    print(f"{'CLASS':<15} | {'POSITIVE':<9} | {'EASY':<8} | {'HARD':<8} | {'REJECTED':<9} | {'CLEAR NEG':<10}")
    print("=" * 75)
    for cls, s in results.items():
        prof = CLASS_PROFILES[cls]
        rejected = s["microscopic_only"] + s["borderline_small"]
        print(
            f"{cls.upper():<15} | "
            f"{s['pos_frames']:<9} | "
            f"{s['easy_pos']:<8} | "
            f"{s['hard_pos']:<8} | "
            f"{rejected:<9} | "
            f"{s['clear_neg']:<10}"
        )
    print("=" * 75)
    print()

    for cls, s in results.items():
        prof = CLASS_PROFILES[cls]
        print(f"--- Class Profile: {cls.upper()} ({prof.description}) ---")
        print(f"  Positive frames:        {s['pos_frames']:5d}")
        print(f"    - Easy candidates:    {s['easy_pos']:5d} (min_dim >= {prof.min_easy_bbox_dim}px or max_dim >= {prof.min_easy_bbox_max_dim}px)")
        print(f"    - Hard candidates:    {s['hard_pos']:5d} (min_dim >= {prof.min_usable_bbox_dim}px and budget satisfied)")
        print(f"    - Microscopic/border: {s['microscopic_only'] + s['borderline_small']:5d} (rejected)")
        print(f"  Negative frames:        {s['total_neg']:5d}")
        print(f"    - Clear negatives:    {s['clear_neg']:5d}")
        print(f"    - Confusable distrac: {s['confusable_neg']:5d} (distractors: {prof.confusable_distractors})")
        print(f"    - Ambiguous rejected: {s['ambiguous_neg']:5d}")
        print(f"  Rendered target target: Level 1 >= {prof.min_rendered_max_dim_l1}px, Level 2A >= {prof.min_rendered_max_dim_l2a}px")
        print()

    return results


if __name__ == "__main__":
    run_audit()
