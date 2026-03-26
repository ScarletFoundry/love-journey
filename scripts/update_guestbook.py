#!/usr/bin/env python3
"""
Support Guestbook Generator
Fetches comments from a GitHub Issue and renders them into SUPPORT.md.
"""

import datetime
import json
import os
import sys
from pathlib import Path
from urllib import request

# Add parent directory to path to import shared modules
sys.path.append(str(Path(__file__).parent.parent))
from scripts.modules.utils import ENCODING, load_json, run_git

# Constants
CONFIG_PATH = Path("config.json")
SUPPORT_FILE = Path("docs/SUPPORT.md")


def fetch_guestbook_comments(repo, issue_id, token, limit=20):
    """Fetches comments from a GitHub issue using the REST API."""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_id}/comments?per_page={limit}&sort=created&direction=desc"

    headers = {
        "User-Agent": "LoveJourneyBot/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        req = request.Request(url, headers=headers)
        with request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                return json.loads(response.read().decode(ENCODING))
    except Exception as e:
        print(f"::error::Failed to fetch comments from issue #{issue_id}: {e}")
    return []


def render_guestbook(comments, issue_url):
    """Renders the comments into Markdown."""
    header = """# ❤️ Support Guestbook

*This guestbook is a collection of warm messages and prayers from our friends and family. Your support gives us the strength to keep moving forward.*

---

"""

    if not comments:
        content = f"\n*No messages yet. Be the first to leave a word of support on [GitHub Issue]({issue_url})!*\n"
    else:
        content = f"<p align='center'><i>Showing the latest {len(comments)} messages. [Leave a message here →]({issue_url})</i></p>\n\n"

        for c in comments:
            user = c.get("user", {}).get("login", "Anonymous")
            avatar = c.get("user", {}).get("avatar_url", "")
            body = c.get("body", "").replace("\n", "<br>")
            date = c.get("created_at", "").split("T")[0]

            content += f"""
<table width="100%">
  <tr>
    <td width="12%" align="center" valign="top">
      <img src="{avatar}" width="60" style="border-radius:50%; border: 2px solid #eee;" alt="{user}">
    </td>
    <td width="88%" valign="top">
      <strong>{user}</strong> <small>on {date}</small>
      <br><br>
      {body}
    </td>
  </tr>
</table>
"""

    footer = f"\n\n---\n<p align='center'><a href='../README.md'><b>← Back to Home</b></a></p>\n"
    return header + content + footer


def main():
    # 1. Load config
    conf = load_json(CONFIG_PATH)
    guestbook_conf = conf.get("global_settings", {}).get("guestbook", {})

    if not guestbook_conf.get("enabled"):
        print("Guestbook is disabled in config.")
        return

    issue_id = guestbook_conf.get("issue_id")
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")

    if not repo:
        print("::error::GITHUB_REPOSITORY environment variable not found.")
        sys.exit(1)

    if not issue_id:
        print("::error::No issue_id found in config.json.")
        sys.exit(1)

    issue_url = f"https://github.com/{repo}/issues/{issue_id}"

    # 2. Fetch comments
    print(f"Fetching comments from {repo} Issue #{issue_id}...")
    comments = fetch_guestbook_comments(
        repo, issue_id, token, guestbook_conf.get("limit", 20)
    )

    # 3. Render
    markdown = render_guestbook(comments, issue_url)

    # 4. Write to file
    SUPPORT_FILE.parent.mkdir(exist_ok=True)
    SUPPORT_FILE.write_text(markdown, encoding=ENCODING)
    print(f"✅ {SUPPORT_FILE} updated.")

    # 5. Git Automation (only in CI)
    if os.environ.get("GITHUB_ACTIONS"):
        git_conf = conf.get("git_settings", {})
        author_name = git_conf.get("author_name", "skiddle-bot")
        author_email = git_conf.get("author_email", "bot@skiddle.id")

        status = os.popen(f"git status --porcelain {SUPPORT_FILE}").read().strip()
        if status:
            print("Committing guestbook changes...")
            run_git(["config", "user.name", author_name])
            run_git(["config", "user.email", author_email])
            run_git(["add", str(SUPPORT_FILE)])
            run_git(["commit", "-m", "chore: updated support guestbook ❤️ [skip ci]"])
            run_git(["push", "origin", f"HEAD:{git_conf.get('branch', 'main')}"])
            print("🚀 Guestbook pushed successfully.")
        else:
            print("No new guestbook messages to commit.")


if __name__ == "__main__":
    main()
