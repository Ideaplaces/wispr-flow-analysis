#!/usr/bin/env python3
"""Generate share-ready posts from your analytics data.

Provider order:
  1. Azure OpenAI (AZURE_OPENAI_*)
  2. Anthropic (ANTHROPIC_API_KEY)
  3. Offline template (works without any API)

Generates four variants per run: data_heavy, narrative_heavy, single_stat_hook,
and a Twitter/X thread. All are saved to outputs/.

Usage:
    python scripts/ai_summary.py
    python scripts/ai_summary.py --variant data_heavy   # generate one only
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env first so config picks up the values.
ENV_PATH = ROOT / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import config  # noqa: E402


VARIANT_INSTRUCTIONS = {
    "data_heavy": (
        "Lead with the most striking number and stack three to four more concrete numbers in "
        "the first half. Show the math behind the 'two voices' insight. Read like a founder "
        "breaking down their own dashboard."
    ),
    "narrative_heavy": (
        "Lead with how the way of working changed, not the number. Numbers come later, sparingly. "
        "Sensory and momentum language. Reads like a personal essay."
    ),
    "single_stat_hook": (
        "Open with one quoted Wispr achievement notification verbatim, on its own line, as the "
        "hook. Then unpack what it actually means in three to four short paragraphs. "
        "Almost no other numbers."
    ),
    "thread": (
        "Format as a numbered Twitter/X thread with eight to twelve short posts. Each post under "
        "270 characters including spaces. Number them 1/, 2/, 3/, etc. First post is the hook. "
        "Last post is a soft invitation to try voice-first."
    ),
}


def build_prompt(d, variant):
    h = d["headline"]
    r = d["recent_30d"]
    sm = d["speed_multipliers"]
    ts = d["time_savings_vs_typing_hours"]
    ai = d["ai_facing"]
    hu = d["human_facing"]
    aches = d.get("wispr_achievements", [])

    achievements_text = "\n".join(f"- {a['title']} | {a['text']}" for a in aches)
    per_app_top = "\n".join(
        f"- {a['label']}: {a['words']:,} words ({a['edit_rate']*100:.0f}% edit rate)"
        for a in d["per_app"][:6] if a["words"] > 100
    )
    variant_block = VARIANT_INSTRUCTIONS.get(variant, VARIANT_INSTRUCTIONS["data_heavy"])
    surface = "Twitter/X thread" if variant == "thread" else "LinkedIn"

    return f"""You are writing a single, share-ready voice-first dictation analytics post for {surface}.

VARIANT INSTRUCTION:
{variant_block}

WRITING RULES (HARD CONSTRAINTS)
- No em dashes or en dashes anywhere. Use periods, commas, parentheses, or restructure.
- No "AI assistant" attribution. No mentions of the model used to draft this.
- No emojis unless quoting a Wispr achievement title verbatim.
- Use periods for hard stops. Where a softer break is wanted, use a comma, a colon, or a line break.
- Short paragraphs. Plenty of vertical breathing room. Spoken cadence.
- Declarative, decisive, warm tone. No hedging adverbs. No corporate cliches like "leveraging" or "synergy".

DATA (the actual numbers, do not invent any)

Wispr Flow corpus:
- {h['total_recordings']:,} dictations, {h['total_words']:,} words, {h['total_hours']:.0f} hours of speech
- Active for {h['active_days']} days from {h['first_day']} to {h['last_day']}
- Speaking speed: {h['speaking_wpm']} WPM
- Longest unbroken local streak: {h['longest_streak_days']} days
- Peak day: {h['peak_day']}, {h['peak_day_words']:,} words across {h['peak_day_dictations']} dictations
- Busiest hour local: {h['busiest_hour_local']}:00, busiest weekday: {h['busiest_dow']}

Time saved vs typing benchmarks:
- vs casual (35 WPM): {ts['casual']:.0f} hours, {sm['casual']}x faster
- vs professional (60 WPM): {ts['professional']:.0f} hours, {sm['professional']}x faster
- vs fast (80 WPM): {ts['fast']:.0f} hours, {sm['fast']}x faster

Recent 30 days:
- {r['recordings']} dictations across {r['active_days']} days
- {r['words']:,} words, average {r['daily_words_avg']:.0f} per active day
- {r['minutes']:.0f} minutes talking, {r['daily_minutes_avg']:.1f} per active day
- {r['saved_pro_hours']:.0f} hours saved vs 60 WPM typing

The two-voices insight (the part that is genuinely new):
- AI-facing apps (Cursor, VS Code, Claude Desktop): {ai['n']:,} dictations, {ai['words']:,} words, {ai['wpm']:.0f} WPM, {ai['edit_rate']*100:.1f}% edit rate. Talking to AI is conversational, mostly unedited.
- Human-facing apps (Slack, Discord, WhatsApp, Messages): {hu['n']:,} dictations, {hu['words']:,} words, {hu['wpm']:.0f} WPM, {hu['edit_rate']*100:.1f}% edit rate. Talking to people gets polished. The honest typing-replacement number lives here: {hu['saved_pro_h']:.0f} hours.

Per-app top:
{per_app_top}

Wispr's own backend has been quietly emitting achievement notifications. Direct quotes from the RemoteNotifications table:
{achievements_text}

OUTPUT
Just the post body. No title, no preamble. Ready to paste.
"""


def call_azure(prompt, max_tokens=1600, temperature=0.75):
    from openai import AzureOpenAI
    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )
    deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system",
             "content": (
                 "You write the user's own LinkedIn or Twitter post in their voice. "
                 "You strictly follow every constraint in the user message. You output only the "
                 "post body itself, no preamble, no markdown headers, no commentary."
             )},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip(), f"Azure OpenAI ({deployment})"


def call_anthropic(prompt, max_tokens=1600):
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip(), f"Anthropic ({config.ANTHROPIC_MODEL})"


def offline_draft(d):
    """Hand-built fallback that uses the actual numbers if no API key is set."""
    h = d["headline"]
    hu = d["human_facing"]
    ai = d["ai_facing"]
    legend_line = ""
    months_quote = ""
    for a in d.get("wispr_achievements", []):
        if "1,500,000" in a["text"] or "living legend" in a["text"]:
            legend_line = a["text"]
        if "9 months" in a["title"] or "39 weeks" in a["text"]:
            months_quote = a["text"]
    parts = []
    if legend_line:
        parts.append(f"Wispr Flow just told me, verbatim: \"{legend_line}\"")
    parts.append(
        f"On my own machine, the local History table sees {h['total_words']:,} words "
        f"across {h['active_days']} active days, {h['total_hours']:.0f} hours of speech."
    )
    parts.append(
        "What is interesting is not the speed. It is that I now have two distinct voices."
    )
    parts.append(
        f"Voice one is the AI-conversation voice. {ai['words']:,} words at {ai['wpm']:.0f} "
        f"WPM, edit rate {ai['edit_rate']*100:.0f}%. Conversational, exploratory, almost never polished."
    )
    parts.append(
        f"Voice two is the human-conversation voice. {hu['words']:,} words at {hu['wpm']:.0f} "
        f"WPM, edit rate {hu['edit_rate']*100:.0f}%. Almost everything I send to a person gets a "
        f"second pass. Real typing replaced: {hu['saved_pro_h']:.0f} hours."
    )
    if months_quote:
        parts.append(f"Wispr also flagged my streak: \"{months_quote}\"")
    parts.append(
        "If you have not tried voice-first yet, the unlock is not WPM. It is the freedom to "
        "keep moving while you think. Try it for a week."
    )
    return "\n\n".join(parts)


def generate(prompt):
    if config.AZURE_OPENAI_API_KEY and config.AZURE_OPENAI_ENDPOINT:
        try:
            return call_azure(prompt)
        except Exception as e:
            print(f"  Azure call failed: {e}")
    if config.ANTHROPIC_API_KEY:
        try:
            return call_anthropic(prompt)
        except Exception as e:
            print(f"  Anthropic call failed: {e}")
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=list(VARIANT_INSTRUCTIONS.keys()) + ["all"],
                    default="all")
    args = ap.parse_args()

    if not config.ANALYTICS_JSON.exists():
        print(f"ERROR: {config.ANALYTICS_JSON} not found. Run scripts/analytics.py first.")
        sys.exit(2)
    d = json.loads(config.ANALYTICS_JSON.read_text())

    variants = list(VARIANT_INSTRUCTIONS.keys()) if args.variant == "all" else [args.variant]

    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    config.SHARE_PROMPT.write_text(build_prompt(d, "data_heavy"))

    for variant in variants:
        print(f"--- Variant: {variant} ---")
        prompt = build_prompt(d, variant)
        draft, source = generate(prompt)
        if draft is None:
            print("  No API key configured. Writing offline template.")
            draft = offline_draft(d)
            source = "offline template"

        out_name = "share_thread.md" if variant == "thread" else f"share_{variant}.md"
        out_path = config.OUT_DIR / out_name
        out_path.write_text(
            f"# Wispr Flow {variant.replace('_', ' ')} draft\n"
            f"Generated by {source} on {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"{draft}\n"
        )
        print(f"  Wrote {out_path}")
        print()
        print(draft)
        print("-" * 60)
        print()


if __name__ == "__main__":
    main()
