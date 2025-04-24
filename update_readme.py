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

AUTHORS = [
    ("arcestia", "7936962+arcestia@users.noreply.github.com"),
    ("scarletnine", "15015459+scarletnine@users.noreply.github.com"),
]
BRANCH         = "main" # Or your main branch name
# ──────────────────────────────────────────────────────────────────────────────

def calculate_age(born_date: datetime.date, today: datetime.date) -> int:
    """Calculates age based on birth date and current date."""
    age = today.year - born_date.year
    if today.month < born_date.month or (today.month == born_date.month and today.day < born_date.day):
        age -= 1
    return age

def format_duration(td: datetime.timedelta) -> str:
    total_minutes = td.days * 24 * 60 + td.seconds // 60
    years = total_minutes // (365 * 24 * 60)
    days  = (total_minutes % (365 * 24 * 60)) // (24 * 60)
    hours = (total_minutes % (24 * 60)) // 60
    mins  = total_minutes % 60
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    parts.append(f"{mins} minute{'s' if mins>1 else ''}")
    return ", ".join(parts)

def build_dynamic_content(now: datetime.datetime) -> str:
    td = now - START_DT
    duration = format_duration(td)

    today_date = now.date()
    skiddle_age = calculate_age(SKIDDLE_BORN, today_date)
    scarlet_age = calculate_age(SCARLET_BORN, today_date)

    # The content to be inserted between the markers
    lines = [
        f"We have been together for **{duration}**.",
        "", # Add a blank line for separation
        f"Jeff is **{skiddle_age}** years old, and Jacqueline is **{scarlet_age}** years old."
    ]

    # Add birthday note if current month is August
    if now.month == 8:
        lines.append("") # Blank line before birthday note
        lines.append("It's our birthday month! 🎉")

    return "\n".join(lines) + "\n" # Ensure trailing newline

def run_git_command(*args):
    """Helper to run git commands and raise exception on error."""
    try:
        result = subprocess.run(['git', *args], capture_output=True, text=True, check=True)
        print(f"Git command successful: git {' '.join(args)}")
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: git {' '.join(args)}")
        print(f"Stderr: {e.stderr.strip()}")
        print(f"Stdout: {e.stdout.strip()}")
        raise

def main():
    now = datetime.datetime.utcnow()
    dynamic_content = build_dynamic_content(now)

    original_content = ""
    if os.path.exists(README):
        with open(README, "r", encoding="utf-8") as f:
            original_content = f.read()

    lines = original_content.splitlines(keepends=True)

    start_index = -1
    end_index = -1

    # Find the marker lines
    for i, line in enumerate(lines):
        if START_MARKER in line:
            start_index = i
        if END_MARKER in line:
            end_index = i

    if start_index == -1 or end_index == -1 or start_index >= end_index:
        print(f"Markers '{START_MARKER}' and '{END_MARKER}' not found in order in {README}. Appending dynamic content.")
        # If markers are not found, just append the dynamic content
        new_content = original_content + dynamic_content
    else:
        # Construct the new content
        before_marker = "".join(lines[:start_index + 1])
        after_marker = "".join(lines[end_index:])
        new_content = before_marker + dynamic_content + after_marker

    # Write the potentially updated content back to the file
    with open(README, "w", encoding="utf-8") as f:
        f.write(new_content)

    # Check if the file content has actually changed
    with open(README, "r", encoding="utf-8") as f:
        current_content = f.read()

    if current_content != original_content:
        print(f"{README} has been updated. Committing changes.")

        # Determine the author/committer based on the current hour
        author_index = now.hour % len(AUTHORS)
        author_name, author_email = AUTHORS[author_index]

        # Configure Git user
        run_git_command('config', 'user.name', author_name)
        run_git_command('config', 'user.email', author_email)

        # Add the README.md file
        run_git_command('add', README)

        # Build the commit message
        commit_message = f"chore: Update README with duration and ages [skip ci]"

        # Commit the changes
        run_git_command('commit', '--message', commit_message)

        # Push the changes
        run_git_command('push', 'origin', f'HEAD:{BRANCH}')
    else:
        print(f"{README} has no changes. No commit needed.")


if __name__ == "__main__":
    main()
