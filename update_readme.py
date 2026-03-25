#!/usr/bin/env python3
"""
Updates the README.md with the latest relationship stats.
This script calculates the duration of the relationship, generates a progress bar
towards the next anniversary, and updates the markdown file with these details.
"""

import calendar
import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# Constants
CONFIG_PATH = Path("config.json")
README_PATH = Path("README.md")
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

    if total_days == 0:
        return 1.0

    return days_passed / total_days


def load_config() -> Dict[str, Any]:
    """Loads configuration from JSON file."""
    if not CONFIG_PATH.exists():
        print(f"Config file not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text(encoding=ENCODING))


def generate_readme_content(conf: Dict[str, Any], now: datetime.datetime) -> str:
    """Assembles the README content based on config and current stats."""
    today = now.date()

    # Parse start date
    # Handle 'Z' manually for compatibility
    start_dt = datetime.datetime.fromisoformat(
        conf["relationship_start"].replace("Z", "+00:00")
    )

    # Stats
    duration_str = get_duration_stats(start_dt, now)
    progress_percent = get_anniversary_progress(start_dt, now)

    # Components
    milestones_list = [
        f"| {m['date']} | {m['event']} |" for m in conf.get("milestones", [])
    ]
    milestones_str = "\n".join(milestones_list)

    birthdays = conf.get("birthdays", {})
    jeff_age = calculate_age(birthdays.get("Jeff", "1997-01-01"), today)
    jacq_age = calculate_age(birthdays.get("Jacqueline", "1999-01-01"), today)

    theme = conf.get("theme", {})
    accent = theme.get("accent_color", "FF69B4")

    # Milestone logic for engagement
    milestones_data = conf.get("milestones", [])
    engagement_str = next(
        (m["date"] for m in milestones_data if "Engagement" in m["event"]), None
    )
    engagement_badge = ""
    if engagement_str:
        try:
            eng_date = datetime.datetime.strptime(engagement_str, "%Y-%m-%d").date()
            days_since = (today - eng_date).days
            engagement_badge = f"![Engaged](https://img.shields.io/badge/Engaged-{days_since}_days-gold?style=flat-square&logo=heart)"
        except ValueError:
            pass

    # Conditional Birthday Badge
    birthday_badge = ""
    if now.month == 8:
        birthday_badge = f"![Birthday](https://img.shields.io/badge/Status-Birthday_Month_🎉-{accent}?style=flat-square)"

    links = conf.get("links", {})
    profiles = conf.get("profiles", {})

    # Template
    content = f"""# Our Journey Begins...

{conf.get("story", "")}

---

### 🗓️ Milestones & Timeline
| Date | Event |
| :--- | :--- |
{milestones_str}

### 🎨 Paper Pulse
We are **Paper Pulse**, a creative duo focused on privacy, design, and software.

#### 🧔 Jeff
{profiles.get("Jeff", "Software Engineer.")}
* [**Jeff's Blog**]({links.get("Jeff", "#")})

#### 👩‍🎨 Jacqueline
{profiles.get("Jacqueline", "Designer & Creative Developer.")}
* [**Jacqueline's Blog**]({links.get("Jacqueline", "#")})

---

### 🕒 The Counter
**We have been together for {duration_str}.** Next Anniversary Progress:
{get_progress_bar(progress_percent)}

**Current Stats:**
![Jeff](https://img.shields.io/badge/Jeff-{jeff_age}_y.o.-blue?style=flat-square) ![Jacqueline](https://img.shields.io/badge/Jacqueline-{jacq_age}_y.o.-{accent}?style=flat-square)
{engagement_badge}
{birthday_badge}

*Last Updated: {now.strftime("%Y-%m-%d %H:%M")} UTC*
"""
    return content


def main():
    conf = load_config()
    now = datetime.datetime.now(datetime.timezone.utc)

    new_content = generate_readme_content(conf, now)

    # Check if update is needed
    if README_PATH.exists():
        try:
            current_content = README_PATH.read_text(encoding=ENCODING)
            if current_content == new_content:
                print("No changes needed.")
                return
        except UnicodeDecodeError:
            print("Existing README has unknown encoding, rewriting...", file=sys.stderr)

    # Write new content
    README_PATH.write_text(new_content, encoding=ENCODING)
    print("README.md updated.")

    # Git Operations
    git_conf = conf.get("git_settings")
    if git_conf:
        try:
            # Configure git
            run_git(["config", "user.name", git_conf["author_name"]])
            run_git(["config", "user.email", git_conf["author_email"]])

            # Commit and push
            run_git(["add", "README.md"])
            run_git(["commit", "-m", "chore: automated journey update [skip ci]"])
            run_git(["push", "origin", f"HEAD:{git_conf['branch']}"])
            print("Changes pushed to Git.")
        except Exception as e:
            # Log but don't fail the script if git operations fail
            # (e.g., if running locally without remote access)
            print(f"Git operations skipped or failed: {e}")


if __name__ == "__main__":
    main()
