# Configuration reference

`config.py` reads everything from environment variables, with sensible defaults. Override any of them via `.env` (loaded automatically) or by exporting them in your shell.

## Paths

| Variable | Default | Notes |
|---|---|---|
| `FLOW_SQLITE_PATH` | `~/Library/Application Support/Wispr Flow/flow.sqlite` | macOS default. Override on Linux/Windows. |
| `SNAPSHOT_PATH` | `./data/snapshot.sqlite` | Where `scripts/snapshot.py` writes its read-only copy. |

## Timezone

| Variable | Default | Notes |
|---|---|---|
| `LOCAL_TZ_OFFSET_MINUTES` | `-240` | Eastern Daylight Time. Use `-300` for EST, `-480` for PST, `0` for UTC. |

## App classification

The "two voices" insight depends on which apps you tag as AI-facing vs human-facing. Edit `AI_FACING_APPS` and `HUMAN_FACING_APPS` in `config.py` to match how you use Wispr Flow. Defaults cover the common North American macOS install set.

You can find your own app bundle IDs by looking at the `app` column in the snapshot:

```python
import sqlite3
conn = sqlite3.connect("file:data/snapshot.sqlite?mode=ro", uri=True)
for row in conn.execute("SELECT DISTINCT app FROM History"):
    print(row[0])
```

## LLM provider

Set up exactly one of these and the AI summary script will pick it up automatically. If both are set, Azure is preferred.

### Azure OpenAI

```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
```

`gpt-4o-mini` is cost-efficient and good enough for short share posts. Use `gpt-4o` or `gpt-4.1` if you have those deployments and want higher polish.

### Anthropic

```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

### No API

If neither is set, `scripts/ai_summary.py` falls back to a hand-built template that uses your real numbers. It will not be as polished, but it works offline.

## Typing benchmarks

| Variable | Default | Source |
|---|---|---|
| `TYPING_SPEEDS["casual"]` | 35 WPM | Hunt-and-peck |
| `TYPING_SPEEDS["professional"]` | 60 WPM | Touch typist |
| `TYPING_SPEEDS["fast"]` | 80 WPM | Expert typist |

Edit these in `config.py` if your audience needs a different baseline.
