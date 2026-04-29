#!/usr/bin/env python3
"""Render the 12-panel Wispr Flow dashboard.

Eight panels cover the universal usage view (daily words, daily count,
cumulative words, cumulative time saved, hour, day of week, speed multiplier,
heatmap). Four are Wispr-only: per-app split, edit-rate split, AI-vs-human
voice split, and the achievement wall.

Output: outputs/dashboard.png
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402

PRIMARY = "#3b6dd8"
SECONDARY = "#e07a5f"
ACCENT = "#3d8168"
WARNING = "#f5b342"
PURPLE = "#7c5fad"
TEAL = "#2bb3a9"


def main():
    if not config.ANALYTICS_JSON.exists():
        print(f"ERROR: {config.ANALYTICS_JSON} not found. Run scripts/analytics.py first.")
        sys.exit(2)
    d = json.loads(config.ANALYTICS_JSON.read_text())

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.spines.top": False,
        "axes.spines.right": False,
    })

    fig = plt.figure(figsize=(20, 26))
    fig.suptitle(
        f"Wispr Flow Dashboard. {d['headline']['total_words']:,} dictated words across "
        f"{d['headline']['active_days']} active days, {d['headline']['total_hours']:.0f}h of speech.",
        fontsize=16, fontweight="bold", y=0.995,
    )

    series = d["daily_series"]
    dates = [datetime.strptime(s["date"], "%Y-%m-%d") for s in series]
    words = [s["words"] for s in series]
    counts = [s["n"] for s in series]

    # 1. Daily words
    ax = plt.subplot(6, 2, 1)
    ax.plot(dates, words, marker="o", markersize=3, linewidth=1.2, color=PRIMARY)
    ax.fill_between(dates, words, alpha=0.15, color=PRIMARY)
    ax.set_title("Daily Words Dictated"); ax.set_ylabel("Words"); ax.grid(True, alpha=0.3)
    ax.tick_params(axis="x", rotation=45)

    # 2. Daily dictations
    ax = plt.subplot(6, 2, 2)
    ax.bar(dates, counts, color=SECONDARY, alpha=0.85, width=0.9)
    ax.set_title("Daily Number of Dictations"); ax.set_ylabel("Dictations"); ax.grid(True, alpha=0.3)
    ax.tick_params(axis="x", rotation=45)

    # 3. Cumulative words
    ax = plt.subplot(6, 2, 3)
    cum = np.cumsum(words)
    ax.plot(dates, cum, color=ACCENT, linewidth=2.5)
    ax.fill_between(dates, cum, alpha=0.18, color=ACCENT)
    if max(cum) > 800_000:
        ax.axhline(1_000_000, color="red", linestyle="--", linewidth=1, alpha=0.7)
        ax.text(dates[-1], 1_000_000, " 1M", color="red", va="center", fontsize=9)
    ax.set_title("Cumulative Words Dictated"); ax.set_ylabel("Words"); ax.grid(True, alpha=0.3)
    ax.tick_params(axis="x", rotation=45)

    # 4. Cumulative time saved (60 WPM)
    ax = plt.subplot(6, 2, 4)
    saved_min = [s["saved_pro_min"] for s in series]
    cum_h = np.cumsum(saved_min) / 60
    ax.plot(dates, cum_h, color="red", linewidth=2.5)
    ax.fill_between(dates, cum_h, alpha=0.15, color="red")
    ax.set_title(
        f"Cumulative Hours Saved vs 60 WPM Typing "
        f"({d['time_savings_vs_typing_hours']['professional']:.0f}h total)"
    )
    ax.set_ylabel("Hours"); ax.grid(True, alpha=0.3); ax.tick_params(axis="x", rotation=45)

    # 5. Hour of day
    ax = plt.subplot(6, 2, 5)
    hour_words = {h["hour"]: h["words"] for h in d["hour_pattern_local"]}
    vals = [hour_words.get(h, 0) for h in range(24)]
    bars = ax.bar(range(24), vals, color=PURPLE, alpha=0.85)
    busy = d["headline"]["busiest_hour_local"]
    if busy is not None and 0 <= busy < 24:
        bars[busy].set_color("crimson")
    ax.set_title(f"Words by Hour of Day, Local (peak: {busy}:00)")
    ax.set_xlabel("Hour"); ax.set_ylabel("Words"); ax.set_xticks(range(0, 24, 2))
    ax.grid(True, alpha=0.3)

    # 6. Day of week
    ax = plt.subplot(6, 2, 6)
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_words = {x["dow"]: x["words"] for x in d["dow_pattern"]}
    vals = [dow_words.get(o, 0) for o in order]
    bars = ax.bar(order, vals, color=TEAL, alpha=0.85)
    busy_dow = d["headline"]["busiest_dow"]
    if busy_dow in order:
        bars[order.index(busy_dow)].set_color("crimson")
    ax.set_title(f"Words by Day of Week (peak: {busy_dow})"); ax.set_ylabel("Words")
    ax.tick_params(axis="x", rotation=30); ax.grid(True, alpha=0.3)

    # 7. Per-app
    ax = plt.subplot(6, 2, 7)
    apps = [a for a in d["per_app"] if a["words"] > 100][:10]
    labels = [a["label"] for a in apps]
    values = [a["words"] for a in apps]
    colors_app = plt.cm.tab10(np.linspace(0, 1, len(apps)))
    bars = ax.barh(labels[::-1], values[::-1], color=colors_app[::-1])
    ax.set_title("Words by App"); ax.set_xlabel("Words")
    for bar, v in zip(bars, values[::-1]):
        ax.text(v, bar.get_y() + bar.get_height() / 2, f" {v:,}", va="center", fontsize=9)

    # 8. Edit rate per app
    ax = plt.subplot(6, 2, 8)
    edit_rates = [a["edit_rate"] * 100 for a in apps][::-1]
    edit_colors = ["crimson" if r > 50 else "#2c7a3e" for r in edit_rates]
    ax.barh(labels[::-1], edit_rates, color=edit_colors)
    ax.set_title("Edit Rate by App (red = polished surface, green = AI passthrough)")
    ax.set_xlabel("% of dictations user edited after Wispr formatted")
    ax.set_xlim(0, 100); ax.grid(True, alpha=0.3, axis="x")

    # 9. AI vs human voices
    ax = plt.subplot(6, 2, 9)
    cats = ["AI-facing\n(Cursor / VSCode / Claude)", "Human-facing\n(Slack / Discord / WA / SMS)"]
    cat_words = [d["ai_facing"].get("words", 0), d["human_facing"].get("words", 0)]
    cat_edits = [d["ai_facing"].get("edit_rate", 0) * 100,
                 d["human_facing"].get("edit_rate", 0) * 100]
    x = np.arange(len(cats))
    ax2 = ax.twinx()
    ax.bar(x - 0.2, cat_words, 0.4, label="Words", color=PRIMARY)
    ax2.bar(x + 0.2, cat_edits, 0.4, label="Edit rate %", color=SECONDARY)
    ax.set_xticks(x); ax.set_xticklabels(cats)
    ax.set_ylabel("Words", color=PRIMARY); ax2.set_ylabel("Edit rate %", color=SECONDARY)
    ax.set_title("Two distinct voices: AI conversation vs polished writing")

    # 10. Speed multiplier
    ax = plt.subplot(6, 2, 10)
    benchmarks = list(d["speed_multipliers"].keys())
    mults = [d["speed_multipliers"][b] for b in benchmarks]
    saved = [d["time_savings_vs_typing_hours"][b] for b in benchmarks]
    bars = ax.bar(benchmarks, mults, color=[ACCENT, WARNING, SECONDARY])
    for bar, m, s in zip(bars, mults, saved):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.05,
                f"{m}x faster\n{s:.0f}h saved",
                ha="center", fontsize=10, fontweight="bold")
    ax.set_ylim(0, max(mults) + 1)
    ax.set_title(f"Speaking ({d['headline']['speaking_wpm']:.0f} WPM) vs typing benchmarks")
    ax.set_ylabel("Speed multiplier")

    # 11. Heatmap
    ax = plt.subplot(6, 2, 11)
    grid = defaultdict(lambda: 0.0)
    for s in series:
        dt = datetime.strptime(s["date"], "%Y-%m-%d")
        iso_year, iso_week, iso_dow = dt.isocalendar()
        grid[(f"{iso_year}-W{iso_week:02d}", iso_dow)] = s["words"]
    weeks = sorted({k[0] for k in grid.keys()})
    matrix = np.zeros((7, len(weeks)))
    for (w, dow), v in grid.items():
        matrix[dow - 1, weeks.index(w)] = v
    im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd")
    ax.set_yticks(range(7))
    ax.set_yticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    show_every = max(1, len(weeks) // 12)
    ax.set_xticks(range(0, len(weeks), show_every))
    ax.set_xticklabels([weeks[i] for i in range(0, len(weeks), show_every)],
                       rotation=45, ha="right")
    ax.set_title("Daily heatmap: words dictated")
    plt.colorbar(im, ax=ax, fraction=0.025)

    # 12. Achievement wall
    ax = plt.subplot(6, 2, 12)
    ax.axis("off")
    aches = d.get("wispr_achievements", [])[:9]
    text_lines = ["Wispr's own milestones (RemoteNotifications):", ""]
    for a in aches:
        text_lines.append(f"* {a['title']}")
        text_lines.append(f"   {a['text']}")
        text_lines.append("")
    ax.text(0.0, 1.0, "\n".join(text_lines), va="top", ha="left",
            fontsize=10, family="DejaVu Sans")
    ax.set_title("Achievements")

    plt.tight_layout(rect=[0, 0, 1, 0.985])
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(config.DASHBOARD_PNG, dpi=150, bbox_inches="tight")
    print(f"Wrote {config.DASHBOARD_PNG}")


if __name__ == "__main__":
    main()
