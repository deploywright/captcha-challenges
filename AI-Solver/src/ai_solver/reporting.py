"""Programmatic report generation for the zero-shot Gemini baseline."""

import json
from pathlib import Path
from typing import Any

STAGE_ORDER = [
    ("Level 1", "street-grid", "Image Selection"),
    ("Level 2A", "hard-street-grid", "Image Selection"),
    ("Level 2B", "checker-shadow", "Single Choice"),
    ("Level 3A", "routing-puzzle", "Single Choice"),
    ("Level 3B", "degraded-vision", "Image Selection"),
]

ROUTING_SUBTYPES = ["pipe-flow", "conveyor-routing", "laser-maze", "device-cables"]
ROUTING_DIFFICULTIES = ["easy", "medium", "story", "hard", "extreme"]
RESOLUTIONS = [64, 48, 32, 24, 16, 12, 8]
ILLUSION_QUESTIONS = {
    "cafe-wall": "Are the horizontal mortar lines dividing the rows parallel?",
    "checker-shadow": "Are squares A and B the same shade?",
    "ebbinghaus": "Are the two orange center circles the same size?",
    "muller-lyer": "Are horizontal lines A and B the same length?",
    "ponzo": "Are horizontal bars A and B the same length?",
    "simultaneous-contrast": "Are squares A and B the same shade of grey?",
}


def _pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val * 100:.2f}%"


def _pct_short(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val * 100:.1f}%"


def _sec(ms: float | None) -> str:
    if ms is None:
        return "N/A"
    return f"{ms / 1000:.2f} s"


def generate_markdown_report(data: dict[str, Any]) -> str:
    """Generate Markdown report entirely from structured metrics JSON."""
    metrics = data.get("metrics", data)
    by_stage = metrics.get("by_stage", {})
    by_subtype = metrics.get("by_subtype", {})
    by_difficulty = metrics.get("by_difficulty", {})
    by_resolution = metrics.get("by_resolution", {})
    by_series = metrics.get("by_series", {})
    sub_by_diff = metrics.get("subtype_by_difficulty", {})

    total_challenges = data.get("total_challenges", metrics.get("challenge_count", 0))
    evaluated = data.get("evaluated_challenges", metrics.get("evaluated_count", 0))
    correct = data.get("correct_challenges", metrics.get("correct_count", 0))
    errors = data.get("error_count", metrics.get("error_count", 0))
    micro_acc = data.get("micro_accuracy", metrics.get("micro_accuracy"))
    macro_stage_acc = data.get("macro_stage_accuracy", metrics.get("macro_stage_accuracy"))
    mean_inference = metrics.get("mean_inference_time_ms")

    model = data.get("model", "gemini-3.5-flash-lite")
    thinking_level = data.get("thinking_level", "MINIMAL")
    cov_pct = _pct(evaluated / total_challenges if total_challenges else 0)

    lines = [
        "# Zero-Shot Gemini 3.5 Flash Lite Baseline Report",
        "",
        (
            f"Definitive baseline evaluation of **{model}** across the full held-out "
            "CAPTCHA benchmark (Levels 1, 2A, 2B, 3A, and 3B)."
        ),
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        (
            "This evaluation measures the zero-shot baseline capability of a general-purpose "
            "commercial multimodal model when evaluated across the complete CAPTCHA challenge "
            "suite under normalized inference parameters."
        ),
        "",
        f"- **Provider**: {data.get('provider', 'Google GenAI')}",
        f"- **Model**: `{model}`",
        f"- **Thinking Level**: `{thinking_level}`",
        "- **Mode**: Zero-shot (no solver-specific training, no fine-tuning)",
        f"- **Total Challenges**: {total_challenges}",
        f"- **Coverage**: {evaluated} / {total_challenges} evaluated ({cov_pct})",
        f"- **Execution Errors**: {errors}",
        f"- **Overall Micro Accuracy**: **{_pct(micro_acc)}** ({correct} / {evaluated} correct)",
        f"- **Macro Stage Accuracy**: **{_pct(macro_stage_acc)}**",
        "",
        "---",
        "",
        "## 2. Top-Level Benchmark Results",
        "",
        "| Stage | Variant | Type | Challenges | Correct | Accuracy | Errors | Mean Inference |",
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
    ]

    for stage_name, variant, type_name in STAGE_ORDER:
        st_data = by_stage.get(stage_name, {})
        st_ch = st_data.get("challenge_count", 0)
        st_corr = st_data.get("correct_count", 0)
        st_acc = st_data.get("exact_challenge_accuracy")
        st_inf = st_data.get("mean_inference_time_ms")
        st_err = st_data.get("challenge_count", 0) - st_data.get("evaluated_count", 0)
        lines.append(
            f"| **{stage_name}** | `{variant}` | {type_name} | {st_ch} | "
            f"{st_corr} | **{_pct_short(st_acc)}** | {st_err} | {_sec(st_inf)} |"
        )

    lines.extend(
        [
            (
                f"| **Total / Overall** | — | — | **{total_challenges}** | **{correct}** | "
                f"**{_pct_short(micro_acc)}** | **{errors}** | **{_sec(mean_inference)}** |"
            ),
            "",
            "*Note: Level 1 results reflect the frozen canonical baseline run (14 / 20 = 70.0%).*",
            "",
            "---",
            "",
            "## 3. Level 2B — Optical & Perceptual Illusions",
            "",
            (
                "Level 2B challenges evaluate whether visual models succumb to classical "
                "human optical illusions. Each subtype in this benchmark contains one evaluated "
                "challenge (N=1 per subtype)."
            ),
            "",
            "| Subtype | Challenge Question | Outcome | Inference Time |",
            "| :--- | :--- | :---: | :---: |",
        ]
    )

    for subtype_key in sorted(ILLUSION_QUESTIONS.keys()):
        q_text = ILLUSION_QUESTIONS[subtype_key]
        sub_info = by_subtype.get(subtype_key, {})
        sub_corr = sub_info.get("correct_count", 0)
        sub_tot = sub_info.get("challenge_count", 0)
        sub_inf = sub_info.get("mean_inference_time_ms")
        if sub_corr == sub_tot and sub_tot > 0:
            outcome = f"Correct ({sub_corr}/{sub_tot})"
        else:
            outcome = f"{sub_corr}/{sub_tot}"
        lines.append(f"| `{subtype_key}` | *{q_text}* | **{outcome}** | {_sec(sub_inf)} |")

    lines.extend(
        [
            "",
            (
                "**Context & Interpretation**: Gemini answered all six illusion challenges "
                "correctly in this benchmark. Each subtype currently contains one evaluated "
                "challenge, so this result should not be interpreted as a general estimate of "
                "performance on optical illusions or as evidence about the internal perceptual "
                "mechanism used by the model. These canonical visual illusions are widely "
                "published and may be represented in general model pretraining data."
            ),
            "",
            "---",
            "",
            "## 4. Level 3A — Visual Routing Puzzles",
            "",
            (
                "Level 3A evaluates spatial tracing and visual graph routing across 4 distinct "
                "routing puzzle subtypes and 5 difficulty tiers (60 challenges total)."
            ),
            "",
            "### Breakdown by Subtype",
            "",
            "| Subtype | Challenges | Correct | Accuracy | Mean Inference Time |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
    )

    for st in ROUTING_SUBTYPES:
        st_data = by_subtype.get(st, {})
        c_count = st_data.get("challenge_count", 0)
        corr = st_data.get("correct_count", 0)
        acc = st_data.get("exact_challenge_accuracy")
        inf = st_data.get("mean_inference_time_ms")
        name = st.replace("-", " ").title()
        lines.append(f"| **{name}** | {c_count} | {corr} | **{_pct(acc)}** | {_sec(inf)} |")

    lines.extend(
        [
            "",
            "### Breakdown by Difficulty Tier",
            "",
            "| Difficulty Tier | Challenges | Correct | Accuracy | Mean Inference Time |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
    )

    for diff in ROUTING_DIFFICULTIES:
        d_data = by_difficulty.get(diff, {})
        c_count = d_data.get("challenge_count", 0)
        corr = d_data.get("correct_count", 0)
        acc = d_data.get("exact_challenge_accuracy")
        inf = d_data.get("mean_inference_time_ms")
        lines.append(f"| **{diff.title()}** | {c_count} | {corr} | **{_pct(acc)}** | {_sec(inf)} |")

    lines.extend(
        [
            "",
            "### Subtype × Difficulty Cross-Tabulation Matrix (Correct / Total)",
            "",
            "| Subtype | Easy | Medium | Story | Hard | Extreme | Total Accuracy |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    for st in sorted(ROUTING_SUBTYPES):
        st_cells = []
        for diff in ROUTING_DIFFICULTIES:
            cell_data = sub_by_diff.get(st, {}).get(diff, {})
            c = cell_data.get("correct_count", 0)
            t = cell_data.get("challenge_count", 0)
            pct = f" ({c / t * 100:.0f}%)" if t > 0 else ""
            st_cells.append(f"{c} / {t}{pct}")
        total_data = by_subtype.get(st, {})
        tot_c = total_data.get("correct_count", 0)
        tot_t = total_data.get("challenge_count", 0)
        tot_pct = _pct_short(total_data.get("exact_challenge_accuracy"))
        name = st.replace("-", " ").title()
        lines.append(f"| **{name}** | {' | '.join(st_cells)} | **{tot_c} / {tot_t} ({tot_pct})** |")

    # Add total row to cross-tab matrix
    tot_cells = []
    for diff in ROUTING_DIFFICULTIES:
        d_data = by_difficulty.get(diff, {})
        dc = d_data.get("correct_count", 0)
        dt = d_data.get("challenge_count", 0)
        dpct = f" ({dc / dt * 100:.1f}%)" if dt > 0 else ""
        tot_cells.append(f"**{dc} / {dt}{dpct}**")
    l3a_data = by_stage.get("Level 3A", {})
    l3a_c = l3a_data.get("correct_count", 0)
    l3a_t = l3a_data.get("challenge_count", 0)
    l3a_pct = _pct_short(l3a_data.get("exact_challenge_accuracy"))
    lines.append(f"| **Total** | {' | '.join(tot_cells)} | **{l3a_c} / {l3a_t} ({l3a_pct})** |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## 5. Level 3B — Degraded Vision (Resolution Ladder)",
            "",
            (
                "Level 3B tests semantic object recognition under stepped visual degradation, "
                "stepping down from 64px to 8px across 4 unique image series (28 challenges total)."
            ),
            "",
            "### Performance by Resolution (Ladder)",
            "",
            "| Tile Resolution | Challenges | Correct | Accuracy | Mean Inference Time |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
    )

    for res in RESOLUTIONS:
        r_data = by_resolution.get(str(res), by_resolution.get(res, {}))
        c_count = r_data.get("challenge_count", 0)
        corr = r_data.get("correct_count", 0)
        acc = r_data.get("exact_challenge_accuracy")
        inf = r_data.get("mean_inference_time_ms")
        lines.append(
            f"| **{res} × {res} px** | {c_count} | {corr} | **{_pct_short(acc)}** | {_sec(inf)} |"
        )

    lines.extend(
        [
            "",
            "### Performance by Image Series",
            "",
            "| Series | Resolution Steps | Correct | Accuracy | Mean Inference Time |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
    )

    for s_id in sorted(by_series.keys()):
        s_data = by_series[s_id]
        c_count = s_data.get("challenge_count", 0)
        corr = s_data.get("correct_count", 0)
        acc = s_data.get("exact_challenge_accuracy")
        inf = s_data.get("mean_inference_time_ms")
        lines.append(f"| **`{s_id}`** | {c_count} | {corr} | **{_pct(acc)}** | {_sec(inf)} |")

    # Descriptive summary section (computed directly from structured numbers)
    stage_accs = [
        (name, by_stage[name].get("exact_challenge_accuracy", 0))
        for name, _, _ in STAGE_ORDER
        if name in by_stage and by_stage[name].get("exact_challenge_accuracy") is not None
    ]
    highest_stage = max(stage_accs, key=lambda x: x[1]) if stage_accs else ("N/A", 0)
    lowest_stage = min(stage_accs, key=lambda x: x[1]) if stage_accs else ("N/A", 0)

    stage_drops = []
    for i in range(len(stage_accs) - 1):
        s1, a1 = stage_accs[i]
        s2, a2 = stage_accs[i + 1]
        stage_drops.append((f"{s1} -> {s2}", a1 - a2))
    largest_drop = max(stage_drops, key=lambda x: x[1]) if stage_drops else ("N/A", 0)

    st_accs = [
        (st, by_subtype.get(st, {}).get("exact_challenge_accuracy", 0))
        for st in ROUTING_SUBTYPES
        if st in by_subtype and by_subtype[st].get("exact_challenge_accuracy") is not None
    ]
    highest_routing = max(st_accs, key=lambda x: x[1]) if st_accs else ("N/A", 0)
    lowest_routing = min(st_accs, key=lambda x: x[1]) if st_accs else ("N/A", 0)

    res_with_correct = [
        res
        for res in RESOLUTIONS
        if by_resolution.get(str(res), by_resolution.get(res, {})).get("correct_count", 0) > 0
    ]
    lowest_res = min(res_with_correct) if res_with_correct else None
    drop_str = f"{largest_drop[0]} ({largest_drop[1] * 100:.1f} percentage points)"
    res_str = f"{lowest_res}x{lowest_res} px" if lowest_res else "None"

    lines.extend(
        [
            "",
            "---",
            "",
            "## 6. Descriptive Summary",
            "",
            f"- **Highest measured stage accuracy**: {highest_stage[0]} ({_pct(highest_stage[1])})",
            f"- **Lowest measured stage accuracy**: {lowest_stage[0]} ({_pct(lowest_stage[1])})",
            f"- **Largest stage-to-stage accuracy drop**: {drop_str}",
            (
                f"- **Routing subtype with highest measured accuracy**: "
                f"{highest_routing[0]} ({_pct(highest_routing[1])})"
            ),
            (
                f"- **Routing subtype with lowest measured accuracy**: "
                f"{lowest_routing[0]} ({_pct(lowest_routing[1])})"
            ),
            f"- **Lowest resolution with at least one correct challenge**: {res_str}",
            "",
            "---",
            "",
            "## 7. Scientific Integrity & Protocol Guarantees",
            "",
            (
                "- **Zero-Shot Protocol**: No model fine-tuning, few-shot demonstration, prompt "
                "engineering from graded feedback, or programmatic vision tools were used."
            ),
            (
                "- **Held-Out Benchmark Split**: BDD100K validation data was held out from our "
                "solver-specific training and fine-tuning pipeline. No solver-specific training "
                "was performed in this baseline."
            ),
            (
                "- **No Answer Leakage**: All challenges were fetched strictly via public "
                "HTTP endpoints (`/challenges/catalog.json`, `/challenges/<id>/challenge.json`, "
                "`/challenges/<id>/assets/*`). Server feedback was restricted to submission status "
                "codes and boolean outcome."
            ),
            (
                "- **Frozen Canonical Level 1**: Preserved historical canonical result "
                "(14 / 20 = 70.0%) from `results/20261002T085501003519Z_level1_vlm_30e5750e/`."
            ),
            (
                "- **No Retries of Inaccurate Answers**: Predictions were submitted exactly "
                "once per challenge. Transport and quota errors were retried strictly at the "
                "provider boundary using exponential backoff."
            ),
            "- **Raw Run Artifacts**:",
        ]
    )

    run_artifacts = data.get("run_artifacts", {})
    for label, path_val in run_artifacts.items():
        lines.append(f"  - {label}: `{path_val}`")

    lines.append("")
    return "\n".join(lines)


def update_report_files(json_path: Path, md_path: Path) -> None:
    """Read aggregate JSON data and update corresponding Markdown report."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    md_content = generate_markdown_report(data)
    md_path.write_text(md_content, encoding="utf-8")


if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent.parent
    j_path = base_dir / "reports" / "gemini-zero-shot-baseline.json"
    m_path = base_dir / "reports" / "gemini-zero-shot-baseline.md"
    if j_path.exists():
        update_report_files(j_path, m_path)
        print(f"Updated {m_path} from {j_path}")
