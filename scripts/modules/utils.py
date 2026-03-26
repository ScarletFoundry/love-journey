import calendar
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import request

# Constants
ENCODING = "utf-8"


def run_git(args: List[str]) -> None:
    """Runs a git command."""
    try:
        subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(
            f"Git command failed: {' '.join(args)}\nError: {e.stderr}", file=sys.stderr
        )
        raise


def get_progress_bar(percent: float, width: int = 20) -> str:
    """Generates a text-based progress bar."""
    filled = int(width * percent)
    bar = "█" * filled + "░" * (width - filled)
    return f"`{bar} {percent * 100:.1f}%`"


def calculate_age(born_str: str, today: datetime.date) -> int:
    """Calculates age based on birthday string and today's date."""
    try:
        born = datetime.datetime.strptime(born_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Invalid date format for birthday: {born_str}", file=sys.stderr)
        return 0
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def get_duration_stats(start_dt: datetime.datetime, now: datetime.datetime) -> str:
    """
    Calculates years, months, and days between start_dt and now.
    """
    years = now.year - start_dt.year
    months = now.month - start_dt.month
    days = now.day - start_dt.day

    if days < 0:
        # Calculate days in previous month
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1
        _, days_in_prev = calendar.monthrange(prev_year, prev_month)
        days += days_in_prev
        months -= 1

    if months < 0:
        months += 12
        years -= 1

    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months > 0:
        parts.append(f"{months} month{'s' if months != 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")

    return ", ".join(parts) if parts else "0 days"


def get_anniversary_progress(
    start_dt: datetime.datetime, now: datetime.datetime
) -> float:
    """Calculates the percentage progress towards the next anniversary."""
    today_year = now.year

    # Determine previous and next anniversary
    try:
        this_year_anniversary = start_dt.replace(year=today_year)
    except ValueError:
        # Handle Leap Year
        this_year_anniversary = start_dt.replace(year=today_year, day=28)

    if now < this_year_anniversary:
        next_anniversary = this_year_anniversary
        try:
            prev_anniversary = start_dt.replace(year=today_year - 1)
        except ValueError:
            prev_anniversary = start_dt.replace(year=today_year - 1, day=28)
    else:
        prev_anniversary = this_year_anniversary
        try:
            next_anniversary = start_dt.replace(year=today_year + 1)
        except ValueError:
            next_anniversary = start_dt.replace(year=today_year + 1, day=28)

    total_days = (next_anniversary - prev_anniversary).days
    days_passed = (now - prev_anniversary).days

    if total_days <= 0:
        return 1.0

    return days_passed / total_days


def send_discord_notification(message: str) -> None:
    """Sends a notification to Discord via Webhook."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    if not webhook_url:
        return

    data = json.dumps({"content": message}).encode(ENCODING)
    req = request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    try:
        with request.urlopen(req) as res:
            if res.status != 204:
                print(f"Discord notification status: {res.status}")
    except Exception as e:
        print(f"Failed to send Discord notification: {e}", file=sys.stderr)


def load_json(path: Path) -> Dict[str, Any]:
    """Loads a JSON file."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding=ENCODING))
