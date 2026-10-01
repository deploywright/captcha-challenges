import sys
from pathlib import Path
from challenge_engine.datasets.bdd100k import load_bdd100k_dataset, CONFUSABLE_DISTRACTORS

ds = load_bdd100k_dataset()
classes = ['motorcycle', 'bicycle', 'bus', 'truck', 'traffic light', 'pedestrian']

results = {}
for cls in classes:
    stats = {
        'pos_frames': 0,
        'easy_pos': 0,
        'hard_pos': 0,
        'microscopic_only': 0,
        'borderline_small': 0,
        'clear_neg': 0,
        'ambiguous_neg': 0,
        'confusable_neg': 0,
        'total_neg': 0,
    }
    for frame in ds.frames:
        eval_res = frame.evaluate_for_target(cls)
        if eval_res['is_positive']:
            stats['pos_frames'] += 1
            if eval_res['is_easy_positive']:
                stats['easy_pos'] += 1
            if eval_res['is_hard_positive']:
                stats['hard_pos'] += 1
            if eval_res['is_microscopic_positive']:
                stats['microscopic_only'] += 1
            if eval_res['is_borderline_small_positive']:
                stats['borderline_small'] += 1
        else:
            stats['total_neg'] += 1
            if eval_res['is_clear_negative']:
                stats['clear_neg'] += 1
            if eval_res['is_ambiguous_negative']:
                stats['ambiguous_neg'] += 1
            if 'confusable-object' in eval_res['difficulty_tags']:
                stats['confusable_neg'] += 1
    results[cls] = stats

print(f"Total frames evaluated: {len(ds.frames)}\n")
for cls, s in results.items():
    print(f"=== Class: {cls.upper()} ===")
    print(f"  Positive frames:        {s['pos_frames']:5d}")
    print(f"    - Easy positive:      {s['easy_pos']:5d}")
    print(f"    - Hard positive:      {s['hard_pos']:5d}")
    print(f"    - Microscopic only:   {s['microscopic_only']:5d}")
    print(f"    - Borderline small:   {s['borderline_small']:5d}")
    print(f"  Negative frames:        {s['total_neg']:5d}")
    print(f"    - Clear negative:     {s['clear_neg']:5d}")
    print(f"    - Confusable negative:{s['confusable_neg']:5d}")
    print(f"    - Ambiguous negative: {s['ambiguous_neg']:5d}")
    print()
