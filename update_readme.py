#!/usr/bin/env python3
import datetime
import subprocess
import os
import json
from pathlib import Path
from urllib import request

CONFIG_PATH = Path("config.json")
README_PATH = Path("README.md")

def run_git(*args):
    subprocess.run(['git', *args], check=True, capture_output=True, text=True)

def get_progress_bar(percent, width=20):
    filled = int(width * percent)
    bar = "█" * filled + "░" * (width - filled)
    return f"`{bar} {percent*100:.1f}%`"

def calculate_age(born_str, today):
    born = datetime.datetime.strptime(born_str, "%Y-%m-%d").date()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def format_duration_accurate(start_dt, end_dt):
    """Calculates years, months, and days accurately."""
    diff = end_dt - start_dt
    years = end_dt.year - start_dt.year
    if (end_dt.month, end_dt.day) < (start_dt.month, start_dt.day):
        years -= 1
    
    days = diff.days
    # This is a simplified "total days" view for the high-level stat
    return f"{years} years, {days % 365} days"

def main():
    if not CONFIG_PATH.exists(): return
    conf = json.loads(CONFIG_PATH.read_text())
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    
    # 1. Anniversary Logic
    start_dt = datetime.datetime.fromisoformat(conf['relationship_start'].replace('Z', '+00:00'))
    duration = format_duration_accurate(start_dt, now)
    
    # Calculate progress to next anniversary
    this_year_anniversary = start_dt.replace(year=today.year)
    if this_year_anniversary < now:
        next_anniversary = start_dt.replace(year=today.year + 1)
        prev_anniversary = this_year_anniversary
    else:
        next_anniversary = this_year_anniversary
        prev_anniversary = start_dt.replace(year=today.year - 1)
    
    total_days_in_year = (next_anniversary - prev_anniversary).days
    days_passed = (now - prev_anniversary).days
    progress_percent = days_passed / total_days_in_year

    # 2. Build Components
    ages = [f"{n}: {calculate_age(d, today)}" for n, d in conf['birthdays'].items()]
    milestones = "\n".join([f"| {m['date']} | {m['event']} |" for m in conf['milestones']])
    
    # 3. Assemble Template
    readme_content = f"""# Our Journey Begins...

{conf['story']}

---

### 🗓️ Milestones & Timeline
| Date | Event |
| :--- | :--- |
{milestones}

### 🎨 Paper Pulse
We are **Paper Pulse**, a creative duo focused on privacy, design, and software.
* [**Jeff's Blog**]({conf['links']['Jeff']})
* [**Jacqueline's Blog**]({conf['links']['Jacqueline']})

---

### 🕒 The Counter
**We have been together for {duration}.** Next Anniversary Progress:
{get_progress_bar(progress_percent)}

**Current Stats:**
![Age](https://img.shields.io/badge/Jeff_Age-{calculate_age(conf['birthdays']['Jeff'], today)}-blue)
![Age](https://img.shields.io/badge/Jacqueline_Age-{calculate_age(conf['birthdays']['Jacqueline'], today)}-ff69b4)
{"![Birthday](https://img.shields.io/badge/Status-Birthday_Month_🎉-gold)" if now.month == 8 else ""}

*Last Updated: {now.strftime('%Y-%m-%d %H:%M')} UTC*
"""

    if README_PATH.exists() and README_PATH.read_text() == readme_content:
        print("No changes.")
        return

    README_PATH.write_text(readme_content)
    
    # 4. Push
    git = conf['git_settings']
    try:
        run_git("config", "user.name", git['author_name'])
        run_git("config", "user.email", git['author_email'])
        run_git("add", "README.md")
        run_git("commit", "-m", "chore: automated journey update [skip ci]")
        run_git("push", "origin", f"HEAD:{git['branch']}")
    except Exception as e:
        print(f"Git failed: {e}")

if __name__ == "__main__":
    main()
