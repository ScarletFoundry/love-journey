#!/usr/bin/env python3
"""
Updates the README.md with the latest relationship stats.
This script calculates the duration of the relationship, generates a progress bar
towards the next anniversary, and updates the markdown file with these details.
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Add scripts directory to path for module imports
sys.path.append(str(Path(__file__).parent / "scripts"))

from modules.renderer import render_sections
from modules.utils import ENCODING, load_json, run_git, send_discord_notification

# Constants
CONFIG_PATH = Path("config.json")
DOCS_DIR = Path("docs")


def validate_config(conf: Dict[str, Any]) -> bool:
    """Performs basic validation on the configuration dictionary."""
    required_keys = ["relationship_start", "birthdays", "global_settings", "outputs"]
    missing = [k for k in required_keys if k not in conf]
    if missing:
        print(f"::error::Missing required config keys: {', '.join(missing)}")
        return False
    return True


def main():
    """Main execution flow for updating the README."""
    parser = argparse.ArgumentParser(description="Update Love Journey documentation.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the update without writing files or pushing to Git.",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("🛠️  DRY RUN MODE: No changes will be saved or pushed.")

    # 1. Load configuration
    conf = load_json(CONFIG_PATH)
    if not conf:
        print(f"::error::Config file not found or empty at {CONFIG_PATH}")
        sys.exit(1)

    if not validate_config(conf):
        sys.exit(1)

    # 1.1 Load modular configs
    global_settings = conf.get("global_settings", {})
    modules_path = global_settings.get("config_modules_path")
    if modules_path:
        modules_dir = Path(modules_path)
        if modules_dir.exists():
            for json_file in modules_dir.glob("*.json"):
                module_data = load_json(json_file)
                if module_data:
                    conf.update(module_data)
            print(f"Loaded modular configs from {modules_path}")

    # 1.1.5 Load Bluesky Feed if enabled
    bluesky_conf = global_settings.get("bluesky", {})
    if bluesky_conf.get("fetch_latest"):
        actors = bluesky_conf.get("actors", [])
        limit_per_actor = bluesky_conf.get("limit_per_actor", 5)
        all_posts = {}

        for actor in actors:
            name = actor.get("name")
            handle = actor.get("handle")
            hashtags = [h.lstrip("#").lower() for h in actor.get("hashtags", [])]

            if not handle:
                continue

            try:
                from urllib import request as bsky_request

                bsky_url = f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={handle}&limit=50"
                req = bsky_request.Request(
                    bsky_url,
                    headers={
                        "User-Agent": "LoveJourneyBot/1.0",
                        "Cache-Control": "no-cache",
                    },
                )

                actor_posts = []
                with bsky_request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        feed_data = json.loads(response.read().decode(ENCODING))
                        feed = feed_data.get("feed", [])

                        for item in feed:
                            if len(actor_posts) >= limit_per_actor:
                                break

                            post = item.get("post", {})
                            record = post.get("record", {})
                            text = record.get("text", "")

                            if hashtags:
                                has_any_tag = False
                                facets = record.get("facets", [])
                                post_tags = []
                                for facet in facets:
                                    for feature in facet.get("features", []):
                                        if (
                                            feature.get("$type")
                                            == "app.bsky.richtext.facet#tag"
                                        ):
                                            post_tags.append(
                                                feature.get("tag", "").lower()
                                            )

                                for tag in hashtags:
                                    if tag in post_tags or f"#{tag}" in text.lower():
                                        has_any_tag = True
                                        break
                                if not has_any_tag:
                                    continue

                            actor_posts.append(
                                {
                                    "text": text,
                                    "date": record.get("createdAt", "").split("T")[0],
                                    "url": f"https://bsky.app/profile/{handle}/post/{post.get('uri', '').split('/')[-1]}",
                                }
                            )

                if actor_posts:
                    all_posts[name] = actor_posts
                    print(
                        f"Successfully loaded {len(actor_posts)} Bluesky posts from {name} ({handle})"
                    )

            except Exception as e:
                print(f"::warning::Failed to fetch Bluesky feed for {handle}: {e}")

        if all_posts:
            conf["bluesky_actor_posts"] = all_posts

    # 1.2 Load remote configs if enabled
    if global_settings.get("remote_config_enabled"):
        remote_urls = global_settings.get("remote_config_urls", [])
        for url in remote_urls:
            try:
                from urllib import request as remote_request

                req = remote_request.Request(
                    url,
                    headers={
                        "User-Agent": "LoveJourneyBot/1.0",
                        "Cache-Control": "no-cache",
                    },
                )
                with remote_request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        remote_data = json.loads(response.read().decode(ENCODING))
                        if isinstance(remote_data, dict):
                            conf.update(remote_data)
                            print(f"Successfully loaded remote config: {url}")
                        else:
                            print(
                                f"::warning::Remote config from {url} is not a valid JSON object."
                            )
            except Exception as e:
                print(f"::warning::Failed to load remote config from {url}: {e}")

    # 2. Get current time in UTC
    now = datetime.datetime.now(datetime.timezone.utc)

    # 3. Generate section components using the renderer module
    sections, discord_msg = render_sections(conf, now)

    # 3.1 Prepare Branding Footer
    theme = conf.get("theme", {})
    branding = theme.get("branding", {})
    footer_content = ""
    if branding:
        footer_text = branding.get("footer_text", "")
        back_to_top = branding.get("show_back_to_top", False)
        footer_parts = []
        if back_to_top:
            footer_parts.append(
                '<p align="center"><a href="#top"><b>Back to Top ↑</b></a></p>'
            )
        if footer_text:
            footer_parts.append(f'<p align="center"><sub>{footer_text}</sub></p>')
        if footer_parts:
            footer_content = "\n\n---\n\n" + "\n".join(footer_parts)

    # 4. Handle multiple output files
    output_mapping = conf.get("outputs", {"README.md": list(sections.keys())})
    if not args.dry_run:
        DOCS_DIR.mkdir(exist_ok=True)

    updated_files = []
    for filename, section_keys in output_mapping.items():
        target_path = (
            Path(filename) if filename.lower() == "readme.md" else DOCS_DIR / filename
        )
        ordered_content = [sections[s] for s in section_keys if s in sections]
        file_content = (
            '<a name="top"></a>\n\n'
            + "\n\n---\n\n".join(ordered_content)
            + footer_content
            + "\n"
        )

        if target_path.exists():
            try:
                if target_path.read_text(encoding=ENCODING) == file_content:
                    continue
            except UnicodeDecodeError:
                pass

        updated_files.append(str(target_path))
        if not args.dry_run:
            target_path.write_text(file_content, encoding=ENCODING)
            print(f"✅ {target_path} updated.")
        else:
            print(f"📝 [DRY RUN] Would update: {target_path}")

    if not updated_files:
        print("✨ No changes needed. All files are up to date.")
        return

    # 6. Handle Discord Notifications
    if discord_msg and not args.dry_run:
        send_discord_notification(discord_msg)

    # 7. Git Automation
    git_conf = conf.get("git_settings")
    if git_conf and os.environ.get("GITHUB_ACTIONS") and not args.dry_run:
        try:
            author_name = git_conf.get("author_name", "skiddle-bot")
            author_email = git_conf.get("author_email", "bot@skiddle.id")
            branch = git_conf.get("branch", "main")

            status = os.popen("git status --porcelain README.md docs/").read().strip()
            if status:
                print(f"Committing changes as {author_name}...")
                run_git(["config", "user.name", author_name])
                run_git(["config", "user.email", author_email])
                run_git(["add", "README.md"])
                if DOCS_DIR.exists():
                    run_git(["add", "docs/"])

                commit_msg = "chore: automated journey update 🕒 [skip ci]"
                if "HEALTH.md" in status:
                    commit_msg = "chore: automated health status update 🎗️ [skip ci]"
                elif "PAPER_PULSE.md" in status:
                    commit_msg = "chore: automated music update 🎵 [skip ci]"

                run_git(["commit", "-m", commit_msg])
                run_git(["push", "origin", f"HEAD:{branch}"])
                print(f"🚀 Changes pushed to {branch} successfully.")
            else:
                print("No changes detected for Git.")
        except Exception as e:
            print(f"::error::Git operations failed: {e}")


if __name__ == "__main__":
    main()
