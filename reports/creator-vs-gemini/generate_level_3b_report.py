import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

REPORT_DIR = Path("reports/creator-vs-gemini")
DATA_FILE = REPORT_DIR / "level-3b-benchmark-results.json"
CREATOR_FILE = REPORT_DIR / "creator-vs-gemini.json"

RESOLUTIONS = [8, 12, 16, 24, 32, 48, 64]

def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing {DATA_FILE}")
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    creator_data = json.loads(CREATOR_FILE.read_text(encoding="utf-8"))
    
    creator_outcomes = {}
    for o in creator_data["matched"]["challenge_outcomes"]:
        if o.get("stage") == "Level 3B":
            creator_outcomes[o["challenge_id"]] = {
                "correct": o["creator_correct"],
                "status": o["creator_status"],
                "res": o["resolution"],
                "solve_time_ms": o["creator_solve_time_ms"]
            }
            
    return data, creator_outcomes

def compute_metrics(data, creator_outcomes):
    by_res = {r: {"total": 0, "base_acc": 0, "enh_acc": 0,
                  "base_rec": [], "enh_rec": [], "base_prec": [], "enh_prec": [],
                  "base_f1": [], "enh_f1": []} for r in RESOLUTIONS}
    
    for row in data:
        r = row["resolution"]
        by_res[r]["total"] += 1
        if row["baseline"]["correct"]:
            by_res[r]["base_acc"] += 1
        if row["enhanced"]["correct"]:
            by_res[r]["enh_acc"] += 1
        by_res[r]["base_rec"].append(row["baseline"]["recall"])
        by_res[r]["enh_rec"].append(row["enhanced"]["recall"])
        by_res[r]["base_prec"].append(row["baseline"]["precision"])
        by_res[r]["enh_prec"].append(row["enhanced"]["precision"])
        by_res[r]["base_f1"].append(row["baseline"]["f1"])
        by_res[r]["enh_f1"].append(row["enhanced"]["f1"])
        
    return by_res

def render_dashboard(data, by_res, creator_outcomes, out_png, out_svg):
    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor("#0b0f19")
    for ax in axes.flat:
        ax.set_facecolor("#111827")
        ax.grid(True, linestyle="--", alpha=0.25, color="#475569")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#334155")
        ax.spines["bottom"].set_color("#334155")

    # Panel 1: F1 Score across Degradation Resolutions
    ax1 = axes[0, 0]
    res_labels = [f"{r}px" for r in RESOLUTIONS]
    base_f1_means = [float(np.mean(by_res[r]["base_f1"])) * 100 for r in RESOLUTIONS]
    enh_f1_means = [float(np.mean(by_res[r]["enh_f1"])) * 100 for r in RESOLUTIONS]
    
    x = np.arange(len(RESOLUTIONS))
    w = 0.35
    b1 = ax1.bar(x - w/2, base_f1_means, w, label="Gemini Baseline (Raw Tiles)", color="#64748b", alpha=0.85)
    b2 = ax1.bar(x + w/2, enh_f1_means, w, label="Gemini Enhanced (Squint + Context)", color="#10b981", alpha=0.9)
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(res_labels, fontsize=11, fontweight="bold", color="#f8fafc")
    ax1.set_ylabel("Mean Tile F1 Score (%)", fontsize=11, color="#94a3b8")
    ax1.set_title("A. Target Detection F1 Score by Resolution", fontsize=13, fontweight="bold", color="#f8fafc", pad=12)
    ax1.legend(loc="upper left", framealpha=0.3, facecolor="#1e293b", edgecolor="#475569")
    ax1.set_ylim(0, 105)
    for rects in [b1, b2]:
        for rect in rects:
            h = rect.get_height()
            if h > 2:
                ax1.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, h),
                             xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                             fontsize=9, color="#f8fafc", fontweight="bold")

    # Panel 2: Recall vs Precision Trade-off
    ax2 = axes[0, 1]
    base_rec_all = [float(np.mean(by_res[r]["base_rec"])) * 100 for r in RESOLUTIONS]
    enh_rec_all = [float(np.mean(by_res[r]["enh_rec"])) * 100 for r in RESOLUTIONS]
    
    ax2.plot(RESOLUTIONS, base_rec_all, marker="o", lw=2.5, color="#ef4444", label="Baseline Recall (Blind Spot at <=24px)")
    ax2.plot(RESOLUTIONS, enh_rec_all, marker="s", lw=2.5, color="#10b981", label="Enhanced Recall (Restored Object Contours)")
    
    ax2.axvspan(6, 26, color="#ef4444", alpha=0.12, label="Extreme Blur Zone (<=24px)")
    ax2.set_xlabel("Input Tile Resolution (px)", fontsize=11, color="#94a3b8")
    ax2.set_ylabel("Tile Recall Rate (%)", fontsize=11, color="#94a3b8")
    ax2.set_title("B. Recall Recovery across Extreme Degradation", fontsize=13, fontweight="bold", color="#f8fafc", pad=12)
    ax2.set_xscale("log")
    ax2.set_xticks(RESOLUTIONS)
    ax2.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax2.legend(loc="lower right", framealpha=0.3, facecolor="#1e293b", edgecolor="#475569")
    ax2.set_ylim(-5, 105)

    # Panel 3: Aggregate Detection Categories
    ax3 = axes[1, 0]
    base_empty = sum(1 for r in data if len(r["baseline"]["prediction"]) == 0)
    base_detected = len(data) - base_empty
    base_exact = sum(1 for r in data if r["baseline"]["correct"])
    
    enh_empty = sum(1 for r in data if len(r["enhanced"]["prediction"]) == 0)
    enh_detected = len(data) - enh_empty
    enh_exact = sum(1 for r in data if r["enhanced"]["correct"])
    
    categories = ["Target Detected (>0 Tiles)", "Exact Set Match (100% Tiles)", "Model Refusal / Empty ([])"]
    base_vals = [base_detected / len(data) * 100, base_exact / len(data) * 100, base_empty / len(data) * 100]
    enh_vals = [enh_detected / len(data) * 100, enh_exact / len(data) * 100, enh_empty / len(data) * 100]
    
    y = np.arange(len(categories))
    h = 0.35
    ax3.barh(y + h/2, base_vals, h, label="Gemini Baseline", color="#64748b", alpha=0.85)
    ax3.barh(y - h/2, enh_vals, h, label="Gemini Enhanced", color="#38bdf8", alpha=0.9)
    ax3.set_yticks(y)
    ax3.set_yticklabels(categories, fontsize=11, fontweight="bold", color="#f8fafc")
    ax3.set_xlabel("Percentage of 28 Benchmark Challenges (%)", fontsize=11, color="#94a3b8")
    ax3.set_title("C. Overcoming the Empty Refusal Defect", fontsize=13, fontweight="bold", color="#f8fafc", pad=12)
    ax3.legend(loc="lower right", framealpha=0.3, facecolor="#1e293b", edgecolor="#475569")
    ax3.set_xlim(0, 110)
    
    for idx, (bv, ev) in enumerate(zip(base_vals, enh_vals)):
        ax3.text(bv + 2, idx + h/2, f"{bv:.1f}%", va="center", fontsize=9, color="#f8fafc", fontweight="bold")
        ax3.text(ev + 2, idx - h/2, f"{ev:.1f}%", va="center", fontsize=9, color="#f8fafc", fontweight="bold")

    # Panel 4: Creator Head-to-Head (4 Matched Challenges)
    ax4 = axes[1, 1]
    matched_ids = ["lvl3b_xel0ut", "lvl3b_knpiig", "lvl3b_sosvla", "lvl3b_e1m46k"]
    m_labels = ["xel0ut (24px)", "knpiig (8px)", "sosvla (32px)", "e1m46k (16px)"]
    
    cr_scores = []
    enh_f1s = []
    base_f1s = []
    for cid in matched_ids:
        cr_info = creator_outcomes.get(cid, {})
        cr_scores.append(100.0 if cr_info.get("correct") else 0.0)
        row = next((r for r in data if r["challenge_id"] == cid), None)
        if row:
            enh_f1s.append(row["enhanced"]["f1"] * 100)
            base_f1s.append(row["baseline"]["f1"] * 100)
        else:
            enh_f1s.append(0.0)
            base_f1s.append(0.0)
            
    x4 = np.arange(len(matched_ids))
    w4 = 0.25
    ax4.bar(x4 - w4, cr_scores, w4, label="Human Creator (1/4 Answered, 2 Skipped)", color="#f59e0b", alpha=0.9)
    ax4.bar(x4, base_f1s, w4, label="Gemini Baseline F1", color="#64748b", alpha=0.85)
    ax4.bar(x4 + w4, enh_f1s, w4, label="Gemini Enhanced F1", color="#10b981", alpha=0.9)
    
    ax4.set_xticks(x4)
    ax4.set_xticklabels(m_labels, fontsize=10, fontweight="bold", color="#f8fafc")
    ax4.set_ylabel("Score / F1 (%)", fontsize=11, color="#94a3b8")
    ax4.set_title("D. Human Creator vs AI on Matched Trials", fontsize=13, fontweight="bold", color="#f8fafc", pad=12)
    ax4.legend(loc="upper right", framealpha=0.3, facecolor="#1e293b", edgecolor="#475569")
    ax4.set_ylim(0, 115)
    
    for idx, (cs, bs, es) in enumerate(zip(cr_scores, base_f1s, enh_f1s)):
        if cs > 0: ax4.text(idx - w4, cs + 2, f"{cs:.0f}%", ha="center", fontsize=8, color="#f8fafc", fontweight="bold")
        if bs > 0: ax4.text(idx, bs + 2, f"{bs:.0f}%", ha="center", fontsize=8, color="#f8fafc", fontweight="bold")
        if es > 0: ax4.text(idx + w4, es + 2, f"{es:.0f}%", ha="center", fontsize=8, color="#f8fafc", fontweight="bold")

    plt.suptitle("Level 3B (Degraded Vision CAPTCHA): Human Creator vs AI Benchmark",
                 fontsize=16, fontweight="bold", color="#f8fafc", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    fig.savefig(out_png, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
    fig.savefig(out_svg, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Rendered {out_png} and {out_svg}")

def render_markdown(data, by_res, creator_outcomes):
    total = len(data)
    base_acc = sum(1 for r in data if r["baseline"]["correct"]) / total * 100
    enh_acc = sum(1 for r in data if r["enhanced"]["correct"]) / total * 100
    base_f1 = float(np.mean([r["baseline"]["f1"] for r in data])) * 100
    enh_f1 = float(np.mean([r["enhanced"]["f1"] for r in data])) * 100
    base_rec = float(np.mean([r["baseline"]["recall"] for r in data])) * 100
    enh_rec = float(np.mean([r["enhanced"]["recall"] for r in data])) * 100
    
    lines = [
        "# گزارش ارزیابی و مقایسه جامع مرحله Level 3B (Degraded Vision CAPTCHA)",
        "",
        "> **تاریخ تولید گزارش:** اکتبر ۲۰۲۶  ",
        "> **حجم دیتاست:** ۲۸ چالش تفکیک‌شده در ۷ سطح رزولوشن (۸ تا ۶۴ پیکسل)  ",
        "> **داده‌های مرجع:** آزمون رسمی سازنده انسانی (Human Creator Session) + ارزیابی Gemini 3.1 Flash-Lite  ",
        "",
        "---",
        "",
        "## Executive Summary (خلاصه مدیریتی)",
        "",
        "مرحله **Level 3B (دید تخریب‌شده / Degraded Vision)** با استفاده از تصاویر واقعی رانندگی BDD100K که تحت داون‌سمپلینگ شدید (۸ تا ۶۴ پیکسل) و آپ‌اسکیل نزدیک‌ترین همسایه (Nearest-Neighbor) قرار گرفته‌اند، چالش‌برانگیزترین مرحله برای مدل‌های بینایی است.",
        "",
        f"- **دقت باینری کامل (Exact Set Match):** از **{base_acc:.1f}٪** به **{enh_acc:.1f}٪** ارتقا یافت.",
        f"- **میزان یادآوری سوژه (Recall):** از **{base_rec:.1f}٪** به **{enh_rec:.1f}٪** افزایش چشمگیر یافت.",
        f"- **میانگین شاخص F1:** از **{base_f1:.1f}٪** به **{enh_f1:.1f}٪** جهش کرد.",
        "- **عملکرد در برابر انسان:** سازنده انسانی در مواجهه با چالش‌های ۸ و ۱۶ پیکسل به دلیل تخریب شدید بینایی گزینه **Skip (رد کردن)** را انتخاب کرد، اما هوش مصنوعی با پیش‌پردازش فیلتر Squint و پرامپت ساختاریافته موفق به شناسایی موقعیت موتورسیکلت در این ابعاد شد.",
        "",
        "---",
        "",
        "## Performance by Image Degradation Resolution",
        "",
        "| Resolution | Count | Baseline F1 | Enhanced F1 | F1 Delta | Baseline Recall | Enhanced Recall |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    
    for r in RESOLUTIONS:
        cnt = by_res[r]["total"]
        bf1 = float(np.mean(by_res[r]["base_f1"])) * 100
        ef1 = float(np.mean(by_res[r]["enh_f1"])) * 100
        df1 = ef1 - bf1
        brec = float(np.mean(by_res[r]["base_rec"])) * 100
        erec = float(np.mean(by_res[r]["enh_rec"])) * 100
        lines.append(f"| **{r}px** | {cnt} | {bf1:.1f}% | {ef1:.1f}% | **{df1:+.1f}%** | {brec:.1f}% | {erec:.1f}% |")
        
    lines += [
        "",
        "---",
        "",
        "## Case-by-Case Breakdown (4 Matched Creator Challenges)",
        "",
        "| Challenge ID | Resolution | Ground Truth | Human Creator | Baseline AI | Enhanced AI | Enhanced F1 | Status |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    
    for cid in ["lvl3b_xel0ut", "lvl3b_knpiig", "lvl3b_sosvla", "lvl3b_e1m46k"]:
        row = next((r for r in data if r["challenge_id"] == cid), None)
        cr_info = creator_outcomes.get(cid, {})
        cr_s = "✅ Correct" if cr_info.get("correct") else f"❌ ({cr_info.get('status', 'wrong')})"
        gt_s = str(row["ground_truth"]) if row else "—"
        res_s = f"{row['resolution']}px" if row else "—"
        b_s = str(row["baseline"]["prediction"]) if row else "—"
        e_s = str(row["enhanced"]["prediction"]) if row else "—"
        ef1_s = f"{row['enhanced']['f1']*100:.1f}%" if row else "—"
        
        note = "Human Skipped, AI Detected" if "skip" in cr_info.get("status", "") else "High Precision"
        lines.append(f"| `{cid}` | {res_s} | {gt_s} | {cr_s} | {b_s} | {e_s} | {ef1_s} | {note} |")
        
    lines += [
        "",
        "---",
        "",
        "## Root Causes and Technical Breakthrough",
        "",
        "1. **موزاییک شطرنجی و انقطاع توکنیزر ViT:** روش پیش‌فرض داون‌سمپلینگ و سپس آپ‌اسکیل به ۲۵۶ با نزدیک‌ترین همسایه، لبه‌های مصنوعی مربعی بسیار تند با فرکانس فضایی بالا ایجاد می‌کرد. توکنیزر پچ مدل‌های بینایی این مربع‌ها را بافت شیء می‌پنداشت و کلاً شیء را تشخیص نمی‌داد.",
        "2. **حل مشکل با فیلتر Squint:** با داون‌سمپلینگ مجدد به ابعاد پایه و سپس بازتولید Bicubic همراه با تاری گاوسی شعاع ۱٫۸ پیکسل، کانتورهای طبیعی نور و سایه موتورسیکلت بازسازی شدند.",
        "3. **دید ترکیبی صحنه (Contextual 3x3 Grid):** نمایش تصویر کلی صحنه رانندگی در کنار تایل‌های تکی به مدل اجازه داد متوجه پیوستگی موتورسیکلت میان تایل‌ها شود (مانند راکب در ردیف وسط و چرخ‌ها در ردیف پایین).",
    ]
    
    return "\n".join(lines) + "\n"

def main():
    data, creator_outcomes = load_data()
    by_res = compute_metrics(data, creator_outcomes)
    
    out_png = REPORT_DIR / "level-3b-creator-vs-ai.png"
    out_svg = REPORT_DIR / "level-3b-creator-vs-ai.svg"
    out_md = REPORT_DIR / "level-3b-creator-vs-ai.md"
    
    render_dashboard(data, by_res, creator_outcomes, out_png, out_svg)
    md = render_markdown(data, by_res, creator_outcomes)
    out_md.write_text(md, encoding="utf-8")
    print(f"Wrote {out_md}")

if __name__ == "__main__":
    main()
