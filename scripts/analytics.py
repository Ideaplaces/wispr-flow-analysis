#!/usr/bin/env python3
"""Analytics rollup for the Wispr Flow corpus.

Inspired by crarau/superwhisper-analysis but extended for Wispr Flow's
richer schema. Includes everything SuperWhisper analytics produced (time
savings vs typing, hour and day patterns, cumulative time saved, peak day,
recent 30-day snapshot) PLUS five Wispr-only dimensions:

    - Per-app split (Cursor vs Slack vs Browser, etc.)
    - Edit-rate split (formatted vs Chip's edited text)
    - AI-facing vs human-facing voice (the "two voices" insight)
    - Daily streak detection
    - Wispr's own RemoteNotifications achievements (verbatim quotes)

Output: outputs/analytics.json
"""

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402


def parse_ts(s):
    if not s:
        return None
    s = s.replace(" +00:00", "+00:00").replace(" UTC", "+00:00")
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def to_local(dt, offset_minutes):
    if dt is None:
        return None
    return dt + timedelta(minutes=offset_minutes)


def block_stats(records):
    if not records:
        return {"n": 0, "words": 0, "hours": 0, "wpm": 0, "edit_rate": 0, "saved_pro_h": 0}
    words = sum(r["words"] for r in records)
    secs = sum(r["duration_s"] for r in records)
    edited = sum(1 for r in records if r["edited"])
    saved = sum(r["time_saved_s"]["professional"] for r in records) / 3600
    return {
        "n": len(records),
        "words": words,
        "hours": round(secs / 3600, 1),
        "wpm": round(words * 60 / secs, 1) if secs else 0,
        "edit_rate": round(edited / len(records), 3),
        "saved_pro_h": round(saved, 1),
    }


def main():
    src = config.get_snapshot_path()
    if not src.exists():
        print(f"ERROR: snapshot not found at {src}")
        print("Run: python scripts/snapshot.py")
        sys.exit(2)

    conn = sqlite3.connect(f"file:{src}?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """SELECT timestamp, app, numWords, duration,
                  formattedText, editedText, audio IS NOT NULL AS has_audio,
                  detectedLanguage
           FROM History
           WHERE timestamp IS NOT NULL"""
    )
    rows = cur.fetchall()

    enriched = []
    for r in rows:
        words = r["numWords"] or 0
        dur_s = r["duration"] or 0.0
        if dur_s <= 0:
            continue
        wpm = words * 60 / dur_s if dur_s else 0
        typing_secs = {k: words / b * 60 for k, b in config.TYPING_SPEEDS.items()}
        time_saved_s = {k: max(0, t - dur_s) for k, t in typing_secs.items()}
        ts_utc = parse_ts(r["timestamp"])
        ts_local = to_local(ts_utc, config.LOCAL_TZ_OFFSET_MINUTES)
        enriched.append({
            "ts_local": ts_local,
            "date_local": ts_local.date() if ts_local else None,
            "hour_local": ts_local.hour if ts_local else None,
            "dow_local": ts_local.strftime("%A") if ts_local else None,
            "app": r["app"] or "",
            "words": words,
            "duration_s": dur_s,
            "wpm": wpm,
            "typing_secs": typing_secs,
            "time_saved_s": time_saved_s,
            "edited": bool(r["editedText"] and r["editedText"] != r["formattedText"]),
            "ai_facing": (r["app"] or "") in config.AI_FACING_APPS,
            "human_facing": (r["app"] or "") in config.HUMAN_FACING_APPS,
            "lang": r["detectedLanguage"] or "unknown",
            "has_audio": bool(r["has_audio"]),
        })

    total_recordings = len(enriched)
    total_words = sum(e["words"] for e in enriched)
    total_seconds = sum(e["duration_s"] for e in enriched)
    total_hours = total_seconds / 3600
    avg_wpm = total_words * 60 / total_seconds if total_seconds else 0

    saved_total = {
        k: round(sum(e["time_saved_s"][k] for e in enriched) / 3600, 1)
        for k in config.TYPING_SPEEDS
    }

    # Daily series
    daily = defaultdict(lambda: {"words": 0, "seconds": 0.0, "n": 0, "saved_pro_min": 0.0})
    for e in enriched:
        d = e["date_local"]
        if d is None:
            continue
        b = daily[d]
        b["words"] += e["words"]
        b["seconds"] += e["duration_s"]
        b["n"] += 1
        b["saved_pro_min"] += e["time_saved_s"]["professional"] / 60

    sorted_days = sorted(daily.keys())
    active_days = len(sorted_days)
    peak_day = max(daily.items(), key=lambda kv: kv[1]["words"]) if daily else (None, {})

    # Streak
    longest_streak = 0
    cur_streak = 0
    prev = None
    for d in sorted_days:
        if prev is None or (d - prev).days == 1:
            cur_streak += 1
        else:
            cur_streak = 1
        longest_streak = max(longest_streak, cur_streak)
        prev = d

    # Recent 30 days
    if sorted_days:
        cutoff = max(sorted_days) - timedelta(days=29)
        recent = [e for e in enriched if e["date_local"] and e["date_local"] >= cutoff]
    else:
        recent = []
    recent_words = sum(e["words"] for e in recent)
    recent_seconds = sum(e["duration_s"] for e in recent)
    recent_minutes = recent_seconds / 60
    recent_active_days = len({e["date_local"] for e in recent})

    # Hour and day-of-week patterns
    hour_words = defaultdict(int)
    hour_seconds = defaultdict(float)
    dow_words = defaultdict(int)
    dow_seconds = defaultdict(float)
    for e in enriched:
        if e["hour_local"] is not None:
            hour_words[e["hour_local"]] += e["words"]
            hour_seconds[e["hour_local"]] += e["duration_s"]
        if e["dow_local"]:
            dow_words[e["dow_local"]] += e["words"]
            dow_seconds[e["dow_local"]] += e["duration_s"]
    busiest_hour = max(hour_seconds.items(), key=lambda kv: kv[1])[0] if hour_seconds else None
    busiest_dow = max(dow_seconds.items(), key=lambda kv: kv[1])[0] if dow_seconds else None

    # Per-app split
    app_roll = defaultdict(lambda: {"n": 0, "words": 0, "seconds": 0.0,
                                     "edited": 0, "saved_pro_min": 0.0})
    for e in enriched:
        a = app_roll[e["app"]]
        a["n"] += 1
        a["words"] += e["words"]
        a["seconds"] += e["duration_s"]
        if e["edited"]:
            a["edited"] += 1
        a["saved_pro_min"] += e["time_saved_s"]["professional"] / 60
    apps_sorted = sorted(app_roll.items(), key=lambda kv: kv[1]["words"], reverse=True)

    # AI vs human-facing
    ai_recs = [e for e in enriched if e["ai_facing"]]
    human_recs = [e for e in enriched if e["human_facing"]]

    # Wispr's own achievement notifications
    cur.execute(
        """SELECT title, text, createdAt FROM RemoteNotifications
           WHERE type = 'achievement'
           ORDER BY createdAt"""
    )
    wispr_achievements = [dict(r) for r in cur.fetchall()]

    streak_weeks = longest_streak // 7
    milestones = []
    if total_words >= 990_000:
        milestones.append(f"Crossed 1 million dictated words ({total_words:,} captured locally).")
    elif total_words >= 500_000:
        milestones.append(f"Halfway to a million dictated words ({total_words:,} so far).")
    if longest_streak >= 30:
        milestones.append(f"{longest_streak}-day local streak of dictating every single day.")
    if total_hours >= 100:
        milestones.append(f"{total_hours:.0f} hours of speech captured.")
    if saved_total["professional"] >= 100:
        milestones.append(
            f"~{saved_total['professional']:.0f} hours saved vs a 60 WPM professional typist."
        )
    if peak_day[0] and peak_day[1].get("words", 0) >= 10_000:
        milestones.append(
            f"Single biggest day: {peak_day[0]} with {peak_day[1]['words']:,} words."
        )
    for ach in wispr_achievements:
        milestones.append(f"Wispr-detected: {ach['title']} | {ach['text']}")

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "headline": {
            "total_recordings": total_recordings,
            "total_words": total_words,
            "total_hours": round(total_hours, 1),
            "active_days": active_days,
            "speaking_wpm": round(avg_wpm, 1),
            "first_day": str(min(sorted_days)) if sorted_days else None,
            "last_day": str(max(sorted_days)) if sorted_days else None,
            "longest_streak_days": longest_streak,
            "longest_streak_weeks": streak_weeks,
            "peak_day": str(peak_day[0]) if peak_day[0] else None,
            "peak_day_words": peak_day[1].get("words", 0) if peak_day[1] else 0,
            "peak_day_dictations": peak_day[1].get("n", 0) if peak_day[1] else 0,
            "busiest_hour_local": busiest_hour,
            "busiest_dow": busiest_dow,
        },
        "time_savings_vs_typing_hours": saved_total,
        "speed_multipliers": {
            k: round(avg_wpm / b, 2) for k, b in config.TYPING_SPEEDS.items()
        },
        "recent_30d": {
            "active_days": recent_active_days,
            "recordings": len(recent),
            "words": recent_words,
            "minutes": round(recent_minutes, 1),
            "saved_pro_hours": round(
                sum(e["time_saved_s"]["professional"] for e in recent) / 3600, 1),
            "daily_words_avg": round(recent_words / max(1, recent_active_days), 0),
            "daily_minutes_avg": round(recent_minutes / max(1, recent_active_days), 1),
            "daily_recordings_avg": round(len(recent) / max(1, recent_active_days), 1),
        },
        "per_app": [
            {
                "app": a or "<unknown>",
                "label": config.app_label(a),
                "dictations": v["n"],
                "words": v["words"],
                "hours": round(v["seconds"] / 3600, 1),
                "edit_rate": round(v["edited"] / v["n"], 3) if v["n"] else 0,
                "saved_pro_hours": round(v["saved_pro_min"] / 60, 1),
            }
            for a, v in apps_sorted
        ],
        "ai_facing": block_stats(ai_recs),
        "human_facing": block_stats(human_recs),
        "hour_pattern_local": [
            {"hour": h, "seconds": round(hour_seconds[h], 0), "words": hour_words[h]}
            for h in sorted(hour_seconds)
        ],
        "dow_pattern": [
            {"dow": d, "seconds": round(dow_seconds[d], 0), "words": dow_words[d]}
            for d in dow_seconds
        ],
        "milestones": milestones,
        "wispr_achievements": wispr_achievements,
        "daily_series": [
            {"date": str(d), **{k: (v if k != "seconds" else round(v, 0))
                                 for k, v in daily[d].items()}}
            for d in sorted_days
        ],
        "languages": {
            l: sum(1 for e in enriched if e["lang"] == l)
            for l in {e["lang"] for e in enriched}
        },
        "audio_count": sum(1 for e in enriched if e["has_audio"]),
    }

    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    config.ANALYTICS_JSON.write_text(json.dumps(report, indent=2, default=str))
    print(f"Wrote {config.ANALYTICS_JSON}")
    print()
    h = report["headline"]
    print(f"Total: {h['total_recordings']:,} dictations, {h['total_words']:,} words, "
          f"{h['total_hours']:.0f}h speech, {h['active_days']} active days, "
          f"{h['speaking_wpm']:.0f} WPM.")
    print(f"Streak: {h['longest_streak_days']} days. Peak: {h['peak_day']} "
          f"({h['peak_day_words']:,} words).")
    print(f"Time saved (60 WPM benchmark): "
          f"{report['time_savings_vs_typing_hours']['professional']:.0f}h overall, "
          f"{report['human_facing']['saved_pro_h']:.0f}h on human-facing apps only.")


if __name__ == "__main__":
    main()
