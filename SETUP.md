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

The most common edits:

- `LOCAL_TZ_OFFSET_MINUTES` so hour-of-day charts read in your local time.
- `AZURE_OPENAI_*` if you have an Azure OpenAI deployment, or `ANTHROPIC_API_KEY`.

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

## Re-running

The corpus grows daily. Steps 1 through 4 are safe to re-run any time. They each overwrite their own outputs.
