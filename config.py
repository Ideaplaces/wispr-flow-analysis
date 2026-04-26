"""Configuration for wispr-flow-analysis.

Override defaults by setting the matching environment variables. The repo
ships with sensible macOS defaults and falls back to a local snapshot copy.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

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

# Typing benchmarks in words per minute, matching crarau/superwhisper-analysis.
TYPING_SPEEDS = {"casual": 35, "professional": 60, "fast": 80}

# Local timezone offset in minutes (Eastern Daylight Time = -240).
# Override LOCAL_TZ_OFFSET_MINUTES in env if you live elsewhere.
LOCAL_TZ_OFFSET_MINUTES = int(os.environ.get("LOCAL_TZ_OFFSET_MINUTES", "-240"))

# Apps where dictation goes to AI tools (Cursor, VS Code, Claude Desktop).
AI_FACING_APPS = {
    "com.todesktop.230313mzl4w4u92",  # Cursor
    "com.microsoft.VSCode",
    "com.anthropic.claudefordesktop",
}

# Apps where dictation goes to other humans.
HUMAN_FACING_APPS = {
    "com.tinyspeck.slackmacgap",       # Slack
    "com.hnc.Discord",
    "net.whatsapp.WhatsApp",
    "com.apple.MobileSMS",
    "org.whispersystems.signal-desktop",
}

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
