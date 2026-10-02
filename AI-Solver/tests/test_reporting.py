import json

from ai_solver.reporting import generate_markdown_report, update_report_files


def sample_metrics_data():
    return {
        "model": "gemini-3.5-flash-lite",
        "provider": "Google GenAI",
        "thinking_level": "MINIMAL",
        "total_challenges": 134,
        "evaluated_challenges": 134,
        "correct_challenges": 75,
        "error_count": 0,
        "micro_accuracy": 75 / 134,
        "macro_stage_accuracy": 0.58,
        "metrics": {
            "mean_inference_time_ms": 4500.0,
            "by_stage": {
                "Level 1": {
                    "challenge_count": 20,
                    "evaluated_count": 20,
                    "correct_count": 14,
                    "exact_challenge_accuracy": 0.70,
                    "mean_inference_time_ms": 6110.0,
                },
                "Level 2A": {
                    "challenge_count": 20,
                    "evaluated_count": 20,
                    "correct_count": 10,
                    "exact_challenge_accuracy": 0.50,
                    "mean_inference_time_ms": 5000.0,
                },
                "Level 2B": {
                    "challenge_count": 6,
                    "evaluated_count": 6,
                    "correct_count": 6,
                    "exact_challenge_accuracy": 1.0,
                    "mean_inference_time_ms": 3000.0,
                },
                "Level 3A": {
                    "challenge_count": 60,
                    "evaluated_count": 60,
                    "correct_count": 30,
                    "exact_challenge_accuracy": 0.50,
                    "mean_inference_time_ms": 4000.0,
                },
                "Level 3B": {
                    "challenge_count": 28,
                    "evaluated_count": 28,
                    "correct_count": 15,
                    "exact_challenge_accuracy": 15 / 28,
                    "mean_inference_time_ms": 3500.0,
                },
            },
            "by_subtype": {
                "pipe-flow": {
                    "challenge_count": 15,
                    "correct_count": 8,
                    "exact_challenge_accuracy": 8 / 15,
                    "mean_inference_time_ms": 4100.0,
                },
                "conveyor-routing": {
                    "challenge_count": 15,
                    "correct_count": 7,
                    "exact_challenge_accuracy": 7 / 15,
                    "mean_inference_time_ms": 4200.0,
                },
                "laser-maze": {
                    "challenge_count": 15,
                    "correct_count": 9,
                    "exact_challenge_accuracy": 9 / 15,
                    "mean_inference_time_ms": 3900.0,
                },
                "device-cables": {
                    "challenge_count": 15,
                    "correct_count": 6,
                    "exact_challenge_accuracy": 6 / 15,
                    "mean_inference_time_ms": 4000.0,
                },
                "checker-shadow": {
                    "challenge_count": 1,
                    "correct_count": 1,
                    "exact_challenge_accuracy": 1.0,
                    "mean_inference_time_ms": 2800.0,
                },
            },
            "by_difficulty": {
                "easy": {
                    "challenge_count": 12,
                    "correct_count": 10,
                    "exact_challenge_accuracy": 10 / 12,
                    "mean_inference_time_ms": 3500.0,
                },
                "medium": {
                    "challenge_count": 12,
                    "correct_count": 8,
                    "exact_challenge_accuracy": 8 / 12,
                    "mean_inference_time_ms": 3800.0,
                },
                "story": {
                    "challenge_count": 12,
                    "correct_count": 6,
                    "exact_challenge_accuracy": 6 / 12,
                    "mean_inference_time_ms": 4000.0,
                },
                "hard": {
                    "challenge_count": 12,
                    "correct_count": 4,
                    "exact_challenge_accuracy": 4 / 12,
                    "mean_inference_time_ms": 4300.0,
                },
                "extreme": {
                    "challenge_count": 12,
                    "correct_count": 2,
                    "exact_challenge_accuracy": 2 / 12,
                    "mean_inference_time_ms": 4500.0,
                },
            },
            "subtype_by_difficulty": {
                "pipe-flow": {"easy": {"challenge_count": 3, "correct_count": 3}},
            },
            "by_resolution": {
                "64": {
                    "challenge_count": 4,
                    "correct_count": 4,
                    "exact_challenge_accuracy": 1.0,
                    "mean_inference_time_ms": 3200.0,
                },
                "48": {
                    "challenge_count": 4,
                    "correct_count": 3,
                    "exact_challenge_accuracy": 0.75,
                    "mean_inference_time_ms": 3300.0,
                },
                "32": {
                    "challenge_count": 4,
                    "correct_count": 3,
                    "exact_challenge_accuracy": 0.75,
                    "mean_inference_time_ms": 3400.0,
                },
                "24": {
                    "challenge_count": 4,
                    "correct_count": 2,
                    "exact_challenge_accuracy": 0.50,
                    "mean_inference_time_ms": 3500.0,
                },
                "16": {
                    "challenge_count": 4,
                    "correct_count": 2,
                    "exact_challenge_accuracy": 0.50,
                    "mean_inference_time_ms": 3600.0,
                },
                "12": {
                    "challenge_count": 4,
                    "correct_count": 1,
                    "exact_challenge_accuracy": 0.25,
                    "mean_inference_time_ms": 3700.0,
                },
                "8": {
                    "challenge_count": 4,
                    "correct_count": 0,
                    "exact_challenge_accuracy": 0.0,
                    "mean_inference_time_ms": 3800.0,
                },
            },
            "by_series": {
                "series_01": {
                    "challenge_count": 7,
                    "correct_count": 4,
                    "exact_challenge_accuracy": 4 / 7,
                    "mean_inference_time_ms": 3500.0,
                },
            },
        },
        "run_artifacts": {
            "Level 1": "results/20261002T085501003519Z_level1_vlm_30e5750e",
        },
    }


def test_markdown_report_matches_json_metrics():
    data = sample_metrics_data()
    md = generate_markdown_report(data)

    assert "# Zero-Shot Gemini 3.5 Flash Lite Baseline Report" in md
    assert "gemini-3.5-flash-lite" in md
    assert "75 / 134" in md
    assert "55.97%" in md
    assert "58.00%" in md
    assert "| **Level 1** | `street-grid` | Image Selection | 20 | 14 | **70.0%** |" in md
    assert "| **Level 2A** | `hard-street-grid` | Image Selection | 20 | 10 | **50.0%** |" in md
    assert "| **Level 2B** | `checker-shadow` | Single Choice | 6 | 6 | **100.0%** |" in md
    assert "| **Level 3A** | `routing-puzzle` | Single Choice | 60 | 30 | **50.0%** |" in md
    assert "| **64 × 64 px** | 4 | 4 | **100.0%** | 3.20 s |" in md
    assert "| **8 × 8 px** | 4 | 0 | **0.0%** | 3.80 s |" in md


def test_update_report_files(tmp_path):
    data = sample_metrics_data()
    json_path = tmp_path / "baseline.json"
    md_path = tmp_path / "baseline.md"

    json_path.write_text(json.dumps(data), encoding="utf-8")
    update_report_files(json_path, md_path)

    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")
    assert "Zero-Shot Gemini 3.5 Flash Lite Baseline Report" in content
    assert "75 / 134" in content
