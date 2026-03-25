#!/usr/bin/env python3
import datetime
import subprocess
import os
import json
from pathlib import Path
from urllib import request, error

# ── CONFIG ────────────────────────────────────────────────────────────────────
# The moment the journey began: April 14, 2014
START_DT     = datetime.datetime(2014, 4, 14, 12, 0, 0, tzinfo=datetime.timezone.utc)
README_PATH  = Path("README.md")
START_MARKER = ""
END_MARKER   = ""

# Birthday config
BIRTHDAYS = {
    "Jeff": datetime.date(1997, 8, 9),
    "Jacqueline": datetime.date(1999, 8, 4)
}

AUTHOR_NAME  = "skiddle-bot"
AUTHOR_EMAIL = "165562787+skiddle-bot@users.noreply.github.com"
BRANCH       = "main"
# ──────────────────────────────────────────────────────────────────────────────

def calculate_age(born_date: datetime.date, today: datetime.date) -> int:
    return today.year - born_date.year - ((today.month, today.day) < (born_date.month, born_date.day))

def format_duration(start: datetime.datetime, end: datetime.datetime) -> str:
    diff = end - start
    years = diff.days // 365
    days = diff.days % 365
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if years: parts.append(f"{years} year{'s' if years != 1 else ''}")
    if days: parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours: parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return ", ".join(parts)

def build_dynamic_content(now: datetime.datetime) -> tuple[str, str]:
    duration = format_duration(START_DT, now)
    today = now.date()
    
    ages = [f"{name} is **{calculate_age(bd, today)}**" for name, bd in BIRTHDAYS.items()]
    age_str = " years old, and ".join(ages) + " years old."

    lines = [
        f"We have been together for **{duration}**.",
        "",
        age_str
    ]

    if now.month == 8:
        lines.extend(["", "It's our birthday month! 🎉"])

    return "\n".join(lines) + "\n", duration

def run_git(*args):
    subprocess.run(['git', *args], check=True, capture_output=True, text=True)

def send_discord_success(duration: str):
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if not webhook_url: return

    payload = {
        "embeds": [{
            "title": "✅ README Updated",
            "description": f"Skiddle & Scarletnine: **{duration}**",
            "color": 15277667,
            "footer": {"text": "Skiddle Bot | GitHub Actions"}
        }]
    }

    req = request.Request(
        webhook_url, 
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with request.urlopen(req):
            print("✅ Discord notification sent.")
    except error.URLError as e:
        print(f"❌ Discord failed: {e}")

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    dynamic_content, duration = build_dynamic_content(now)

    if not README_PATH.exists():
        print("README.md not found.")
        return

    content = README_PATH.read_text(encoding="utf-8")
    
    if START_MARKER not in content or END_MARKER not in content:
        print("Markers not found in README.md. Skipping update.")
        return

    # Surgical replacement using string partitioning
    prefix, _, rest = content.partition(START_MARKER)
    _, _, suffix = rest.partition(END_MARKER)
    new_content = f"{prefix}{START_MARKER}\n{dynamic_content}{END_MARKER}{suffix}"

    if new_content != content:
        README_PATH.write_text(new_content, encoding="utf-8")
        try:
            run_git("config", "user.name", AUTHOR_NAME)
            run_git("config", "user.email", AUTHOR_EMAIL)
            run_git("add", str(README_PATH))
            run_git("commit", "-m", "chore: update time-together section [skip ci]")
            run_git("push", "origin", f"HEAD:{BRANCH}")
            send_discord_success(duration)
        except subprocess.CalledProcessError as e:
            print(f"Git failed: {e.stderr}")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    main()
