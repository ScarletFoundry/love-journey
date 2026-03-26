#!/usr/bin/env python3
"""
Updates the README.md with the latest relationship stats.
This script calculates the duration of the relationship, generates a progress bar
towards the next anniversary, and updates the markdown file with these details.
"""

import datetime
import os
import sys
from pathlib import Path

# Add scripts directory to path for module imports
sys.path.append(str(Path(__file__).parent / "scripts"))

from modules.renderer import render_sections
from modules.utils import ENCODING, load_json, run_git, send_discord_notification

# Constants
CONFIG_PATH = Path("config.json")
README_PATH = Path("README.md")


def main():
    """Main execution flow for updating the README."""
    # 1. Load configuration
    conf = load_json(CONFIG_PATH)
    if not conf:
        print(
            f"Error: Config file not found or empty at {CONFIG_PATH}", file=sys.stderr
        )
        sys.exit(1)

    # 2. Get current time in UTC
    now = datetime.datetime.now(datetime.timezone.utc)

    # 3. Generate new content using the renderer module
    new_content, discord_msg = render_sections(conf, now)

    # 4. Check if update is actually needed
    if README_PATH.exists():
        try:
            current_content = README_PATH.read_text(encoding=ENCODING)
            if current_content == new_content:
                print("No changes needed. README is up to date.")
                return
        except UnicodeDecodeError:
            print("Existing README has unknown encoding, rewriting...", file=sys.stderr)

    # 5. Write updated content
    README_PATH.write_text(new_content, encoding=ENCODING)
    print("README.md updated successfully.")

    # 6. Handle Discord Notifications if applicable
    if discord_msg:
        send_discord_notification(discord_msg)

    # 7. Git Automation (if configured)
    git_conf = conf.get("git_settings")
    if git_conf and os.environ.get("GITHUB_ACTIONS"):
        try:
            author_name = git_conf.get("author_name", "skiddle-bot")
            author_email = git_conf.get("author_email", "bot@skiddle.id")
            branch = git_conf.get("branch", "main")

            print(f"Committing changes as {author_name}...")
            run_git(["config", "user.name", author_name])
            run_git(["config", "user.email", author_email])
            run_git(["add", "README.md"])

            # Check if there are staged changes before committing
            status = os.popen("git status --porcelain").read()
            if status:
                run_git(["commit", "-m", "chore: automated journey update [skip ci]"])
                run_git(["push", "origin", f"HEAD:{branch}"])
                print("Changes pushed to Git.")
            else:
                print("No changes to commit.")

        except Exception as e:
            print(f"Git operations failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
