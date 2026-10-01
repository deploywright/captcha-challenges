"""Script to generate the Level 3A Routing Puzzles development batch (40 challenges)

Subtypes generated:
- 10 Laser Maze (2 easy, 6 medium, 2 hard)
- 10 Conveyor Routing (2 easy, 6 medium, 2 hard)
- 10 Pipe Flow (2 easy, 6 medium, 2 hard)
- 10 Device Cables (2 easy, 6 medium, 2 hard)

Outputs:
- Challenges to challenges/generated/level-3a/
- Visual QA HTML report to challenges/level_3a_visual_qa.html (developer only)
"""

from __future__ import annotations

import base64
import html
import io
import json
from pathlib import Path
from PIL import Image

from challenge_engine.core.config import PROJECT_ROOT
from challenge_engine.core.exporter import export_challenge_bundle
from challenge_engine.core.schemas import Level3AConfig
from challenge_engine.core.validation import validate_single_challenge_dir, validate_generated_directory
from challenge_engine.levels.level_3a.conveyor_routing import ConveyorRoutingGenerator
from challenge_engine.levels.level_3a.device_cables import DeviceCablesGenerator
from challenge_engine.levels.level_3a.laser_maze import LaserMazeGenerator
from challenge_engine.levels.level_3a.pipe_flow import PipeFlowGenerator


def main() -> None:
    generated_dir = PROJECT_ROOT / "generated" / "level-3a"
    generated_dir.mkdir(parents=True, exist_ok=True)

    # Subtype generators and their seed/difficulty configs
    subtypes = [
        ("laser-maze", LaserMazeGenerator, 300),
        ("conveyor-routing", ConveyorRoutingGenerator, 310),
        ("pipe-flow", PipeFlowGenerator, 320),
        ("device-cables", DeviceCablesGenerator, 330),
    ]

    diff_schedule = [
        ("easy", 2),
        ("medium", 6),
        ("hard", 2),
    ]

    all_bundles = []
    qa_cards = []

    print("Generating Level 3A Routing Puzzles batch (40 challenges)...")

    for subtype_name, gen_cls, base_seed in subtypes:
        seed_offset = 0
        for diff, count in diff_schedule:
            cfg = Level3AConfig(
                defaultSubtype=subtype_name,
                subtype=subtype_name,
                difficulty=diff,
            )
            gen = gen_cls(cfg)

            for i in range(count):
                curr_seed = base_seed + seed_offset
                seed_offset += 1

                bundle = gen.generate_one(curr_seed)

                # Export to disk under challenges/generated/level-3a/<id>/
                export_path = export_challenge_bundle(
                    bundle,
                    output_root=PROJECT_ROOT / "generated",
                    overwrite=True,
                    organize_by_level=True,
                    update_manifest=False,
                )

                val_res = validate_single_challenge_dir(export_path, check_determinism=False)
                if not val_res.passed:
                    raise RuntimeError(f"Validation failed for {bundle.public_challenge.id}: {val_res.errors}")

                all_bundles.append(bundle)

                # Prepare QA report data
                img = bundle.assets[bundle.public_challenge.assets[0]]
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                b64_img = base64.b64encode(buf.getvalue()).decode("ascii")

                routing_summary = ""
                if bundle.private_answer.routing:
                    r = bundle.private_answer.routing
                    if subtype_name == "laser-maze":
                        routing_summary = f"Reflections: {len(r.get('mirrorHits', []))} | Target: {r.get('finalTarget')} | Status: {r.get('exitStatus')}"
                    elif subtype_name == "conveyor-routing":
                        routing_summary = f"Path: {' -> '.join(r.get('solutionPath', []))} | Switches: {len(r.get('switchStates', {}))}"
                    elif subtype_name == "pipe-flow":
                        routing_summary = f"Open valves: {len(r.get('openValves', []))} | Closed: {len(r.get('closedValves', []))} | Target: {r.get('targetTank')}"
                    elif subtype_name == "device-cables":
                        routing_summary = f"Query: {r.get('queryDevice')} <-> {r.get('queryOutlet')} | Total cables: {r.get('cableCount')}"

                qa_cards.append({
                    "id": bundle.public_challenge.id,
                    "subtype": subtype_name,
                    "difficulty": diff,
                    "seed": curr_seed,
                    "instruction": bundle.public_challenge.instruction,
                    "options": bundle.public_challenge.ui.options,
                    "answer": bundle.private_answer.answer,
                    "routing_summary": routing_summary,
                    "img_b64": b64_img,
                })

                print(f"  [OK] {bundle.public_challenge.id} ({subtype_name}, {diff}, seed={curr_seed}) -> answer: {bundle.private_answer.answer}")

    print(f"Successfully exported {len(all_bundles)} Level 3A challenges.")

    # Validate Level 3A generated directory
    report = validate_generated_directory(PROJECT_ROOT / "generated" / "level-3a", check_determinism=False)
    if not report.is_valid:
        print("Validation report errors:")
        for err in report.global_errors:
            print("  - Global:", err)
        for r in report.results:
            if not r.passed:
                for err in r.errors:
                    print(f"  - [{r.challenge_id}]:", err)
        raise RuntimeError("Generated directory validation failed!")
    print(f"Generated directory validation PASSED: {report.total_count} total challenges across all levels ({report.passed_count} passed).")

    # Generate Visual QA HTML Contact Sheet
    qa_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Level 3A Routing Puzzles — Visual QA Report</title>
<style>
  body {{
    background: #0f172a;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0;
    padding: 24px;
  }}
  h1 {{
    color: #38bdf8;
    margin-bottom: 8px;
  }}
  .meta {{
    color: #94a3b8;
    font-size: 14px;
    margin-bottom: 24px;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(540px, 1fr));
    gap: 20px;
  }}
  .card {{
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
  }}
  .badge-laser {{ background: #7c2d12; color: #fdba74; }}
  .badge-conveyor {{ background: #14532d; color: #86efac; }}
  .badge-pipe {{ background: #1e3a8a; color: #93c5fd; }}
  .badge-cables {{ background: #581c87; color: #d8b4fe; }}
  .badge-easy {{ background: #064e3b; color: #6ee7b7; }}
  .badge-medium {{ background: #78350f; color: #fde68a; }}
  .badge-hard {{ background: #7f1d1d; color: #fca5a5; }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .img-container {{
    background: #090d16;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid #0f172a;
  }}
  .img-container img {{
    width: 100%;
    height: auto;
    display: block;
  }}
  .instruction {{
    font-size: 14px;
    font-weight: 600;
    color: #f1f5f9;
  }}
  .answer-box {{
    background: #090d16;
    padding: 10px;
    border-radius: 6px;
    border: 1px solid #1e293b;
    font-size: 12px;
    font-family: monospace;
  }}
  .answer-box .ans {{
    color: #4ade80;
    font-weight: bold;
  }}
</style>
</head>
<body>
<h1>Level 3A Routing Puzzles — Visual QA Contact Sheet</h1>
<div class="meta">Total Samples: {len(qa_cards)} | Generated from deterministic seeds | Held-out benchmark quality</div>

<div class="grid">
"""
    for c in qa_cards:
        st = c["subtype"]
        badge_cls = "badge-laser" if "laser" in st else ("badge-conveyor" if "conveyor" in st else ("badge-pipe" if "pipe" in st else "badge-cables"))
        diff_cls = f"badge-{c['difficulty']}"

        qa_html += f"""
  <div class="card">
    <div class="header">
      <div>
        <span class="badge {badge_cls}">{c['subtype']}</span>
        <span class="badge {diff_cls}">{c['difficulty']}</span>
        <span style="font-family: monospace; font-size: 12px; color: #94a3b8; margin-left: 6px;">{c['id']} (seed {c['seed']})</span>
      </div>
    </div>
    <div class="img-container">
      <img src="data:image/jpeg;base64,{c['img_b64']}" alt="{c['id']}" />
    </div>
    <div class="instruction">{html.escape(c['instruction'])}</div>
    <div class="answer-box">
      <div>Options: {html.escape(str(c['options']))}</div>
      <div style="margin-top: 4px;">Correct Answer: <span class="ans">{html.escape(str(c['answer']))}</span></div>
      <div style="margin-top: 4px; color: #94a3b8;">Route: {html.escape(c['routing_summary'])}</div>
    </div>
  </div>
"""

    qa_html += """
</div>
</body>
</html>
"""

    qa_path = PROJECT_ROOT / "level_3a_visual_qa.html"
    qa_path.write_text(qa_html, encoding="utf-8")
    print(f"Visual QA Contact Sheet generated: {qa_path}")


if __name__ == "__main__":
    main()
