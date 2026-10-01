"""Developer Visual QA Tool: Contact sheet generator for visual inspection of challenges.

Produces standalone HTML contact sheets with rendered tiles, target bounding box overlays,
rendered dimensions, crop windows, and difficulty metadata.
Usage:
    python challenges/scripts/generate_visual_qa.py --input challenges/generated --output challenges/visual_qa_report.html
"""

from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw


def encode_image_base64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def draw_bounding_box_overlay(img: Image.Image, box: list[float] | None, color: str = "#22c55e", width: int = 3) -> Image.Image:
    if not box:
        return img
    annotated = img.copy()
    draw = ImageDraw.Draw(annotated)
    x1, y1, x2, y2 = [int(v) for v in box]
    draw.rectangle([x1, y1, x2, y2], outline=color, width=width)
    return annotated


def generate_visual_qa_html(challenges_dir: Path, output_file: Path, max_per_level: int = 6) -> None:
    sections: list[str] = []

    level_dirs = sorted([d for d in challenges_dir.iterdir() if d.is_dir()])
    total_challenges = 0

    for l_dir in level_dirs:
        c_dirs = sorted([d for d in l_dir.iterdir() if d.is_dir() and (d / "challenge.json").exists()])
        if not c_dirs:
            # Check if l_dir itself is a challenge directory
            if (l_dir / "challenge.json").exists():
                c_dirs = [l_dir]

        level_cards: list[str] = []
        for c_dir in c_dirs[:max_per_level]:
            total_challenges += 1
            pub_data = json.loads((c_dir / "challenge.json").read_text(encoding="utf-8"))
            priv_data = json.loads((c_dir / "answer.json").read_text(encoding="utf-8"))

            c_id = pub_data.get("id", c_dir.name)
            instruction = pub_data.get("instruction", "")
            target_class = priv_data.get("targetClass", priv_data.get("target", "N/A"))
            variant = pub_data.get("variant", "")

            tiles_html: list[str] = []
            tiles = priv_data.get("tiles")

            if tiles:
                for t in tiles:
                    idx = t.get("tileIndex", 0)
                    is_pos = t.get("isPositive", False)
                    asset_rel = t.get("asset", f"assets/{idx:02d}.webp")
                    asset_file = c_dir / asset_rel
                    rendered_dim = t.get("rendered_object_size")
                    diff_factors = t.get("difficulty_budget_factors", t.get("attributes", []))
                    weather = t.get("weather", "N/A")
                    tod = t.get("timeofday", "N/A")

                    img_b64 = ""
                    if asset_file.exists():
                        with Image.open(asset_file) as im:
                            img_b64 = encode_image_base64(im)

                    border_color = "border-emerald-500 ring-2 ring-emerald-500/50" if is_pos else "border-slate-700"
                    badge = f'<span class="bg-emerald-500/20 text-emerald-300 text-xs px-1.5 py-0.5 rounded font-mono font-medium">POSITIVE</span>' if is_pos else f'<span class="bg-slate-700/60 text-slate-400 text-xs px-1.5 py-0.5 rounded font-mono">NEGATIVE</span>'
                    rendered_badge = f'<span class="text-xs text-amber-300 font-mono">Target: {rendered_dim:.0f}px</span>' if rendered_dim else ""
                    factors_badge = " ".join([f'<span class="bg-slate-800 text-slate-300 text-[10px] px-1 py-0.5 rounded font-mono">{f}</span>' for f in diff_factors[:3]])

                    tiles_html.append(f"""
                    <div class="flex flex-col bg-slate-900 rounded-lg p-2 border {border_color}">
                        <div class="relative aspect-square w-full bg-slate-950 rounded overflow-hidden">
                            <img src="data:image/webp;base64,{img_b64}" class="w-full h-full object-contain" alt="Tile {idx}" />
                            <div class="absolute top-1 left-1">{badge}</div>
                            <div class="absolute bottom-1 right-1">{rendered_badge}</div>
                        </div>
                        <div class="mt-2 text-xs text-slate-400 flex flex-col gap-1">
                            <div class="flex justify-between items-center">
                                <span class="font-mono text-slate-500">#{idx:02d}</span>
                                <span class="font-mono text-[11px] text-slate-400">{tod} / {weather}</span>
                            </div>
                            <div class="flex flex-wrap gap-1 mt-0.5">{factors_badge}</div>
                        </div>
                    </div>
                    """)
                grid_cols = "grid-cols-3" if pub_data.get("ui", {}).get("columns") == 3 else "grid-cols-4"
                content_html = f'<div class="grid {grid_cols} gap-3 mt-3">{"".join(tiles_html)}</div>'
            else:
                # Single-asset challenge (Level 2B or Level 3A)
                rel_asset = pub_data.get("assets", ["assets/00.webp"])[0]
                asset_file = c_dir / rel_asset
                img_b64 = ""
                if asset_file.exists():
                    with Image.open(asset_file) as im:
                        img_b64 = encode_image_base64(im)

                answer_str = str(priv_data.get("answer", "N/A"))
                explanation = ""
                if priv_data.get("illusion"):
                    explanation = priv_data["illusion"].get("explanation", "")
                elif priv_data.get("annotations"):
                    dm = priv_data["annotations"].get("difficultyMetadata", {})
                    explanation = f"Cables: {dm.get('cableCount')}, Crossings: {dm.get('crossingCount')}, LineWidth: {dm.get('lineWidth')}px"

                content_html = f"""
                <div class="mt-3 flex flex-col md:flex-row gap-4 bg-slate-900 p-3 rounded-lg border border-slate-800">
                    <div class="max-w-md w-full bg-slate-950 rounded overflow-hidden">
                        <img src="data:image/webp;base64,{img_b64}" class="w-full h-auto object-contain" alt="{c_id}" />
                    </div>
                    <div class="flex-1 text-sm text-slate-300 flex flex-col gap-2">
                        <div class="text-xs font-mono text-slate-500">Ground Truth Answer:</div>
                        <div class="text-base font-semibold text-emerald-400 font-mono">{answer_str}</div>
                        <div class="text-xs text-slate-400 mt-2 leading-relaxed bg-slate-950/60 p-2.5 rounded border border-slate-800/80">{explanation}</div>
                    </div>
                </div>
                """

            level_cards.append(f"""
            <div class="bg-slate-900/60 border border-slate-800 rounded-xl p-4 shadow-lg mb-6">
                <div class="flex items-baseline justify-between border-b border-slate-800 pb-2 mb-2">
                    <div>
                        <span class="text-xs font-mono text-indigo-400 font-semibold">{c_id}</span>
                        <span class="ml-2 text-xs font-mono text-slate-400">variant: {variant}</span>
                        <span class="ml-2 text-xs font-mono text-emerald-400">target: {target_class}</span>
                    </div>
                </div>
                <div class="text-sm font-medium text-slate-200">{instruction}</div>
                {content_html}
            </div>
            """)

        sections.append(f"""
        <section class="mb-12">
            <h2 class="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <span class="w-3 h-3 rounded-full bg-indigo-500"></span>
                Level: {l_dir.name} ({len(c_dirs)} challenges)
            </h2>
            {"".join(level_cards)}
        </section>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CAPTCHA Visual QA Contact Sheet</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
        <header class="border-b border-slate-800 pb-6 mb-8">
            <h1 class="text-3xl font-black tracking-tight text-white flex items-center gap-3">
                <span>CAPTCHA Visual QA</span>
                <span class="bg-indigo-500/20 text-indigo-400 text-sm px-2.5 py-1 rounded-full font-mono font-medium">Developer Inspection</span>
            </h1>
            <p class="text-sm text-slate-400 mt-2">
                Inspection contact sheet with target labels, aspect-ratio preserved context crops, and ground-truth metadata.
            </p>
        </header>

        <main>
            {"".join(sections)}
        </main>
    </div>
</body>
</html>
"""
    output_file.write_text(html_content, encoding="utf-8")
    print(f"Visual QA contact sheet generated at: {output_file} ({total_challenges} challenges inspected)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Visual QA HTML contact sheet")
    parser.add_argument("--input", default="challenges/generated", help="Directory containing generated challenges")
    parser.add_argument("--output", default="challenges/visual_qa_report.html", help="Path to output HTML report")
    parser.add_argument("--max-per-level", type=int, default=6, help="Maximum challenges to render per level")
    args = parser.parse_args()

    generate_visual_qa_html(Path(args.input), Path(args.output), max_per_level=args.max_per_level)
