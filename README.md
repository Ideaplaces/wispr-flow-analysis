# Wispr Flow Analysis

Analytics toolkit for [Wispr Flow](https://wisprflow.ai) voice dictation. Pulls your full local corpus, surfaces the patterns nobody else can see (per-app split, edit rates, your two distinct voices), and drafts a share-ready summary in your voice using Azure OpenAI or Anthropic.

The companion project to [crarau/superwhisper-analysis](https://github.com/crarau/superwhisper-analysis) (28 stars, 1 fork). Same idea, but Wispr Flow's richer SQLite schema unlocks insights SuperWhisper's flat `meta.json` files cannot.

## What you get

A single dashboard PNG and a JSON file with everything underneath, plus four LLM-generated post variants ready to paste into LinkedIn or X.

The four insights that matter:

1. **Total volume.** Words, hours, active days, longest streak, peak day.
2. **Speed and time saved.** Speaking WPM vs casual / professional / fast typing benchmarks. Cumulative hours saved.
3. **Two voices.** AI-facing dictation (Cursor, VS Code, Claude Desktop) vs human-facing dictation (Slack, Discord, WhatsApp, Messages). Different speeds, different edit rates, different roles. This is the part SuperWhisper analytics could not see, because it had no app context.
4. **Wispr's own achievements.** Your `RemoteNotifications` table is full of milestone quotes ("9 months of unbroken Flow usage", "1,500,000 words crossed", and the rest). The AI summary script quotes these verbatim, which is the most viral hook in the corpus.

## Quick start

```bash
git clone <this repo>
cd wispr-flow-analysis
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit with your Azure OpenAI or Anthropic key

python scripts/snapshot.py     # safe read-only copy of flow.sqlite
python scripts/analytics.py    # rollup -> outputs/analytics.json
python scripts/visualize.py    # -> outputs/dashboard.png
python scripts/ai_summary.py   # -> outputs/share_*.md
```

Full setup details in [SETUP.md](SETUP.md). Configuration reference in [CONFIG_EXAMPLE.md](CONFIG_EXAMPLE.md).

## Sample output

The share draft starts with a Wispr-stamped milestone (verbatim from your `RemoteNotifications` table) and unpacks the two-voices insight in your own data. Every number is real and pulled from your corpus. The script generates four variants per run:

- `share_data_heavy.md` -- leads with the numbers
- `share_narrative_heavy.md` -- leads with the story
- `share_single_stat_hook.md` -- one Wispr quote on its own line, then unpacks it
- `share_thread.md` -- 8 to 12 numbered tweets

Pick whichever variant matches the surface and the day.

## What's in the schema that SuperWhisper did not have

Wispr Flow's `History` table records, per dictation:

- `app` and `url` (where the dictation was sent)
- `formattedText` (Wispr's AI-cleaned version) and `editedText` (what you actually shipped after manual edits)
- `numWordsCorrected`, `numDictionaryReplacements` (Wispr's own correction count)
- `formattingDivergenceScore` (how much Wispr cleaned up the raw ASR)
- `audio` blobs and `opusChunks` for a fraction of dictations
- `axText` and `axHTML` (the screen context at the moment you spoke)
- `Dictionary`, `Polish`, `RemoteNotifications` tables alongside `History`

This script uses `app`, `formattedText` vs `editedText` (for the edit-rate split), `numWords`, `duration`, `timestamp`, `detectedLanguage`, plus `RemoteNotifications` for the achievement quotes. The richer columns (`axText`, `audio`, etc.) are surfaced in `outputs/analytics.json` for downstream use.

## How the two-voices analysis works

Apps in `config.AI_FACING_APPS` (Cursor, VS Code, Claude Desktop) almost never get edited after Wispr formats them. Apps in `config.HUMAN_FACING_APPS` (Slack, Discord, WhatsApp, Messages) almost always do. The script reports both blocks separately, with their own word counts, WPM, edit rates, and time-saved figures. Adjust the two sets in `config.py` to match how you actually use Wispr.

## Privacy

Everything runs locally. The script never uploads your dictations or audio anywhere. The only network call is the LLM provider (Azure OpenAI or Anthropic) for the share-summary step, and that call sends only your aggregate numbers, never raw dictation text. If you skip the AI step, no data leaves your machine.

## License

MIT. See [LICENSE](LICENSE).

## Credits

Built on top of the analytics structure pioneered in [crarau/superwhisper-analysis](https://github.com/crarau/superwhisper-analysis). Wispr Flow's richer schema does the rest.
