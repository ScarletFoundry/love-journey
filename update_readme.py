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

def calculate_age(born_str, today):
    born = datetime.datetime.strptime(born_str, "%Y-%m-%d").date()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def format_duration(start_str, end):
    start = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
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

def main():
    if not CONFIG_PATH.exists():
        print("config.json not found!")
        return

    conf = json.loads(CONFIG_PATH.read_text())
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Process Stats
    duration = format_duration(conf['relationship_start'], now)
    ages = [f"{name} is **{calculate_age(date, now.date())}**" for name, date in conf['birthdays'].items()]
    age_line = " years old, and ".join(ages) + " years old."

    # 2. Process Milestones
    milestone_lines = [f"* **{m['date']}:** {m['event']}" for m in conf['milestones']]
    milestone_text = "\n".join(milestone_lines)

    # 3. Assemble README
    readme_content = f"""# Our Journey Begins... and Now, We Share It.

{conf['story']}

---

### 🗓️ Our Milestones
{milestone_text}

---

### 🎨 Our Creative Duo: Paper Pulse
When we aren't coding or managing homelabs, we collaborate as **Paper Pulse**, our shared creative outlet for design, games, and experiments.

### 📖 Read More About Our Journey
* **Laurensius's Blog:** [{conf['links']['Laurensius']}]({conf['links']['Laurensius']})
* **Jacqueline's Blog:** *{conf['links']['Jacqueline']}*

---

We have been together for **{duration}**.

{age_line}
{"" if now.month != 8 else "It's our birthday month! 🎉"}
"""

    # 4. Check & Update
    if README_PATH.exists() and README_PATH.read_text() == readme_content:
        print("No changes needed.")
        return

    README_PATH.write_text(readme_content)
    
    # 5. Git Push
    git = conf['git_settings']
    try:
        run_git("config", "user.name", git['author_name'])
        run_git("config", "user.email", git['author_email'])
        run_git("add", "README.md")
        run_git("commit", "-m", "chore: update journey stats [skip ci]")
        run_git("push", "origin", f"HEAD:{git['branch']}")
        print("Successfully updated README and pushed.")
    except Exception as e:
        print(f"Git failed: {e}")

if __name__ == "__main__":
    main()
