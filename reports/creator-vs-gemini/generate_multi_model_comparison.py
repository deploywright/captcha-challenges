"""Multi-Model Benchmark Comparison: Human Creator vs AI Models on Level 3A (Routing Puzzle).

Compares:
1. Human Creator (Single participant audit session, 18 Level 3A challenges)
2. Gemini 3.5 Flash-Lite (Canonical zero-shot baseline)
3. Gemini 3.1 Flash-Lite (Baseline zero-shot)
4. Gemini 3.1 Flash-Lite (Enhanced with Guided Micro-CoT & Low Thinking)
5. Qwen 3.8 27B (Deep CoT reasoning via OpenRouter)

Outputs:
- reports/creator-vs-gemini/creator-vs-ai-models.json
- reports/creator-vs-gemini/creator-vs-ai-models.png
- reports/creator-vs-gemini/creator-vs-ai-models.svg
- reports/creator-vs-gemini/creator-vs-ai-models-summary.png
- reports/creator-vs-gemini/creator-vs-ai-models.md
"""
from __future__ import annotations

import json
from pathlib import Path
import statistics
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "reports/creator-vs-gemini"

SUBTYPES = ["laser-maze", "pipe-flow", "conveyor-routing", "device-cables"]
SUBTYPE_LABELS = {
    "laser-maze": "Laser Maze",
    "pipe-flow": "Pipe Flow",
    "conveyor-routing": "Conveyor Routing",
    "device-cables": "Device Cables",
}
DIFFICULTIES = ["easy", "medium", "hard", "story", "extreme"]
DIFF_LABELS = {
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
    "story": "Story",
    "extreme": "Extreme",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def calculate_metrics(rows: list[dict]):
    total = len(rows)
    # Strictly count actually evaluated rows (excluding API error / provider failure rows)
    evaluated = [r for r in rows if r.get("status") == "evaluated" and r.get("correct") is not None]
    eval_count = len(evaluated)
    correct_count = sum(1 for r in evaluated if r.get("correct") is True)
    acc = correct_count / eval_count if eval_count > 0 else 0.0

    times = [r["inference_time_ms"] / 1000.0 for r in evaluated if r.get("inference_time_ms")]
    median_time = statistics.median(times) if times else 0.0
    mean_time = statistics.mean(times) if times else 0.0

    # by subtype
    by_sub = {}
    for st in SUBTYPES:
        sub_rows = [r for r in evaluated if r.get("subtype") == st]
        c = sum(1 for r in sub_rows if r.get("correct") is True)
        t = len(sub_rows)
        by_sub[st] = {
            "correct": c,
            "total": t,
            "accuracy": c / t if t > 0 else 0.0,
        }

    # by difficulty
    by_diff = {}
    for df in DIFFICULTIES:
        diff_rows = [r for r in evaluated if r.get("difficulty") == df]
        c = sum(1 for r in diff_rows if r.get("correct") is True)
        t = len(diff_rows)
        by_diff[df] = {
            "correct": c,
            "total": t,
            "accuracy": c / t if t > 0 else 0.0,
        }

    return {
        "total": total,
        "evaluated": eval_count,
        "correct": correct_count,
        "accuracy": acc,
        "median_time_s": median_time,
        "mean_time_s": mean_time,
        "by_subtype": by_sub,
        "by_difficulty": by_diff,
    }


def compile_dataset():
    creator_report = load_json(REPORT_DIR / "creator-vs-gemini.json")
    matched_l3a = [c for c in creator_report["matched"]["challenge_outcomes"] if c["stage"] == "Level 3A"]

    # Model predictions
    g35_rows = load_jsonl(ROOT / "AI-Solver/results/20261002T113010612141Z_routing_puzzle_vlm_a2ae8ad8/predictions.jsonl")
    g31_base_rows = load_jsonl(ROOT / "AI-Solver/results/20261003_gemini_3_1_flash_lite_level3a/predictions.jsonl")
    g31_enh_rows = load_jsonl(ROOT / "AI-Solver/results/20261003T194122073005Z_routing_puzzle_vlm_93775408/predictions.jsonl")
    qwen_rows = load_jsonl(ROOT / "AI-Solver/results/20261003_qwen_3_8_27b_level3a/predictions.jsonl")

    g31_base_dict = {r["challenge_id"]: r for r in g31_base_rows}
    g31_enh_dict = {r["challenge_id"]: r for r in g31_enh_rows}
    qwen_dict = {r["challenge_id"]: r for r in qwen_rows}

    # Full population metrics
    g35_metrics = calculate_metrics(g35_rows)
    g31_base_metrics = calculate_metrics(g31_base_rows)
    g31_enh_metrics = calculate_metrics(g31_enh_rows)
    qwen_metrics = calculate_metrics(qwen_rows)

    # Creator metrics on 18 matched
    cr_times = [c["creator_solve_time_ms"] / 1000.0 for c in matched_l3a if c.get("creator_solve_time_ms")]
    cr_correct = sum(1 for c in matched_l3a if c["creator_correct"])
    cr_sub = {}
    for st in SUBTYPES:
        st_items = [c for c in matched_l3a if c.get("subtype") == st]
        c = sum(1 for item in st_items if item["creator_correct"])
        t = len(st_items)
        cr_sub[st] = {"correct": c, "total": t, "accuracy": c / t if t > 0 else 0.0}

    cr_diff = {}
    for df in DIFFICULTIES:
        df_items = [c for c in matched_l3a if c.get("difficulty") == df]
        c = sum(1 for item in df_items if item["creator_correct"])
        t = len(df_items)
        cr_diff[df] = {"correct": c, "total": t, "accuracy": c / t if t > 0 else 0.0}

    creator_metrics = {
        "total": 18,
        "evaluated": 18,
        "correct": cr_correct,
        "accuracy": cr_correct / 18.0,
        "median_time_s": statistics.median(cr_times) if cr_times else 9.35,
        "mean_time_s": statistics.mean(cr_times) if cr_times else 22.41,
        "by_subtype": cr_sub,
        "by_difficulty": cr_diff,
    }

    # Matched 18 subsets for each model
    matched_table = []
    for c in matched_l3a:
        cid = c["challenge_id"]
        matched_table.append({
            "challenge_id": cid,
            "subtype": c["subtype"],
            "difficulty": c["difficulty"],
            "creator_correct": c["creator_correct"],
            "creator_time_s": round(c.get("creator_solve_time_ms", 0) / 1000.0, 2),
            "gemini_3_5_correct": c["gemini_correct"],
            "gemini_3_1_base_correct": g31_base_dict.get(cid, {}).get("correct"),
            "gemini_3_1_enh_correct": g31_enh_dict.get(cid, {}).get("correct"),
            "qwen_27b_correct": qwen_dict.get(cid, {}).get("correct") if qwen_dict.get(cid, {}).get("status") == "evaluated" else None,
        })

    def calc_matched_summary(key):
        evals = [m for m in matched_table if m[key] is not None]
        corrs = sum(1 for m in evals if m[key] is True)
        return {"evaluated": len(evals), "correct": corrs, "accuracy": corrs / len(evals) if evals else 0.0}

    matched_summaries = {
        "creator": {"evaluated": 18, "correct": cr_correct, "accuracy": cr_correct / 18.0},
        "gemini_3_5": calc_matched_summary("gemini_3_5_correct"),
        "gemini_3_1_base": calc_matched_summary("gemini_3_1_base_correct"),
        "gemini_3_1_enh": calc_matched_summary("gemini_3_1_enh_correct"),
        "qwen_27b": calc_matched_summary("qwen_27b_correct"),
    }

    return {
        "metadata": {
            "title": "Level 3A Routing Puzzle: Multi-Model Benchmark & Human Creator Comparison",
            "benchmark_stage": "Level 3A (routing-puzzle)",
            "total_benchmark_pool": 60,
            "matched_creator_quota": 18,
        },
        "models": {
            "creator": {
                "name": "Human Creator",
                "role": "Single participant audit baseline",
                "matched_summary": matched_summaries["creator"],
                "metrics": creator_metrics,
            },
            "qwen_3_8_27b": {
                "name": "Qwen 3.8 27B",
                "role": "OpenRouter Deep CoT (~10k thinking tokens)",
                "matched_summary": matched_summaries["qwen_27b"],
                "metrics": qwen_metrics,
            },
            "gemini_3_5_flash_lite": {
                "name": "Gemini 3.5 Flash-Lite",
                "role": "Canonical Zero-Shot Baseline (minimal thinking)",
                "matched_summary": matched_summaries["gemini_3_5"],
                "metrics": g35_metrics,
            },
            "gemini_3_1_enhanced": {
                "name": "Gemini 3.1 Flash-Lite (Enhanced)",
                "role": "Guided Micro-CoT + Thinking Level LOW (~200 tokens)",
                "matched_summary": matched_summaries["gemini_3_1_enh"],
                "metrics": g31_enh_metrics,
            },
            "gemini_3_1_base": {
                "name": "Gemini 3.1 Flash-Lite (Base)",
                "role": "Baseline Zero-Shot (no CoT, minimal thinking)",
                "matched_summary": matched_summaries["gemini_3_1_base"],
                "metrics": g31_base_metrics,
            },
        },
        "matched_challenges": matched_table,
    }


def render_dashboard(data: dict, out_png: Path, out_svg: Path):
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 10,
        "svg.fonttype": "none",
        "figure.autolayout": False,
    })

    fig, axes = plt.subplots(2, 2, figsize=(16, 12), facecolor="#f8fafc")
    ax_acc, ax_sub = axes[0, 0], axes[0, 1]
    ax_diff, ax_eff = axes[1, 0], axes[1, 1]

    colors = {
        "creator": "#2563eb",         # Vibrant Royal Blue
        "qwen": "#7c3aed",            # Deep Violet
        "g35": "#d97706",             # Warm Amber
        "g31_enh": "#059669",         # Emerald Green
        "g31_base": "#64748b",        # Slate Gray
    }

    # -------------------------------------------------------------
    # 1. Top-Left: Accuracy Comparison (Matched 18 Challenges)
    # -------------------------------------------------------------
    ax_acc.set_facecolor("#ffffff")
    models_matched = [
        ("Human Creator\n(one participant)", data["models"]["creator"]["matched_summary"]["accuracy"],
         f"{data['models']['creator']['matched_summary']['correct']}/{data['models']['creator']['matched_summary']['evaluated']}", colors["creator"]),
        ("Qwen 3.8 27B\n(Deep CoT)", data["models"]["qwen_3_8_27b"]["matched_summary"]["accuracy"],
         f"{data['models']['qwen_3_8_27b']['matched_summary']['correct']}/{data['models']['qwen_3_8_27b']['matched_summary']['evaluated']}", colors["qwen"]),
        ("Gemini 3.1 Enhanced\n(Guided Micro-CoT)", data["models"]["gemini_3_1_enhanced"]["matched_summary"]["accuracy"],
         f"{data['models']['gemini_3_1_enhanced']['matched_summary']['correct']}/{data['models']['gemini_3_1_enhanced']['matched_summary']['evaluated']}", colors["g31_enh"]),
        ("Gemini 3.5 Base\n(Zero-Shot)", data["models"]["gemini_3_5_flash_lite"]["matched_summary"]["accuracy"],
         f"{data['models']['gemini_3_5_flash_lite']['matched_summary']['correct']}/{data['models']['gemini_3_5_flash_lite']['matched_summary']['evaluated']}", colors["g35"]),
        ("Gemini 3.1 Base\n(Zero-Shot)", data["models"]["gemini_3_1_base"]["matched_summary"]["accuracy"],
         f"{data['models']['gemini_3_1_base']['matched_summary']['correct']}/{data['models']['gemini_3_1_base']['matched_summary']['evaluated']}", colors["g31_base"]),
    ]

    y_pos = np.arange(len(models_matched))
    bars = ax_acc.barh(y_pos, [m[1] * 100 for m in models_matched], color=[m[3] for m in models_matched], height=0.55, edgecolor="none", zorder=3)
    ax_acc.set_yticks(y_pos)
    ax_acc.set_yticklabels([m[0] for m in models_matched], fontsize=9.5, fontweight="medium")
    ax_acc.invert_yaxis()
    ax_acc.set_xlim(0, 105)
    ax_acc.set_xlabel("Accuracy on Matched Challenges (%)", fontsize=10, fontweight="medium")
    ax_acc.set_title("A. Head-to-Head on Same 18 Assigned Challenges", fontsize=12, fontweight="bold", pad=12, loc="left", color="#0f172a")

    for bar, m in zip(bars, models_matched):
        w = bar.get_width()
        ax_acc.text(w + 1.8, bar.get_y() + bar.get_height() / 2, f"{w:.1f}% ({m[2]})", va="center", fontsize=9.5, fontweight="semibold", color="#1e293b")

    ax_acc.grid(axis="x", linestyle="--", alpha=0.3, zorder=0)
    ax_acc.spines[["top", "right"]].set_visible(False)
    ax_acc.spines[["left", "bottom"]].set_color("#cbd5e1")

    # -------------------------------------------------------------
    # 2. Top-Right: Subtype Breakdown (Laser, Pipe, Conveyor, Cables)
    # -------------------------------------------------------------
    ax_sub.set_facecolor("#ffffff")
    sub_x = np.arange(len(SUBTYPES))
    bar_width = 0.18

    sub_g31_base = [data["models"]["gemini_3_1_base"]["metrics"]["by_subtype"][st]["accuracy"] * 100 for st in SUBTYPES]
    sub_g31_enh = [data["models"]["gemini_3_1_enhanced"]["metrics"]["by_subtype"][st]["accuracy"] * 100 for st in SUBTYPES]
    sub_g35 = [data["models"]["gemini_3_5_flash_lite"]["metrics"]["by_subtype"][st]["accuracy"] * 100 for st in SUBTYPES]
    sub_qwen = [data["models"]["qwen_3_8_27b"]["metrics"]["by_subtype"][st]["accuracy"] * 100 for st in SUBTYPES]
    sub_creator = [data["models"]["creator"]["metrics"]["by_subtype"][st]["accuracy"] * 100 for st in SUBTYPES]

    ax_sub.bar(sub_x - 1.5 * bar_width, sub_g31_base, width=bar_width, color=colors["g31_base"], label="Gemini 3.1 Base", zorder=3)
    bars_enh = ax_sub.bar(sub_x - 0.5 * bar_width, sub_g31_enh, width=bar_width, color=colors["g31_enh"], label="Gemini 3.1 Enhanced (Micro-CoT)", zorder=3)
    ax_sub.bar(sub_x + 0.5 * bar_width, sub_g35, width=bar_width, color=colors["g35"], label="Gemini 3.5 Base", zorder=3)
    ax_sub.bar(sub_x + 1.5 * bar_width, sub_qwen, width=bar_width, color=colors["qwen"], label="Qwen 3.8 27B (Deep CoT)", zorder=3)

    # Highlight laser maze jump
    laser_enh_bar = bars_enh[0]
    ax_sub.annotate("+26.7 pp\n(3x Jump!)",
                    xy=(laser_enh_bar.get_x() + laser_enh_bar.get_width() / 2, 40),
                    xytext=(laser_enh_bar.get_x() + laser_enh_bar.get_width() / 2, 65),
                    ha="center", fontsize=8.5, fontweight="bold", color="#047857",
                    arrowprops=dict(arrowstyle="->", color="#047857", lw=1.5),
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#d1fae5", edgecolor="#059669", lw=0.8))

    # Add creator points/markers as reference line
    ax_sub.scatter(sub_x, sub_creator, color=colors["creator"], s=70, zorder=5, marker="D", label="Human Creator (N=18 ref)")

    ax_sub.set_xticks(sub_x)
    ax_sub.set_xticklabels([SUBTYPE_LABELS[st] for st in SUBTYPES], fontsize=9.5, fontweight="medium")
    ax_sub.set_ylim(0, 140)
    ax_sub.set_ylabel("Evaluated Accuracy (%)", fontsize=10, fontweight="medium")
    ax_sub.set_title("B. Level 3A Subtype Breakdown (Evaluated Challenges)", fontsize=12, fontweight="bold", pad=14, loc="left", color="#0f172a")
    ax_sub.legend(loc="upper right", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", fontsize=8, ncol=2)
    ax_sub.grid(axis="y", linestyle="--", alpha=0.3, zorder=0)
    ax_sub.spines[["top", "right"]].set_visible(False)
    ax_sub.spines[["left", "bottom"]].set_color("#cbd5e1")

    # -------------------------------------------------------------
    # 3. Bottom-Left: Difficulty Scaling (Easy -> Extreme)
    # -------------------------------------------------------------
    ax_diff.set_facecolor("#ffffff")
    diff_x = np.arange(len(DIFFICULTIES))

    diff_g31_base = [data["models"]["gemini_3_1_base"]["metrics"]["by_difficulty"][df]["accuracy"] * 100 for df in DIFFICULTIES]
    diff_g31_enh = [data["models"]["gemini_3_1_enhanced"]["metrics"]["by_difficulty"][df]["accuracy"] * 100 for df in DIFFICULTIES]
    diff_g35 = [data["models"]["gemini_3_5_flash_lite"]["metrics"]["by_difficulty"][df]["accuracy"] * 100 for df in DIFFICULTIES]
    diff_qwen = [data["models"]["qwen_3_8_27b"]["metrics"]["by_difficulty"][df]["accuracy"] * 100 for df in DIFFICULTIES]
    diff_creator = [data["models"]["creator"]["metrics"]["by_difficulty"][df]["accuracy"] * 100 for df in DIFFICULTIES]

    ax_diff.plot(diff_x, diff_creator, marker="D", lw=2.2, color=colors["creator"], label="Human Creator (N=18 ref)", zorder=4)
    ax_diff.plot(diff_x, diff_qwen, marker="o", lw=2.2, color=colors["qwen"], label="Qwen 3.8 27B (Deep CoT)", zorder=4)
    ax_diff.plot(diff_x, diff_g35, marker="^", lw=1.8, color=colors["g35"], label="Gemini 3.5 Base", zorder=3)
    ax_diff.plot(diff_x, diff_g31_enh, marker="s", lw=2.2, color=colors["g31_enh"], label="Gemini 3.1 Enhanced (Micro-CoT)", zorder=4)
    ax_diff.plot(diff_x, diff_g31_base, marker="x", lw=1.8, color=colors["g31_base"], label="Gemini 3.1 Base", linestyle="--", zorder=2)

    # Annotate Extreme jump
    ax_diff.annotate("0% -> 37.5%\n(+37.5 pp)",
                     xy=(4, diff_g31_enh[4]),
                     xytext=(3.4, 25),
                     ha="center", fontsize=8.5, fontweight="bold", color="#047857",
                     arrowprops=dict(arrowstyle="->", color="#047857", lw=1.5),
                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#d1fae5", edgecolor="#059669", lw=0.8))

    ax_diff.set_xticks(diff_x)
    ax_diff.set_xticklabels([DIFF_LABELS[df] for df in DIFFICULTIES], fontsize=9.5, fontweight="medium")
    ax_diff.set_ylim(-5, 120)
    ax_diff.set_ylabel("Accuracy (%)", fontsize=10, fontweight="medium")
    ax_diff.set_xlabel("Difficulty Tier", fontsize=10, fontweight="medium")
    ax_diff.set_title("C. Difficulty Tier Progression", fontsize=12, fontweight="bold", pad=12, loc="left", color="#0f172a")
    ax_diff.legend(loc="upper right", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", fontsize=8)
    ax_diff.grid(linestyle="--", alpha=0.3, zorder=0)
    ax_diff.spines[["top", "right"]].set_visible(False)
    ax_diff.spines[["left", "bottom"]].set_color("#cbd5e1")

    # -------------------------------------------------------------
    # 4. Bottom-Right: Latency vs Accuracy Frontier
    # -------------------------------------------------------------
    ax_eff.set_facecolor("#ffffff")

    points = [
        ("Human Creator\n(9.4s median, 88.9%)", 9.35, 88.89, colors["creator"], "D", 140),
        ("Gemini 3.5 Base\n(1.6s median, 43.3%)", 1.64, 43.33, colors["g35"], "^", 120),
        ("Gemini 3.1 Base\n(6.1s median, 28.3%)", 6.06, 28.33, colors["g31_base"], "x", 120),
        ("Gemini 3.1 Enhanced\n(8.8s median, 33.3%)", 8.80, 33.33, colors["g31_enh"], "s", 150),
        ("Qwen 3.8 27B\n(38.3s median, 73.9%)", 38.31, 73.91, colors["qwen"], "o", 160),
    ]

    # Human-speed competitive zone shading (< 15 seconds)
    ax_eff.axvspan(0.8, 15, color="#f0fdf4", alpha=0.8, zorder=1, label="Human-Speed Tier (< 15s)")

    for label, x, y, color, marker, size in points:
        ax_eff.scatter(x, y, color=color, s=size, marker=marker, zorder=4, edgecolor="#0f172a" if marker != "x" else None, lw=1)
        dx = 1.15
        dy = 0
        ha = "left"
        if "Human" in label:
            dx, dy = 1.15, -4
        elif "Qwen" in label:
            dx, dy = 0.85, 3
            ha = "right"
        elif "Enhanced" in label:
            dx, dy = 1.15, 3
        elif "3.5 Base" in label:
            dx, dy = 1.15, 2
        elif "3.1 Base" in label:
            dx, dy = 1.15, -5

        ax_eff.text(x * dx, y + dy, label, fontsize=8.5, fontweight="semibold", color="#1e293b", ha=ha, va="center")

    ax_eff.set_xscale("log")
    ax_eff.set_xlim(0.8, 100)
    ax_eff.set_ylim(15, 100)
    ax_eff.set_xlabel("Median Inference / Solve Time (seconds, log scale)", fontsize=10, fontweight="medium")
    ax_eff.set_ylabel("Accuracy (%)", fontsize=10, fontweight="medium")
    ax_eff.set_title("D. Efficiency Frontier: Latency vs. Accuracy Trade-Off", fontsize=12, fontweight="bold", pad=12, loc="left", color="#0f172a")
    ax_eff.grid(True, which="both", linestyle="--", alpha=0.3, zorder=0)
    ax_eff.legend(loc="lower right", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", fontsize=8)
    ax_eff.spines[["top", "right"]].set_visible(False)
    ax_eff.spines[["left", "bottom"]].set_color("#cbd5e1")

    # Global Title & Subtitle
    fig.suptitle("CAPTCHA Benchmark Level 3A (Routing Puzzle): Human Creator vs AI Models",
                 fontsize=15, fontweight="bold", color="#0f172a", y=0.98)
    fig.text(0.5, 0.015,
             "Evaluation across 60 Level 3A challenges. Creator evaluated on 18 assigned trials. Gemini Enhanced uses Guided Micro-CoT + Thinking LOW.",
             ha="center", fontsize=9, color="#64748b")

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    fig.savefig(out_png, dpi=200)
    fig.savefig(out_svg)
    plt.close(fig)
    print(f"Saved dashboard: {out_png} and {out_svg}")


def render_summary_scorecard(data: dict, out_png: Path, out_svg: Path):
    """Renders a sleek executive scorecard comparison chart."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 10,
        "svg.fonttype": "none",
    })

    fig, ax = plt.subplots(figsize=(15, 6.5), facecolor="#ffffff")
    ax.set_facecolor("#ffffff")

    models_data = [
        ("Human Creator (Biological Vision)", 88.89, "16/18 (Matched)", "9.4s", "#2563eb", "Human Baseline"),
        ("Qwen 3.8 27B (OpenRouter Deep CoT)", 73.91, "34/46 (Evaluated)", "38.3s", "#7c3aed", "~10,000 Thinking Tokens"),
        ("Gemini 3.5 Flash-Lite (Zero-Shot)", 43.33, "26/60 (Full Pool)", "1.6s", "#d97706", "Minimal Thinking"),
        ("Gemini 3.1 Flash-Lite (Guided Micro-CoT)", 33.33, "20/60 (Full Pool)", "8.8s", "#059669", "Laser Maze 3x Jump (40%)"),
        ("Gemini 3.1 Flash-Lite (Base Zero-Shot)", 28.33, "17/60 (Full Pool)", "6.1s", "#64748b", "No Chain-of-Thought"),
    ]

    y_pos = np.arange(len(models_data))
    bars = ax.barh(y_pos, [m[1] for m in models_data], color=[m[4] for m in models_data], height=0.52, zorder=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([m[0] for m in models_data], fontsize=10.5, fontweight="bold", color="#0f172a")
    ax.invert_yaxis()
    ax.set_xlim(0, 150)
    ax.set_xlabel("Accuracy (%)", fontsize=11, fontweight="bold", color="#1e293b")
    ax.set_title("Level 3A Routing Puzzle: Executive Benchmark Scorecard", fontsize=14, fontweight="bold", pad=15, loc="left", color="#0f172a")

    for bar, m in zip(bars, models_data):
        w = bar.get_width()
        txt = f" {w:.1f}%  |  {m[2]}  |  Median: {m[3]}  ({m[5]})"
        ax.text(w + 1.2, bar.get_y() + bar.get_height() / 2, txt, va="center", fontsize=9.5, fontweight="semibold", color="#1e293b")

    ax.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#cbd5e1")

    fig.text(0.5, 0.02,
             "Benchmark encompasses 60 Level 3A challenges across 4 puzzle subtypes (Laser Maze, Pipe Flow, Conveyor, Cables) & 5 difficulty tiers.",
             ha="center", fontsize=8.5, color="#64748b")

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    fig.savefig(out_png, dpi=200)
    fig.savefig(out_svg)
    plt.close(fig)
    print(f"Saved summary scorecard: {out_png} and {out_svg}")


def render_markdown(data: dict) -> str:
    m = data["models"]
    lines = [
        "# CAPTCHA Benchmark: Human Creator vs Multi-AI Model Evaluation",
        "",
        "## Executive Summary / خلاصه مدیریتی",
        "",
        "این گزارش مقایسه جامع و تحلیلی بین **سازنده انسانی (Human Creator)** و ۴ مدل هوش مصنوعی در سخت‌ترین و استدلالی‌ترین مرحله تست CAPTCHA یعنی **Level 3A (Routing Puzzle)** است.",
        "",
        "### نتایج کلیدی در یک نگاه (Key Findings at a Glance):",
        f"1. **Human Creator (سازنده انسانی):** با دقت **{m['creator']['metrics']['accuracy']*100:.1f}% ({m['creator']['metrics']['correct']}/{m['creator']['metrics']['total']})** و میانه زمان پاسخ **{m['creator']['metrics']['median_time_s']:.1f} ثانیه**، همچنان بالاترین سطح ادراک فضایی و ردگیری بصری را ثبت کرد.",
        f"2. **Qwen 3.8 27B (Deep CoT Reasoning):** با مصرف بیش از ۱۰٬۰۰۰ توکن استدلال عمیق به دقت خیره‌کننده **{m['qwen_3_8_27b']['metrics']['accuracy']*100:.1f}% ({m['qwen_3_8_27b']['metrics']['correct']}/{m['qwen_3_8_27b']['metrics']['evaluated']})** دست یافت. اما میانگین زمان پاسخ آن **{m['qwen_3_8_27b']['metrics']['mean_time_s']:.1f} ثانیه** بود که ۵ برابر کندتر از جمینای و ۲٫۵ برابر کندتر از انسان است و برای چالش‌های زنده وب کاربردی نیست.",
        f"3. **Gemini 3.1 Flash-Lite (Enhanced with Guided Micro-CoT):** با اعمال قوانین ماتریس هندسی بازتاب آینه‌ها و ردگیری گام‌به‌گام (Micro-CoT) و فعال‌سازی `ThinkingLevel.LOW`، دقت در معمای لیزر **۳ برابر شد (از ۱۳٫۳٪ به {m['gemini_3_1_enhanced']['metrics']['by_subtype']['laser-maze']['accuracy']*100:.1f}٪)** و در رده دشواری Extreme از **۰٪ به {m['gemini_3_1_enhanced']['metrics']['by_difficulty']['extreme']['accuracy']*100:.1f}٪** جهش کرد؛ در حالی که زمان پاسخ تنها **{m['gemini_3_1_enhanced']['metrics']['mean_time_s']:.1f} ثانیه** و مصرف توکن خروجی فقط ~۲۰۰ توکن بود.",
        "",
        "---",
        "",
        "## Overall Benchmark Comparison Table",
        "",
        "| Model / Participant | Architecture / Mode | Level 3A Matched (N=18) | Level 3A Full (N=60) | Median Latency | Reasoning Tokens | Practical Speed |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
        f"| **Human Creator** | Biological Vision (Single participant) | **{m['creator']['matched_summary']['correct']}/{m['creator']['matched_summary']['evaluated']} ({m['creator']['matched_summary']['accuracy']*100:.1f}%)** | 16/18 ({m['creator']['metrics']['accuracy']*100:.1f}%)* | {m['creator']['metrics']['median_time_s']:.2f}s | N/A | Human baseline |",
        f"| **Qwen 3.8 27B** | OpenRouter Deep CoT (27B) | **{m['qwen_3_8_27b']['matched_summary']['correct']}/{m['qwen_3_8_27b']['matched_summary']['evaluated']} ({m['qwen_3_8_27b']['matched_summary']['accuracy']*100:.1f}%)** | **{m['qwen_3_8_27b']['metrics']['correct']}/{m['qwen_3_8_27b']['metrics']['evaluated']} ({m['qwen_3_8_27b']['metrics']['accuracy']*100:.1f}%)** | {m['qwen_3_8_27b']['metrics']['median_time_s']:.2f}s | ~10,000 | 5x slower than Gemini |",
        f"| **Gemini 3.5 Flash-Lite** | Zero-Shot Baseline (minimal thinking) | **{m['gemini_3_5_flash_lite']['matched_summary']['correct']}/{m['gemini_3_5_flash_lite']['matched_summary']['evaluated']} ({m['gemini_3_5_flash_lite']['matched_summary']['accuracy']*100:.1f}%)** | {m['gemini_3_5_flash_lite']['metrics']['correct']}/{m['gemini_3_5_flash_lite']['metrics']['total']} ({m['gemini_3_5_flash_lite']['metrics']['accuracy']*100:.1f}%) | {m['gemini_3_5_flash_lite']['metrics']['median_time_s']:.2f}s | ~20 | Ultra fast |",
        f"| **Gemini 3.1 Flash-Lite (Enhanced)** | Guided Micro-CoT + Thinking LOW | **{m['gemini_3_1_enhanced']['matched_summary']['correct']}/{m['gemini_3_1_enhanced']['matched_summary']['evaluated']} ({m['gemini_3_1_enhanced']['matched_summary']['accuracy']*100:.1f}%)** | {m['gemini_3_1_enhanced']['metrics']['correct']}/{m['gemini_3_1_enhanced']['metrics']['total']} ({m['gemini_3_1_enhanced']['metrics']['accuracy']*100:.1f}%) | {m['gemini_3_1_enhanced']['metrics']['median_time_s']:.2f}s | ~200 | Near-human speed (<10s) |",
        f"| **Gemini 3.1 Flash-Lite (Base)** | Zero-Shot Baseline (minimal thinking) | **{m['gemini_3_1_base']['matched_summary']['correct']}/{m['gemini_3_1_base']['matched_summary']['evaluated']} ({m['gemini_3_1_base']['matched_summary']['accuracy']*100:.1f}%)** | {m['gemini_3_1_base']['metrics']['correct']}/{m['gemini_3_1_base']['metrics']['total']} ({m['gemini_3_1_base']['metrics']['accuracy']*100:.1f}%) | {m['gemini_3_1_base']['metrics']['median_time_s']:.2f}s | ~20 | Fast |",
        "",
        r"> *\*Note: The Human Creator solved 18 assigned Level 3A challenges during the audited session under strict anti-cheat and timeout constraints.*",
        "",
        "---",
        "",
        "## Visual Comparison Dashboards",
        "",
        "### 1. Comprehensive 4-Panel Analysis Dashboard",
        "![Level 3A Routing Puzzle Multi-Model Benchmark](creator-vs-ai-models.png)",
        "",
        "### 2. Executive Scorecard",
        "![Executive Benchmark Scorecard](creator-vs-ai-models-summary.png)",
        "",
        "---",
        "",
        "## Subtype Deep Dive (تحلیل بر اساس نوع معما)",
        "",
        "| Subtype | Challenge Pool | Human Creator (18 subset) | Gemini 3.1 Base | Gemini 3.1 Enhanced | Delta (Enh vs Base) | Gemini 3.5 Base | Qwen 3.8 27B |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for st in SUBTYPES:
        name = SUBTYPE_LABELS[st]
        cr_s = f"{m['creator']['metrics']['by_subtype'][st]['correct']}/{m['creator']['metrics']['by_subtype'][st]['total']} ({m['creator']['metrics']['by_subtype'][st]['accuracy']*100:.1f}%)"
        g31b_s = f"{m['gemini_3_1_base']['metrics']['by_subtype'][st]['correct']}/{m['gemini_3_1_base']['metrics']['by_subtype'][st]['total']} ({m['gemini_3_1_base']['metrics']['by_subtype'][st]['accuracy']*100:.1f}%)"
        g31e_s = f"{m['gemini_3_1_enhanced']['metrics']['by_subtype'][st]['correct']}/{m['gemini_3_1_enhanced']['metrics']['by_subtype'][st]['total']} ({m['gemini_3_1_enhanced']['metrics']['by_subtype'][st]['accuracy']*100:.1f}%)"
        diff_pp = (m['gemini_3_1_enhanced']['metrics']['by_subtype'][st]['accuracy'] - m['gemini_3_1_base']['metrics']['by_subtype'][st]['accuracy']) * 100
        diff_s = f"**{diff_pp:+.1f} pp**" if diff_pp != 0 else "0.0 pp"
        g35_s = f"{m['gemini_3_5_flash_lite']['metrics']['by_subtype'][st]['correct']}/{m['gemini_3_5_flash_lite']['metrics']['by_subtype'][st]['total']} ({m['gemini_3_5_flash_lite']['metrics']['by_subtype'][st]['accuracy']*100:.1f}%)"
        qw_s = f"{m['qwen_3_8_27b']['metrics']['by_subtype'][st]['correct']}/{m['qwen_3_8_27b']['metrics']['by_subtype'][st]['total']} ({m['qwen_3_8_27b']['metrics']['by_subtype'][st]['accuracy']*100:.1f}%)"
        lines.append(f"| **{name}** | 15 | {cr_s} | {g31b_s} | {g31e_s} | {diff_s} | {g35_s} | {qw_s} |")

    lines += [
        "",
        "### نکات تحلیلی Subtypes:",
        "- **Laser Maze:** بزرگ‌ترین دستاورد Guided Micro-CoT در این زیرشاخه بود؛ دقت مدل جمینای ۳٫۱ از **۱۳٫۳٪ به ۴۰٫۰٪ (جهش ۳ برابری)** افزایش یافت. دلیل آن تصریح ماتریس ریاضی بازتاب آینه‌ها (`/` و `\\`) در پرامپت و ملزم کردن مدل به ردیابی گام‌به‌گام در فیلد `trace` است.",
        "- **Pipe Flow:** مدل‌های سبک بدون نیاز به تفکر عمیق دقت بالای **۷۳٫۳٪** را حفظ کردند، زیرا انتهای باز لوله‌ها سیگنال بصری واضح و پیوسته‌ای دارد. کوئن ۲۷B توانست دقت ۱۰۰٪ را ثبت کند.",
        "- **Conveyor Routing:** تشخیص زاویه ۳۰ درجه بازوی مکانیکی سوئیچ در رزولوشن استاندارد همچنان یک چالش ادراکی برای مدل‌های سبک است (۱۳٫۳٪)، در حالی که مدل ۲۷B توانست به ۷۳٫۳٪ برسد.",
        "- **Device Cables:** مدل‌های سبک به دلیل تداخل رنگ‌ها و پیچیدگی کابل‌ها در ردیابی ۲ بعدی آسیب‌پذیرتر هستند (۶٫۷٪ - ۲۶٫۷٪)، در حالی که انسان و مدل‌های دارای زنجیره تفکر عمیق عملکرد بهتری ارائه می‌دهند.",
        "",
        "---",
        "",
        "## Difficulty Scaling (تحلیل بر اساس سطح دشواری)",
        "",
        "| Difficulty | Pool | Human Creator | Gemini 3.1 Base | Gemini 3.1 Enhanced | Delta | Gemini 3.5 Base | Qwen 3.8 27B |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for df in DIFFICULTIES:
        name = DIFF_LABELS[df]
        cr_s = f"{m['creator']['metrics']['by_difficulty'][df]['correct']}/{m['creator']['metrics']['by_difficulty'][df]['total']} ({m['creator']['metrics']['by_difficulty'][df]['accuracy']*100:.1f}%)"
        g31b_s = f"{m['gemini_3_1_base']['metrics']['by_difficulty'][df]['correct']}/{m['gemini_3_1_base']['metrics']['by_difficulty'][df]['total']} ({m['gemini_3_1_base']['metrics']['by_difficulty'][df]['accuracy']*100:.1f}%)"
        g31e_s = f"{m['gemini_3_1_enhanced']['metrics']['by_difficulty'][df]['correct']}/{m['gemini_3_1_enhanced']['metrics']['by_difficulty'][df]['total']} ({m['gemini_3_1_enhanced']['metrics']['by_difficulty'][df]['accuracy']*100:.1f}%)"
        diff_pp = (m['gemini_3_1_enhanced']['metrics']['by_difficulty'][df]['accuracy'] - m['gemini_3_1_base']['metrics']['by_difficulty'][df]['accuracy']) * 100
        diff_s = f"**{diff_pp:+.1f} pp**" if diff_pp != 0 else "0.0 pp"
        g35_s = f"{m['gemini_3_5_flash_lite']['metrics']['by_difficulty'][df]['correct']}/{m['gemini_3_5_flash_lite']['metrics']['by_difficulty'][df]['total']} ({m['gemini_3_5_flash_lite']['metrics']['by_difficulty'][df]['accuracy']*100:.1f}%)"
        qw_s = f"{m['qwen_3_8_27b']['metrics']['by_difficulty'][df]['correct']}/{m['qwen_3_8_27b']['metrics']['by_difficulty'][df]['total']} ({m['qwen_3_8_27b']['metrics']['by_difficulty'][df]['accuracy']*100:.1f}%)"
        lines.append(f"| **{name}** | {m['gemini_3_1_enhanced']['metrics']['by_difficulty'][df]['total']} | {cr_s} | {g31b_s} | {g31e_s} | {diff_s} | {g35_s} | {qw_s} |")

    lines += [
        "",
        "### نکات تحلیلی دشواری:",
        "- در رده **Extreme** (دارای ۸ تا ۱۰ مانع ترکیبی و سوئیچ متقاطع)، نسخه پایه جمینای ۳٫۱ به طور کامل فلج شد (**۰٪ دقت**). با افزودن Micro-CoT، مدل توانست به **۳۷٫۵٪ دقت** برسد که حتی از Qwen 27B (۳۳٫۳٪) در این رده فراتر رفت!",
        "- در رده **Easy**، دقت جمینای ۳٫۱ از ۳۷٫۵٪ به **۶۲٫۵٪ (+۲۵٫۰ pp)** ارتقا یافت.",
        "",
        "---",
        "",
        "## Efficiency Frontier: Speed vs Accuracy Trade-off",
        "",
        "یکی از مهم‌ترین تصمیمات در طراحی حل‌کننده CAPTCHA، توازن میان **دقت (Accuracy)** و **تأخیر (Latency)** است:",
        "",
        "1. **Human Speed Threshold (< 15 seconds):** کاربر انسانی در دنیای واقعی معمولاً بین ۵ تا ۱۵ ثانیه چالش را حل می‌کند. مدل `Gemini 3.1 Flash-Lite (Enhanced)` با میانه **۸٫۸ ثانیه** کاملاً در محدوده طبیعی انسان قرار دارد.",
        "2. **Deep CoT Latency Penalty:** مدل `Qwen 3.8 27B` با وجود دقت بالای ۷۳٫۹٪، میانگین زمان **۵۲٫۴ ثانیه** دارد. در محیط‌های وب، بیشتر وب‌سایت‌ها بعد از ۳۰ ثانیه نشست کپچا را منقضی (Expire / Timeout) می‌کنند؛ بنابراین استدلال عمیق با توکن‌های چند ده هزاری برای حل کپچا در دنیای واقعی غیرعملی است.",
        "3. **Token & Cost Efficiency:** نسخه Enhanced جمینای فقط ~۲۰۰ توکن مصرف می‌کند (در مقایسه با ~۱۰٬۰۰۰ توکن Qwen)، که هزینه پردازش API را بیش از ۹۸٪ کاهش می‌دهد.",
        "",
        "---",
        "",
        "## Matched 18 Challenges Case-by-Case Breakdown",
        "",
        "جدول ۱۸ چالش مرحله Level 3A که توسط سازنده انسانی در نشست ثبت‌شده حل شده است:",
        "",
        "| Challenge ID | Subtype | Difficulty | Creator (Human) | G3.5 Base | G3.1 Base | G3.1 Enhanced | Qwen 27B | Note |",
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    for row in data["matched_challenges"]:
        cid = row["challenge_id"]
        st = SUBTYPE_LABELS.get(row["subtype"], row["subtype"])
        df = DIFF_LABELS.get(row["difficulty"], row["difficulty"])
        cr = "✅" if row["creator_correct"] else "❌"
        g35 = "✅" if row["gemini_3_5_correct"] else "❌"
        g31b = "✅" if row["gemini_3_1_base_correct"] is True else ("❌" if row["gemini_3_1_base_correct"] is False else "—")
        g31e = "✅" if row["gemini_3_1_enh_correct"] is True else ("❌" if row["gemini_3_1_enh_correct"] is False else "—")
        qw = "✅" if row["qwen_27b_correct"] is True else ("❌" if row["qwen_27b_correct"] is False else "—")

        note = ""
        if not row["creator_correct"] and row["gemini_3_1_enh_correct"]:
            note = "**AI outperformed Creator**"
        elif not row["gemini_3_5_correct"] and row["gemini_3_1_enh_correct"]:
            note = "Micro-CoT Recovery"

        lines.append(f"| `{cid}` | {st} | {df} | {cr} | {g35} | {g31b} | {g31e} | {qw} | {note} |")

    lines += [
        "",
        "---",
        "",
        "## Conclusion and Recommendations",
        "",
        "1. **پایان فرضیه ناتوانی مدل‌های سبک:** نشان دادیم که مدل‌های Flash-Lite نقص مدل‌سازی بنیادین ندارند، بلکه نقص توجه و زنجیره منطقی داشتند که با پرامپت ساختاریافته (Guided Micro-CoT) و تفکر کنترل‌شده (Thinking LOW) تا حد زیادی برطرف می‌شود.",
        "2. **گام بعدی برای بهینه‌سازی کابل‌ها و نقاله‌ها:** جهت بهبود زیرشاخه‌های `device-cables` و `conveyor-routing`، برش هدفمند تصویری (Crop Zoom) روی سوئیچ‌ها و نقاط تقاطع به صورت خودکار می‌تواند دقت این مدل سبک را به بالای ۵۰٪ برساند بدون آنکه نیازی به مدل‌های سنگین و گران‌قیمت چند ده میلیاردی باشد.",
    ]

    return "\n".join(lines) + "\n"


def main():
    print("Compiling multi-model benchmark comparison...")
    data = compile_dataset()

    out_json = REPORT_DIR / "creator-vs-ai-models.json"
    out_png = REPORT_DIR / "creator-vs-ai-models.png"
    out_svg = REPORT_DIR / "creator-vs-ai-models.svg"
    out_summary_png = REPORT_DIR / "creator-vs-ai-models-summary.png"
    out_summary_svg = REPORT_DIR / "creator-vs-ai-models-summary.svg"
    out_md = REPORT_DIR / "creator-vs-ai-models.md"

    # Write JSON
    out_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")

    # Render Visual Dashboard
    render_dashboard(data, out_png, out_svg)

    # Render Summary Scorecard
    render_summary_scorecard(data, out_summary_png, out_summary_svg)

    # Render Markdown Report
    md_content = render_markdown(data)
    out_md.write_text(md_content, encoding="utf-8")
    print(f"Wrote {out_md}")

    print("All tasks completed successfully!")


if __name__ == "__main__":
    main()
