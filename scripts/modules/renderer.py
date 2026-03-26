import calendar
import datetime
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .utils import (
    calculate_age,
    get_anniversary_progress,
    get_duration_stats,
    get_progress_bar,
)


def render_stylized_quote(text: str, author: str, color: str = "FF69B4") -> str:
    """Renders a stylized HTML quote block for personal notes."""
    clean_color = color.lstrip("#")
    return f"""
<div align="center">
<table width="85%">
  <tr>
    <td style="border-left: 5px solid #{clean_color}; padding: 20px; background-color: rgba(0,0,0,0.03); border-radius: 8px;">
      <p align="center" style="font-family: 'Georgia', serif; font-size: 1.2em; font-style: italic; line-height: 1.6;">
        "{text}"
      </p>
      <p align="right">
        <strong>— {author}</strong>
      </p>
    </td>
  </tr>
</table>
</div>
"""


def get_profile_card(
    name: str,
    color: str,
    profiles: Dict,
    skills_data: Dict,
    links: Dict,
    role_data: Dict = None,
) -> str:
    """Generates an HTML table cell for a profile."""
    p = profiles.get(name, {})
    gh = p.get("github", "")
    note = p.get("note", "")
    bio = p.get("bio", "")
    link = links.get(name, "#")
    skills = skills_data.get(name, [])
    roles = role_data.get(name, []) if role_data else []

    # Global Settings
    global_settings = p.get("_global_settings", {})
    use_global_cdn = global_settings.get("use_cdn", False)
    global_cdn_url = global_settings.get("cdn_base_url", "").rstrip("/")

    avatar_url = p.get("avatar_url", "")

    clean_color = color.replace("#", "")
    css_color = f"#{clean_color}"

    badges = " ".join(
        [
            f'<img src="https://img.shields.io/badge/-{s.replace(" ", "_")}-{clean_color}?style=flat-square" alt="{s}">'
            for s in skills
        ]
    )

    role_badges = ""
    if roles:
        role_badges = "<br><b>Paper Pulse Roles:</b><br>" + " ".join(
            [
                f'<img src="https://img.shields.io/badge/-{r.replace(" ", "_")}-grey?style=flat-square" alt="{r}">'
                for r in roles
            ]
        )

    if avatar_url:
        if (
            use_global_cdn
            and global_cdn_url
            and not avatar_url.startswith(("http://", "https://"))
        ):
            avatar = f"{global_cdn_url}/{avatar_url.lstrip('/')}"
        else:
            avatar = avatar_url
    else:
        avatar = (
            f"https://github.com/{gh}.png?size=100"
            if gh
            else "https://github.com/identicons/default.png"
        )

    return f"""
<td width="50%" valign="top">
<p align="center">
<a href="https://github.com/{gh}">
<img src="{avatar}" width="100" style="border-radius:50%; border: 3px solid {css_color};" alt="{name}'s avatar">
</a>
<br>
<strong>{name}</strong>
<br>
<em>"{note}"</em>
</p>
{bio}
<br><br>
{badges}
{role_badges}
<br>
<p align="center">
<br>
<a href="{link}"><b>Website</b></a> | <a href="https://github.com/{gh}"><b>GitHub</b></a>
</p>
</td>
"""


def generate_mermaid_timeline(milestones: List[Dict]) -> str:
    """Generates a Mermaid timeline from milestones."""
    timeline_groups = defaultdict(list)
    for m in milestones:
        date_val = str(m.get("date", ""))
        date_parts = date_val.split("-")
        year = date_parts[0]
        event = m.get("event", "").strip()

        if year.lower() == "future":
            continue

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

    return (
        "```mermaid\ntimeline\n    title Our Evolution\n"
        + "\n".join(timeline_lines)
        + "\n```"
    )


def render_sections(
    conf: Dict[str, Any], now: datetime.datetime
) -> Tuple[Dict[str, str], Optional[str]]:
    """Renders all sections and returns them as a dictionary of components."""
    today = now.date()
    discord_msg = None

    start_dt = datetime.datetime.fromisoformat(
        conf["relationship_start"].replace("Z", "+00:00")
    )

    # Calculate global stats
    duration_str = get_duration_stats(start_dt, now)
    progress_percent = get_anniversary_progress(start_dt, now)

    # Theme & Config data
    theme = conf.get("theme", {})
    accent = theme.get("accent_color", "FF69B4")
    birthdays = conf.get("birthdays", {})
    milestones_data = conf.get("milestones", [])

    # Celebration Logic
    celebration_banner = ""
    if today.month == start_dt.month and today.day == start_dt.day:
        years_together = today.year - start_dt.year
        celebration_banner = (
            f"\n> ### 🎉 Happy {years_together}th Anniversary! Cheers to us! 🥂\n"
        )
        discord_msg = f"🎉 Happy {years_together}th Anniversary! 🥂 To many more years!"
    else:
        for name, bday_str in birthdays.items():
            bday = datetime.datetime.strptime(bday_str, "%Y-%m-%d").date()
            if today.month == bday.month and today.day == bday.day:
                age = calculate_age(bday_str, today)
                celebration_banner = f"\n> ### 🎂 Happy Birthday, {name}! Wishing you a wonderful {age}th year! 🎉\n"
                discord_msg = f"🎂 Happy Birthday, {name}! 🎉 Wishing you a wonderful {age}th year!"

    # Pass global settings into profiles for CDN logic
    global_settings = conf.get("global_settings", {})
    profiles = conf.get("profiles", {})
    for p_name in profiles:
        profiles[p_name]["_global_settings"] = global_settings

    # Profile Cards
    role_data = conf.get("roles", {})
    jeff_card = get_profile_card(
        "Jeff",
        "3498db",
        conf.get("profiles", {}),
        conf.get("skills", {}),
        conf.get("links", {}),
        role_data,
    )
    jacq_card = get_profile_card(
        "Jacqueline",
        accent,
        conf.get("profiles", {}),
        conf.get("skills", {}),
        conf.get("links", {}),
        role_data,
    )

    # Engagement Badge
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

    # Birthday Badge
    birthday_badge = ""
    if now.month == 8:
        birthday_badge = f"![Birthday](https://img.shields.io/badge/Status-Birthday_Month_🎉-{accent}?style=flat-square)"

    # Build Sections dictionary
    sections = {}

    # Health Support Section
    health = conf.get("health_status", {})
    if health:
        status = health.get("status", "Recovering")
        last_update = health.get("last_update", "")
        message = health.get("message", "")
        personal_note = health.get("personal_note", "")
        treatment_start = health.get("treatment_start", "")

        day_counter = ""
        if treatment_start:
            try:
                start_date = datetime.datetime.strptime(
                    treatment_start, "%Y-%m-%d"
                ).date()
                days_fighting = (today - start_date).days + 1
                day_counter = f"![Day {days_fighting}](https://img.shields.io/badge/Battle_Day-{days_fighting}-red?style=for-the-badge&logo=heartbeat)\n\n"
            except ValueError:
                pass

        note_block = ""
        if personal_note:
            note_block = render_stylized_quote(personal_note, "Jacqueline", accent)

        sections["health_support"] = f"""### 🎗️ Current Health Status: {status}
<p align="center">{day_counter}</p>

{message}

{note_block}

<p align="right"><i>Last updated: {last_update}</i></p>"""

    # Bluesky Notes Section (Separated by Actor)
    actor_posts = conf.get("bluesky_actor_posts", {})
    if actor_posts:
        notes_content = "### 🦋 Personal Notes & Updates\n"

        for name, posts in actor_posts.items():
            icon = "✍️" if name == "Jeff" else "📖"
            notes_content += f"#### {icon} From {name}\n"
            for post in posts:
                text = post.get("text", "")
                date = post.get("date", "")
                url = post.get("url", "#")
                notes_content += f"""
> *"{text}"*
> — [{date}]({url})
>
"""
        sections["bluesky_notes"] = notes_content.strip()

    sections["story"] = f"""# Our Journey Begins...
{celebration_banner}
{conf.get("story", "")}"""

    milestones_list = [f"| {m['date']} | {m['event']} |" for m in milestones_data]
    sections["milestones"] = f"""### 🗓️ Milestones & Timeline
{generate_mermaid_timeline(milestones_data)}

| Date | Event |
| :--- | :--- |
{"\n".join(milestones_list)}"""

    # Gallery Section (Chapter-based)
    gallery_conf = conf.get("gallery", {})
    chapters = gallery_conf.get("chapters", [])
    use_cdn = gallery_conf.get("use_cdn", global_settings.get("use_cdn", False))
    cdn_base = gallery_conf.get("cdn_base_url") or global_settings.get(
        "cdn_base_url", ""
    )

    if chapters:
        gallery_content = "### 📸 Moments\n"

        for chapter in chapters:
            title = chapter.get("title", "")
            desc = chapter.get("description", "")
            images = chapter.get("images", [])

            chapter_html = f"#### 📖 {title}\n"
            if desc:
                chapter_html += f"> *{desc}*\n\n"

            # Resolve all image paths first
            resolved_images = []
            for img in images:
                path = img.get("path", "")
                caption = img.get("caption", "")
                img_src = path
                if (
                    use_cdn
                    and cdn_base
                    and not path.startswith(("http://", "https://"))
                ):
                    img_src = f"{cdn_base.rstrip('/')}/{path.lstrip('/')}"
                resolved_images.append({"src": img_src, "caption": caption})

            # Dynamic Layout based on image count
            count = len(resolved_images)
            layout_html = ""

            if count == 1:
                # Showcase (Full Width)
                img = resolved_images[0]
                layout_html = f"""
<p align="center">
  <a href="{img["src"]}">
    <img src="{img["src"]}" style="max-width: 100%; width: 600px; height: auto; border-radius: 12px; border: 1px solid #eee;">
  </a>
  <br>
  <sub>{img["caption"]}</sub>
</p>
"""
            elif count == 2:
                # 50/50 Split
                layout_html = '<table width="100%"><tr>\n'
                for img in resolved_images:
                    layout_html += f'  <td width="50%" align="center" valign="bottom"><a href="{img["src"]}"><img src="{img["src"]}" style="width: 100%; aspect-ratio: 4/5; object-fit: cover; border-radius: 10px;"></a><br><sub>{img["caption"]}</sub></td>\n'
                layout_html += "</tr></table>\n"
            elif count > 0:
                # 3-Column Grid (Square)
                cells = []
                for img in resolved_images:
                    cells.append(
                        f'<td align="center" width="33%" valign="bottom"><a href="{img["src"]}"><img src="{img["src"]}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 8px; border: 1px solid #eee;"></a><br><sub>{img["caption"]}</sub></td>'
                    )

                rows = [cells[i : i + 3] for i in range(0, len(cells), 3)]
                table = '<table width="100%">\n'
                for row in rows:
                    table += "  <tr>\n    " + "\n    ".join(row) + "\n  </tr>\n"
                table += "</table>\n"
                layout_html = table

            gallery_content += chapter_html + layout_html + "\n---\n"

        sections["gallery"] = gallery_content

    # Paper Pulse Section
    pp_conf = conf.get("paper_pulse", {})
    latest = pp_conf.get("latest_release", {})
    releases = pp_conf.get("releases", [])
    channel = pp_conf.get("channel", "https://www.youtube.com/@paperpulsemusic")

    pp_header = f"""### 🎨 Paper Pulse
In January 11, 2026, we joined forces to create **Paper Pulse**—a journey of combining our ideas into music using AI assistance, alongside our shared focus on privacy, design, and software.

[**Visit our YouTube Channel →**]({channel})"""

    pp_music_card = ""
    if latest:
        title = latest.get("title", "New Track")
        cover = latest.get("cover", "")
        link = latest.get("link", "#")
        desc = latest.get("description", "")

        if (
            global_settings.get("use_cdn")
            and cover
            and not cover.startswith(("http://", "https://"))
        ):
            cover = (
                f"{global_settings.get('cdn_base_url').rstrip('/')}/{cover.lstrip('/')}"
            )

        pp_music_card = f"""
<table width="100%">
  <tr>
    <td width="35%" align="center">
      <a href="{link}">
        <img src="{cover}" width="240" style="border-radius:10px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" alt="{title}">
      </a>
    </td>
    <td width="65%" valign="top">
      <h4>🎵 Featured: {title}</h4>
      <p>{desc}</p>
      <a href="{link}"><b>Watch on YouTube →</b></a>
    </td>
  </tr>
</table>"""

    pp_history = ""
    if releases:
        rows = []
        for r in releases:
            rows.append(
                f"| {r.get('date', '-')} | [{r.get('title')}]({r.get('link')}) |"
            )

        pp_history = f"""
<details>
<summary>📂 View Release History</summary>
<br>

| Date | Track Title |
| :--- | :--- |
{"\n".join(rows)}
</details>"""

    sections["paper_pulse"] = f"""{pp_header}

{pp_music_card}
{pp_history}

<table width="100%">
<tr>
{jeff_card}
{jacq_card}
</tr>
</table>"""

    # The Counter Section
    anniversary_conf = conf.get("anniversary_settings", {})
    countdown_str = ""
    if anniversary_conf.get("show_countdown"):
        try:
            today_year = today.year
            anniversary_this_year = start_dt.replace(year=today_year).date()
            if today > anniversary_this_year:
                anniversary_next = start_dt.replace(year=today_year + 1).date()
            else:
                anniversary_next = anniversary_this_year

            days_left = (anniversary_next - today).days
            if days_left == 0:
                countdown_str = "\n**🎉 Today is our Anniversary! 🎉**\n"
            else:
                label = anniversary_conf.get("label", "Next Anniversary")
                countdown_str = (
                    f"\n**⏳ {days_left} days remaining until our {label}**\n"
                )
        except Exception:
            pass

    sections["counter"] = f"""### 🕒 The Counter
<div align="center">
  <p><b>We have been together for</b></p>
  <h3>✨ {duration_str} ✨</h3>
  <br>
  <p>Next Anniversary Progress</p>
  {get_progress_bar(progress_percent, width=30)}
  {countdown_str}
  <br>

  <p><b>Relationship Status</b></p>
  ![Jeff](https://img.shields.io/badge/Jeff-{calculate_age(birthdays.get("Jeff", "1997-01-01"), today)}_y.o.-blue?style=for-the-badge) ![Jacqueline](https://img.shields.io/badge/Jacqueline-{calculate_age(birthdays.get("Jacqueline", "1999-01-01"), today)}_y.o.-{accent}?style=for-the-badge)
  <br>
  {engagement_badge} {birthday_badge}

  <br>
  <sub><i>Last Updated: {now.strftime("%Y-%m-%d")} UTC</i></sub>
</div>"""

    # Pets Section
    pets = conf.get("pets", [])
    if pets:
        pet_content = '### 🐾 The Quiet Supporters\n\n<div align="center">\n<table width="90%">\n  <tr>\n'
        for pet in pets:
            name = pet.get("name")
            role = pet.get("role")
            joined = pet.get("joined")
            avatar = pet.get("avatar", "")

            if (
                global_settings.get("use_cdn")
                and avatar
                and not avatar.startswith(("http://", "https://"))
            ):
                avatar = f"{global_settings.get('cdn_base_url').rstrip('/')}/{avatar.lstrip('/')}"

            pet_content += f"""    <td align="center" width="{100 // len(pets)}%">
      <img src="{avatar}" width="120" style="border-radius:50%; border: 2px solid #eee; box-shadow: 0 4px 10px rgba(0,0,0,0.1);" alt="{name}">
      <br><br>
      <strong>{name}</strong>
      <br>
      <img src="https://img.shields.io/badge/-{role.replace(" ", "_")}-grey?style=flat-square" alt="{role}">
      <br>
      <small>Since {joined.split("-")[0]}</small>
    </td>\n"""
        pet_content += "  </tr>\n</table>\n</div>"
        sections["pets"] = pet_content

    return sections, discord_msg
