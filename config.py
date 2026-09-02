"""Configuration for wispr-flow-analysis.

Override defaults by setting the matching environment variables, either in the
shell or in a .env file next to this module. The repo ships with sensible
macOS defaults and falls back to a local snapshot copy.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_env_file(path: Path) -> None:
    """Read key=value pairs out of .env and into os.environ.

    SETUP.md tells users to copy .env.example to .env, so something has to
    actually read it. Before this, LOCAL_TZ_OFFSET_MINUTES and the API keys
    were silently ignored unless the user exported them by hand.

    python-dotenv is marked optional in requirements.txt, so fall back to a
    small parser when the package is absent. Both paths leave already-set
    environment variables alone, which keeps one-off overrides such as
    `FLOW_SQLITE_PATH=... python scripts/analytics.py` working.
    """
    if not path.exists():
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        pass
    else:
        load_dotenv(path, override=False)
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


_load_env_file(ROOT / ".env")

# ---------------------------------------------------------------------------
# Source database
# ---------------------------------------------------------------------------

# Live Wispr Flow SQLite. Opened read-only via the snapshot helper.
# macOS install location:
FLOW_SQLITE_PATH = os.environ.get(
    "FLOW_SQLITE_PATH",
    str(Path.home() / "Library" / "Application Support" / "Wispr Flow" / "flow.sqlite"),
)

# Working copy created by scripts/snapshot.py
SNAPSHOT_PATH = os.environ.get("SNAPSHOT_PATH", str(ROOT / "data" / "snapshot.sqlite"))

# ---------------------------------------------------------------------------
# Analysis parameters
# ---------------------------------------------------------------------------

# Typing benchmarks in words per minute. Casual = hunt-and-peck, professional =
# touch typist, fast = expert typist.
TYPING_SPEEDS = {"casual": 35, "professional": 60, "fast": 80}

# Local timezone offset in minutes (Eastern Daylight Time = -240).
# Override LOCAL_TZ_OFFSET_MINUTES in env if you live elsewhere.
LOCAL_TZ_OFFSET_MINUTES = int(os.environ.get("LOCAL_TZ_OFFSET_MINUTES", "-240"))

def _app_set(env_name: str, defaults: set) -> set:
    """Let the user replace an app set from the environment.

    The two-voices analysis is the headline insight, and it silently reports
    zero words when none of the user's apps appear in these sets. Dictating
    into Codex, Telegram or a browser instead of Cursor and Slack was enough
    to empty the panel with no warning. Overriding meant editing this tracked
    file, which then conflicts on every pull, so accept a comma-separated
    bundle ID list from the environment instead.
    """
    raw = os.environ.get(env_name)
    if not raw:
        return set(defaults)
    return {part.strip() for part in raw.split(",") if part.strip()}


# Apps where dictation goes to AI tools. Override with AI_FACING_APPS, a
# comma-separated list of bundle IDs. Run scripts/analytics.py once and read
# the per_app block in outputs/analytics.json to find your own IDs.
AI_FACING_APPS = _app_set(
    "AI_FACING_APPS",
    {
        "com.todesktop.230313mzl4w4u92",  # Cursor
        "com.microsoft.VSCode",
        "com.anthropic.claudefordesktop",
        "com.openai.codex",
    },
)

# Apps where dictation goes to other humans. Override with HUMAN_FACING_APPS.
HUMAN_FACING_APPS = _app_set(
    "HUMAN_FACING_APPS",
    {
        "com.tinyspeck.slackmacgap",       # Slack
        "com.hnc.Discord",
        "net.whatsapp.WhatsApp",
        "com.apple.MobileSMS",
        "org.whispersystems.signal-desktop",
        "com.tdesktop.Telegram",
        "com.automattic.beeper.desktop",   # bridges several chat networks
    },
)

# Friendly labels for charts.
APP_LABELS = {
    "com.todesktop.230313mzl4w4u92": "Cursor",
    "com.tinyspeck.slackmacgap": "Slack",
    "com.microsoft.VSCode": "VS Code",
    "company.thebrowser.Browser": "Arc",
    "com.anthropic.claudefordesktop": "Claude Desktop",
    "com.apple.MobileSMS": "Messages",
    "net.whatsapp.WhatsApp": "WhatsApp",
    "com.hnc.Discord": "Discord",
    "org.whispersystems.signal-desktop": "Signal",
    "com.openai.codex": "Codex",
    "com.tdesktop.Telegram": "Telegram",
    "com.automattic.beeper.desktop": "Beeper",
    "company.thebrowser.dia": "Dia",
    "com.electron.wispr-flow": "Wispr Flow",
    "com.genos.littlebird": "Littlebird",
    "com.nousresearch.hermes": "Hermes",
    "screenpi.pe": "screenpipe",
    "com.google.Chrome": "Chrome",
    "com.apple.Safari": "Safari",
}

# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

OUT_DIR = ROOT / "outputs"
ANALYTICS_JSON = OUT_DIR / "analytics.json"
DASHBOARD_PNG = OUT_DIR / "dashboard.png"
SHARE_PROMPT = OUT_DIR / "share_prompt.md"

# ---------------------------------------------------------------------------
# LLM provider settings (the ai_summary script picks the first available)
# ---------------------------------------------------------------------------

# Azure OpenAI. Set these in your .env file (see CONFIG_EXAMPLE.md).
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")

# Anthropic fallback. Optional.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_flow_sqlite_path() -> Path:
    return Path(FLOW_SQLITE_PATH).expanduser()


def get_snapshot_path() -> Path:
    return Path(SNAPSHOT_PATH).expanduser()


def app_label(app_id: str) -> str:
    return APP_LABELS.get(app_id, app_id or "<unknown>")
