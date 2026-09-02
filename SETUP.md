# Setup

## 1. Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure your environment

```bash
cp .env.example .env
# edit .env with your timezone offset and your Azure OpenAI or Anthropic key
```

`config.py` reads this file on import, so the values take effect without
exporting anything by hand. A variable already set in your shell still wins
over the file.

The most common edits:

- `LOCAL_TZ_OFFSET_MINUTES` so hour-of-day charts read in your local time.
- `AI_FACING_APPS` and `HUMAN_FACING_APPS` so the two-voices analysis matches
  the apps you actually dictate into. See step 5.
- `AZURE_OPENAI_*` if you have an Azure OpenAI deployment, or `ANTHROPIC_API_KEY`.

`ANTHROPIC_API_KEY` must be a raw API key from console.anthropic.com (starts with `sk-ant-`). Tokens injected into your shell by IDE assistants or wrapper CLIs (Claude Code, Claude Desktop, etc.) are not accepted by the SDK and will fail with a 401.

If you set neither, the AI summary script falls back to a hand-built template that uses your real numbers.

## 3. Verify your Wispr Flow path

The default macOS path is:

```
~/Library/Application Support/Wispr Flow/flow.sqlite
```

Override with `FLOW_SQLITE_PATH` in `.env` if your install lives elsewhere.

## 4. Run the pipeline

```bash
# Step 1. Snapshot the live SQLite. Safe to run while Flow is open.
python scripts/snapshot.py

# Step 2. Compute analytics. Outputs JSON.
python scripts/analytics.py

# Step 3. Render the 12-panel dashboard.
python scripts/visualize.py

# Step 4. Generate the share-ready posts.
python scripts/ai_summary.py
```

All outputs land under `outputs/`:

- `outputs/analytics.json` -- full structured rollup
- `outputs/dashboard.png` -- the chart
- `outputs/share_data_heavy.md` -- LinkedIn variant, leads with numbers
- `outputs/share_narrative_heavy.md` -- LinkedIn variant, leads with the story
- `outputs/share_single_stat_hook.md` -- LinkedIn variant, opens with one Wispr quote
- `outputs/share_thread.md` -- Twitter/X thread version

## 5. Check the two-voices split against your own apps

The AI-facing and human-facing comparison keys off the destination app's bundle
ID, and the defaults only cover Cursor, VS Code, Claude Desktop, Codex, Slack,
Discord, WhatsApp, Messages, Signal, Telegram, and Beeper. If you dictate
somewhere else, that panel reports zero words for one side and nothing tells
you why.

After the first `python scripts/analytics.py`, read your own IDs out of the
rollup:

```bash
python -c "import json; [print(a['words'], a['label']) for a in json.load(open('outputs/analytics.json'))['per_app'] if a['words'] > 100]"
```

Then set `AI_FACING_APPS` and `HUMAN_FACING_APPS` in `.env` and re-run steps 2
and 3. Leave genuinely mixed surfaces such as a browser out of both sets rather
than guessing, since anything you add moves the headline numbers.

## Re-running

The corpus grows daily. Steps 1 through 4 are safe to re-run any time. They each overwrite their own outputs.
