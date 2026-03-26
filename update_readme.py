#!/usr/bin/env python3
"""
Updates the README.md with the latest relationship stats.
This script calculates the duration of the relationship, generates a progress bar
towards the next anniversary, and updates the markdown file with these details.
"""

import datetime
import json
import os
import sys
from pathlib import Path

# Add scripts directory to path for module imports
sys.path.append(str(Path(__file__).parent / "scripts"))

from modules.renderer import render_sections
from modules.utils import ENCODING, load_json, run_git, send_discord_notification

# Constants
CONFIG_PATH = Path("config.json")
DOCS_DIR = Path("docs")


def main():
    """Main execution flow for updating the README."""
    # 1. Load configuration
    conf = load_json(CONFIG_PATH)
    if not conf:
        print(
            f"Error: Config file not found or empty at {CONFIG_PATH}", file=sys.stderr
        )
        sys.exit(1)

    # 1.1 Load modular configs
    global_settings = conf.get("global_settings", {})
    modules_path = global_settings.get("config_modules_path")
    if modules_path:
        modules_dir = Path(modules_path)
        if modules_dir.exists():
            for json_file in modules_dir.glob("*.json"):
                module_data = load_json(json_file)
                conf.update(module_data)
            print(f"Loaded modular configs from {modules_path}")

    # 1.2 Load remote configs if enabled
    if global_settings.get("remote_config_enabled"):
        remote_urls = global_settings.get("remote_config_urls", [])
        for url in remote_urls:
            try:
                from urllib import request as remote_request

                req = remote_request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"},
                )
                with remote_request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        remote_data = json.loads(response.read().decode(ENCODING))
                        conf.update(remote_data)
                        print(f"Successfully loaded remote config: {url}")
            except Exception as e:
                print(f"Failed to load remote config from {url}: {e}", file=sys.stderr)

    # 2. Get current time in UTC
    now = datetime.datetime.now(datetime.timezone.utc)

    # 3. Generate section components using the renderer module
    sections, discord_msg = render_sections(conf, now)

    # 4. Handle multiple output files
    output_mapping = conf.get("outputs", {"README.md": list(sections.keys())})
    DOCS_DIR.mkdir(exist_ok=True)

    updated_files = []
    for filename, section_keys in output_mapping.items():
        # Determine target path: README.md stays at root, others go to docs/
        target_path = (
            Path(filename) if filename.lower() == "readme.md" else DOCS_DIR / filename
        )

        # Assemble content for this specific file
        ordered_content = [sections[s] for s in section_keys if s in sections]
        file_content = "\n\n---\n\n".join(ordered_content) + "\n"

        # Check if update is needed
        if target_path.exists():
            try:
                if target_path.read_text(encoding=ENCODING) == file_content:
                    continue
            except UnicodeDecodeError:
                pass

        # Write updated content
        target_path.write_text(file_content, encoding=ENCODING)
        updated_files.append(str(target_path))
        print(f"{target_path} updated successfully.")

    if not updated_files:
        print("No changes needed. All files are up to date.")
        return

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

            # Check for changes across the root and docs directory
            # This ensures we only run git config and commit if something actually changed
            status = os.popen("git status --porcelain README.md docs/").read().strip()

            if status:
                print(f"Changes detected. Committing as {author_name}...")
                run_git(["config", "user.name", author_name])
                run_git(["config", "user.email", author_email])

                # Stage README and the entire docs directory
                run_git(["add", "README.md"])
                if DOCS_DIR.exists():
                    run_git(["add", "docs/"])

                # Create a descriptive commit message based on what changed
                commit_msg = "chore: automated journey update 🕒 [skip ci]"
                if "HEALTH.md" in status:
                    commit_msg = "chore: automated health status update 🎗️ [skip ci]"
                elif "PAPER_PULSE.md" in status:
                    commit_msg = "chore: automated music update 🎵 [skip ci]"

                run_git(["commit", "-m", commit_msg])
                run_git(["push", "origin", f"HEAD:{branch}"])
                print(f"Changes pushed to {branch} successfully.")
            else:
                print(
                    "No changes detected in README.md or docs/. Skipping git operations."
                )

        except Exception as e:
            print(f"Git operations failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
