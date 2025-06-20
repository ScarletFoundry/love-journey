#!/usr/bin/env python3
import datetime
import subprocess
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────
START_DT       = datetime.datetime(2014, 4, 14, 12, 0, 0)
README         = "README.md"
START_MARKER   = "<!-- TIME-TOGETHER:START -->"
END_MARKER     = "<!-- TIME-TOGETHER:END -->"

# Birth dates
SKIDDLE_BORN = datetime.date(1997, 8, 9)
SCARLET_BORN = datetime.date(1998, 8, 4)

AUTHOR_NAME  = "skiddle-bot"
AUTHOR_EMAIL = "165562787+skiddle-bot@users.noreply.github.com"
BRANCH       = "main"
# ──────────────────────────────────────────────────────────────────────────────

def calculate_age(born_date: datetime.date, today: datetime.date) -> int:
    age = today.year - born_date.year
    if (today.month, today.day) < (born_date.month, born_date.day):
        age -= 1
    return age

def format_duration(td: datetime.timedelta) -> str:
    total_minutes = td.days * 24 * 60 + td.seconds // 60
    years = total_minutes // (365 * 24 * 60)
    days  = (total_minutes % (365 * 24 * 60)) // (24 * 60)
    hours = (total_minutes % (24 * 60)) // 60
    mins  = total_minutes % 60
    parts = []
    if years: parts.append(f"{years} year{'s' if years != 1 else ''}")
    if days: parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours: parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    parts.append(f"{mins} minute{'s' if mins != 1 else ''}")
    return ", ".join(parts)

def build_dynamic_content(now: datetime.datetime) -> tuple[str, str]:
    td = now - START_DT
    duration = format_duration(td)

    today = now.date()
    skiddle_age = calculate_age(SKIDDLE_BORN, today)
    scarlet_age = calculate_age(SCARLET_BORN, today)

    lines = [
        f"We have been together for **{duration}**.",
        "",
        f"Jeff is **{skiddle_age}** years old, and Jacqueline is **{scarlet_age}** years old."
    ]

    if now.month == 8:
        lines.append("")
        lines.append("It's our birthday month! 🎉")

    return "\n".join(lines) + "\n", duration

def run_git_command(*args):
    try:
        result = subprocess.run(['git', *args], capture_output=True, text=True, check=True)
        if result.stdout.strip(): print(result.stdout.strip())
        if result.stderr.strip(): print(result.stderr.strip())
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e.stderr.strip()}")
        raise

def send_discord_success(duration: str):
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if not webhook_url:
        print("DISCORD_WEBHOOK not set. Skipping Discord notification.")
        return

    import json
    import requests

    payload = {
        "embeds": [{
            "title": "✅ README Updated",
            "description": f"Skiddle and Scarletnine have been together for **{duration}**.",
            "color": 15277667,
            "fields": [
                {"name": "Updated File", "value": README, "inline": True},
                {"name": "Branch", "value": BRANCH, "inline": True},
                {"name": "Time (UTC)", "value": datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
            ],
            "footer": {"text": "Skiddle Bot | GitHub Actions"}
        }]
    }

    try:
        res = requests.post(webhook_url, json=payload, timeout=10)
        res.raise_for_status()
        print("✅ Discord notification sent.")
    except Exception as e:
        print(f"❌ Failed to send Discord notification: {e}")

def main():
    now = datetime.datetime.utcnow()
    dynamic_content, duration = build_dynamic_content(now)

    if not os.path.exists(README):
        print(f"{README} not found.")
        return

    with open(README, "r", encoding="utf-8") as f:
        original = f.read()

    lines = original.splitlines(keepends=True)
    start_index = next((i for i, l in enumerate(lines) if START_MARKER in l), -1)
    end_index   = next((i for i, l in enumerate(lines) if END_MARKER in l), -1)

    if start_index == -1 or end_index == -1 or start_index >= end_index:
        print("Markers not found properly. Appending content.")
        updated = original + "\n" + START_MARKER + "\n" + dynamic_content + END_MARKER + "\n"
    else:
        before = "".join(lines[:start_index + 1])
        after  = "".join(lines[end_index:])
        updated = before + dynamic_content + after

    if updated != original:
        with open(README, "w", encoding="utf-8") as f:
            f.write(updated)

        run_git_command("config", "user.name", AUTHOR_NAME)
        run_git_command("config", "user.email", AUTHOR_EMAIL)
        run_git_command("add", README)
        run_git_command("commit", "-m", "chore: update time-together section in README [skip ci]")
        run_git_command("push", "origin", f"HEAD:{BRANCH}")

        send_discord_success(duration)
    else:
        print("No change detected. Nothing to commit.")

if __name__ == "__main__":
    main()
