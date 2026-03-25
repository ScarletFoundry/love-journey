#!/usr/bin/env python3
"""
Updates the README.md with the latest relationship stats.
This script calculates the duration of the relationship, generates a progress bar
towards the next anniversary, and updates the markdown file with these details.
"""

import calendar
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import request

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


def load_config() -> Dict[str, Any]:
    """Loads configuration from JSON file."""
    if not CONFIG_PATH.exists():
        print(f"Config file not found: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text(encoding=ENCODING))


def generate_readme_content(
    conf: Dict[str, Any], now: datetime.datetime
) -> Tuple[str, Optional[str]]:
    """Assembles the README content based on config and current stats."""
    today = now.date()
    discord_msg = None

    # Parse start date
    # Handle 'Z' manually for compatibility
    start_dt = datetime.datetime.fromisoformat(
        conf["relationship_start"].replace("Z", "+00:00")
    )

    # Stats
    duration_str = get_duration_stats(start_dt, now)
    progress_percent = get_anniversary_progress(start_dt, now)

    # Milestones logic
    milestones_data = conf.get("milestones", [])
    milestones_list = [f"| {m['date']} | {m['event']} |" for m in milestones_data]
    milestones_str = "\n".join(milestones_list)

    # Mermaid Timeline Logic
    from collections import defaultdict

    timeline_groups = defaultdict(list)
    for m in milestones_data:
        date_parts = m["date"].split("-")
        year = date_parts[0]
        event = m["event"].strip()
        if len(date_parts) > 1:
            try:
                month_idx = int(date_parts[1])
                month_name = calendar.month_name[month_idx]
                event = f"{month_name}: {event}"
            except (ValueError, IndexError):
                pass
        timeline_groups[year].append(event)
    timeline_lines = []
    for year, events in sorted(timeline_groups.items()):
        events_str = " : ".join(events)
        timeline_lines.append(f"    {year} : {events_str}")
    mermaid_timeline = (
        "```mermaid\ntimeline\n    title Our Evolution\n"
        + "\n".join(timeline_lines)
        + "\n```"
    )

    # Profile & Skill Logic
    theme = conf.get("theme", {})
    accent = theme.get("accent_color", "FF69B4")
    profiles = conf.get("profiles", {})
    skills_data = conf.get("skills", {})
    links = conf.get("links", {})

    def get_profile_card(name: str, color: str):
        p = profiles.get(name, {})
        gh = p.get("github", "")
        note = p.get("note", "")
        bio = p.get("bio", "")
        link = links.get(name, "#")
        skills = skills_data.get(name, [])

        badges = " ".join(
            [
                f"![{s}](https://img.shields.io/badge/-{s.replace(' ', '_')}-{color}?style=flat-square)"
                for s in skills
            ]
        )

        avatar = (
            f"https://github.com/{gh}.png?size=100"
            if gh
            else "https://github.com/identicons/default.png"
        )

        return f"""
<td width="50%" valign="top">
<p align="center">
<a href="https://github.com/{gh}">
<img src="{avatar}" width="100" style="border-radius:50%; border: 3px solid #{color};" alt="{name}'s avatar">
</a>
<br>
<strong>{name}</strong>
<br>
<em>"{note}"</em>
</p>
{bio}
<br><br>
{badges}
<br>
<p align="center">
<a href="{link}"><b>Website</b></a> | <a href="https://github.com/{gh}"><b>GitHub</b></a>
</p>
</td>
"""

    jeff_card = get_profile_card("Jeff", "blue")
    jacq_card = get_profile_card("Jacqueline", accent)

    # Milestone logic for engagement
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

    # Celebration Mode Logic
    celebration_banner = ""
    birthdays = conf.get("birthdays", {})
    if today.month == start_dt.month and today.day == start_dt.day:
        years_together = today.year - start_dt.year
        celebration_banner = (
            f"\n> ### 🎉 Happy {years_together}th Anniversary! Cheers to us! 🥂\n"
        )
        discord_msg = f"🎉 Happy {years_together}th Anniversary! 🥂 To many more beautiful years together!"
    else:
        for name, bday_str in birthdays.items():
            bday = datetime.datetime.strptime(bday_str, "%Y-%m-%d").date()
            if today.month == bday.month and today.day == bday.day:
                age = calculate_age(bday_str, today)
                celebration_banner = f"\n> ### 🎂 Happy Birthday, {name}! Wishing you a wonderful {age}th year! 🎉\n"
                discord_msg = f"🎂 Happy Birthday, {name}! 🎉 Hope you have an amazing {age}th year!"

    # Conditional Birthday Badge
    birthday_badge = ""
    if now.month == 8:
        birthday_badge = f"![Birthday](https://img.shields.io/badge/Status-Birthday_Month_🎉-{accent}?style=flat-square)"

    # Assemble Template
    content = f"""# Our Journey Begins...
{celebration_banner}
{conf.get("story", "")}

---

### 🗓️ Milestones & Timeline
{mermaid_timeline}

| Date | Event |
| :--- | :--- |
{milestones_str}

### 🎨 Paper Pulse
In January 11, 2026, we joined forces to create **Paper Pulse**—a journey of combining our ideas into music using AI assistance, alongside our shared focus on privacy, design, and software.

<table width="100%">
<tr>
{jeff_card}
{jacq_card}
</tr>
</table>

---

### 🕒 The Counter
**We have been together for {duration_str}.** Next Anniversary Progress:
{get_progress_bar(progress_percent)}

**Current Stats:**
![Jeff](https://img.shields.io/badge/Jeff-{calculate_age(birthdays.get("Jeff", "1997-01-01"), today)}_y.o.-blue?style=flat-square) ![Jacqueline](https://img.shields.io/badge/Jacqueline-{calculate_age(birthdays.get("Jacqueline", "1999-01-01"), today)}_y.o.-{accent}?style=flat-square)
{engagement_badge}
{birthday_badge}

*Last Updated: {now.strftime("%Y-%m-%d")} UTC*
"""
    return content, discord_msg


def main():
    conf = load_config()
    now = datetime.datetime.now(datetime.timezone.utc)

    new_content, discord_msg = generate_readme_content(conf, now)

    if README_PATH.exists():
        try:
            current_content = README_PATH.read_text(encoding=ENCODING)
            if current_content == new_content:
                print("No changes needed.")
                return
        except UnicodeDecodeError:
            print("Existing README has unknown encoding, rewriting...", file=sys.stderr)

    README_PATH.write_text(new_content, encoding=ENCODING)
    print("README.md updated.")

    if discord_msg:
        send_discord_notification(discord_msg)

    git_conf = conf.get("git_settings")
    if git_conf:
        try:
            run_git(["config", "user.name", git_conf["author_name"]])
            run_git(["config", "user.email", git_conf["author_email"]])
            run_git(["add", "README.md"])
            run_git(["commit", "-m", "chore: automated journey update [skip ci]"])
            run_git(["push", "origin", f"HEAD:{git_conf['branch']}"])
            print("Changes pushed to Git.")
        except Exception as e:
            print(f"Git operations skipped or failed: {e}")


if __name__ == "__main__":
    main()
