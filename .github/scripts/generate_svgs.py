#!/usr/bin/env python3
"""
Generate static SVG stats for GitHub profile README.
Based on: https://www.avivashishta.com/blog/build-animated-github-profile-readme.html
"""
import os
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
USERNAME = "junghyun100"
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

ASSETS_DIR = "assets"

GRAPHQL_QUERY = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""

def fetch_repos():
    """Fetch all non-fork repos with languages."""
    repos = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            params={"per_page": 100, "page": page, "type": "owner", "sort": "updated"},
            headers=HEADERS
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        for repo in data:
            if not repo["fork"]:
                lang_resp = requests.get(repo["languages_url"], headers=HEADERS)
                lang_resp.raise_for_status()
                languages = lang_resp.json()
                repos.append({
                    "name": repo["name"],
                    "description": repo["description"] or "",
                    "language": repo["language"],
                    "languages": languages,
                    "updated_at": repo["updated_at"],
                    "stargazers_count": repo["stargazers_count"],
                    "forks_count": repo["forks_count"],
                })
        page += 1
    return repos

def fetch_user_stats():
    """Fetch user stats (total stars, commits, etc.)."""
    resp = requests.get(f"https://api.github.com/users/{USERNAME}", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def fetch_contributions():
    """Fetch contribution data via GitHub GraphQL API."""
    if not GITHUB_TOKEN:
        print("Warning: No GITHUB_TOKEN, contribution data will be empty")
        return {}

    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": GRAPHQL_QUERY, "variables": {"username": USERNAME}},
        headers=HEADERS
    )
    resp.raise_for_status()
    data = resp.json()

    if "errors" in data:
        print(f"GraphQL errors: {data['errors']}")
        return {}

    return data.get("data", {}).get("user", {}).get("contributionsCollection", {}).get("contributionCalendar", {})


def parse_contributions(calendar_data):
    """Parse GraphQL contribution calendar into flat list."""
    contributions = []
    weeks = calendar_data.get("weeks", [])
    for week in weeks:
        for day in week.get("contributionDays", []):
            contributions.append({
                "date": day["date"],
                "count": day["contributionCount"],
                "level": day["contributionLevel"]
            })
    return contributions

def generate_stats_svg(user_data, repos):
    """Generate GitHub stats SVG (replaces github-readme-stats)."""
    total_stars = sum(r["stargazers_count"] for r in repos)
    total_forks = sum(r["forks_count"] for r in repos)
    total_repos = len(repos)

    # Colors for tokyo night theme
    BG = "#1a1b26"
    FG = "#a9b1d6"
    ACCENT = "#5865f2"
    TITLE = "#c0caf5"
    GREEN = "#9ece6a"

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="495" height="195" viewBox="0 0 495 195" xmlns="http://www.w3.org/2000/svg">
  <rect width="495" height="195" fill="{BG}" rx="8"/>
  <text x="20" y="30" font-family="JetBrains Mono, monospace" font-size="14" font-weight="bold" fill="{TITLE}">junghyun100's GitHub Stats</text>

  <!-- Total Repos -->
  <rect x="20" y="45" width="140" height="55" fill="#24283b" rx="6"/>
  <text x="30" y="70" font-family="JetBrains Mono, monospace" font-size="11" fill="{FG}">Total Repositories</text>
  <text x="30" y="90" font-family="JetBrains Mono, monospace" font-size="22" font-weight="bold" fill="{FG}">{total_repos}</text>

  <!-- Total Stars -->
  <rect x="175" y="45" width="140" height="55" fill="#24283b" rx="6"/>
  <text x="185" y="70" font-family="JetBrains Mono, monospace" font-size="11" fill="{FG}">Total Stars</text>
  <text x="185" y="90" font-family="JetBrains Mono, monospace" font-size="22" font-weight="bold" fill="{GREEN}">{total_stars}</text>

  <!-- Total Forks -->
  <rect x="330" y="45" width="140" height="55" fill="#24283b" rx="6"/>
  <text x="340" y="70" font-family="JetBrains Mono, monospace" font-size="11" fill="{FG}">Total Forks</text>
  <text x="340" y="90" font-family="JetBrains Mono, monospace" font-size="22" font-weight="bold" fill="{FG}">{total_forks}</text>

  <!-- Commits (estimate) -->
  <rect x="20" y="115" width="140" height="55" fill="#24283b" rx="6"/>
  <text x="30" y="140" font-family="JetBrains Mono, monospace" font-size="11" fill="{FG}">Total Commits</text>
  <text x="30" y="160" font-family="JetBrains Mono, monospace" font-size="22" font-weight="bold" fill="{FG}">{user_data.get("total_private_commits", "N/A")}</text>

  <!-- Issues/PRs -->
  <rect x="175" y="115" width="140" height="55" fill="#24283b" rx="6"/>
  <text x="185" y="140" font-family="JetBrains Mono, monospace" font-size="11" fill="{FG}">Contributions</text>
  <text x="185" y="160" font-family="JetBrains Mono, monospace" font-size="22" font-weight="bold" fill="{ACCENT}">{user_data.get("contributions", "N/A")}</text>

  <!-- Profile views -->
  <rect x="330" y="115" width="140" height="55" fill="#24283b" rx="6"/>
  <text x="340" y="140" font-family="JetBrains Mono, monospace" font-size="11" fill="{FG}">Followers</text>
  <text x="340" y="160" font-family="JetBrains Mono, monospace" font-size="22" font-weight="bold" fill="{FG}">{user_data.get("followers", 0)}</text>
</svg>'''
    return svg


def generate_languages_svg(repos):
    """Generate top languages SVG (replaces github-readme-stats top-langs)."""
    # Language breakdown
    lang_bytes = defaultdict(int)
    for r in repos:
        for lang, bytes_count in r["languages"].items():
            lang_bytes[lang] += bytes_count

    top_langs = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)[:8]

    BG = "#1a1b26"
    FG = "#a9b1d6"
    ACCENT = "#5865f2"
    TITLE = "#c0caf5"

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="495" height="195" viewBox="0 0 495 195" xmlns="http://www.w3.org/2000/svg">
  <rect width="495" height="195" fill="{BG}" rx="8"/>
  <text x="20" y="30" font-family="JetBrains Mono, monospace" font-size="14" font-weight="bold" fill="{TITLE}">Most Used Languages</text>
'''

    if not top_langs:
        svg += f'<text x="20" y="70" font-family="JetBrains Mono, monospace" font-size="14" fill="{FG}">No language data</text></svg>'
        return svg

    # Bar chart
    max_bytes = top_langs[0][1]
    total_bytes = sum(b for _, b in top_langs)
    bar_max_width = 380
    y_start = 50
    row_height = 16

    lang_colors = {
        "Java": "#b07219", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
        "Python": "#3572A5", "SCSS": "#c6538c", "Vue": "#42b883",
        "Rust": "#dea584", "Go": "#00ADD8", "Shell": "#89e051",
        "HTML": "#e34c26", "CSS": "#563d7c", "Dockerfile": "#384d54",
        "C": "#555555", "C++": "#f34b7d", "C#": "#178600",
        "Kotlin": "#F18E33", "Swift": "#ffac45", "PHP": "#4F5D95",
    }

    for i, (lang, bytes_count) in enumerate(top_langs):
        width = max(1, int((bytes_count / max_bytes) * bar_max_width))
        pct = (bytes_count / total_bytes) * 100
        color = lang_colors.get(lang, ACCENT)
        y = y_start + i * row_height

        svg += f'''
  <rect x="20" y="{y}" width="455" height="14" fill="#24283b" rx="3"/>
  <rect x="20" y="{y}" width="{width}" height="14" fill="{color}" rx="3"/>
  <text x="30" y="{y + 10}" font-family="JetBrains Mono, monospace" font-size="10" fill="{FG}">{lang}</text>
  <text x="470" y="{y + 10}" font-family="JetBrains Mono, monospace" font-size="10" fill="{FG}" text-anchor="end">{pct:.1f}%</text>
'''

    svg += '''</svg>'''
    return svg

def generate_streak_svg(contributions):
    """Generate streak stats SVG (replaces streak-stats)."""
    if not contributions:
        return ""

    # Sort by date
    contribs = sorted(contributions, key=lambda x: x["date"])

    # Find current streak
    today = datetime.now().date()
    current_streak = 0
    longest_streak = 0
    temp_streak = 0

    for c in reversed(contribs):
        d = datetime.strptime(c["date"], "%Y-%m-%d").date()
        if c["count"] > 0:
            temp_streak += 1
            if d == today - timedelta(days=current_streak):
                current_streak = temp_streak
        else:
            if temp_streak > longest_streak:
                longest_streak = temp_streak
            temp_streak = 0
            if d < today - timedelta(days=current_streak):
                break

    if temp_streak > longest_streak:
        longest_streak = temp_streak

    BG = "#1a1b26"
    FG = "#a9b1d6"
    ACCENT = "#5865f2"
    FIRE = "#ff6b6b"
    TITLE = "#c0caf5"

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="495" height="195" viewBox="0 0 495 195" xmlns="http://www.w3.org/2000/svg">
  <rect width="495" height="195" fill="{BG}" rx="8"/>
  <text x="20" y="30" font-family="JetBrains Mono, monospace" font-size="14" font-weight="bold" fill="{TITLE}">Contribution Streak</text>

  <rect x="20" y="45" width="140" height="80" fill="#24283b" rx="6"/>
  <text x="30" y="70" font-family="JetBrains Mono, monospace" font-size="11" fill="{FG}">Current Streak</text>
  <text x="30" y="100" font-family="JetBrains Mono, monospace" font-size="36" font-weight="bold" fill="{FIRE}">{current_streak}</text>
  <text x="30" y="120" font-family="JetBrains Mono, monospace" font-size="10" fill="{FG}">days</text>

  <rect x="175" y="45" width="140" height="80" fill="#24283b" rx="6"/>
  <text x="185" y="70" font-family="JetBrains Mono, monospace" font-size="11" fill="{FG}">Longest Streak</text>
  <text x="185" y="100" font-family="JetBrains Mono, monospace" font-size="36" font-weight="bold" fill="{ACCENT}">{longest_streak}</text>
  <text x="185" y="120" font-family="JetBrains Mono, monospace" font-size="10" fill="{FG}">days</text>

  <rect x="330" y="45" width="140" height="80" fill="#24283b" rx="6"/>
  <text x="340" y="70" font-family="JetBrains Mono, monospace" font-size="11" fill="{FG}">Total Contributions</text>
  <text x="340" y="100" font-family="JetBrains Mono, monospace" font-size="36" font-weight="bold" fill="{FG}">{sum(c["count"] for c in contribs)}</text>
  <text x="340" y="120" font-family="JetBrains Mono, monospace" font-size="10" fill="{FG}">(53 weeks)</text>
'''
    svg += '''</svg>'''
    return svg

def generate_heatmap_svg(contributions):
    """Generate contribution heatmap SVG (replaces activity-graph)."""
    if not contributions:
        return ""

    # Build 53 weeks x 7 days grid
    contribs_by_date = {c["date"]: c for c in contributions}

    # Find end date (last Sunday)
    dates = sorted(contribs_by_date.keys())
    end_date = datetime.strptime(dates[-1], "%Y-%m-%d").date()
    # Adjust to Sunday
    while end_date.weekday() != 6:
        end_date += timedelta(days=1)

    start_date = end_date - timedelta(days=53*7 - 1)

    BG = "#1a1b26"
    FG = "#a9b1d6"
    TITLE = "#c0caf5"
    COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="804" height="144" viewBox="0 0 804 144" xmlns="http://www.w3.org/2000/svg">
  <rect width="804" height="144" fill="{BG}"/>
  <text x="10" y="20" font-family="JetBrains Mono, monospace" font-size="12" font-weight="bold" fill="{TITLE}">Contribution Heatmap (Last 53 Weeks)</text>
'''

    # Day labels
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, day in enumerate(days):
        svg += f'<text x="15" y="{35 + i * 16}" font-family="JetBrains Mono, monospace" font-size="8" fill="{FG}" text-anchor="end">{day}</text>\n'

    # Month labels
    months = []
    for week in range(53):
        d = start_date + timedelta(days=week * 7)
        if week == 0 or d.month != (start_date + timedelta(days=(week-1)*7)).month:
            months.append((week, d.strftime("%b")))

    for week, month in months:
        svg += f'<text x="{22 + week * 14}" y="20" font-family="JetBrains Mono, monospace" font-size="8" fill="{FG}" text-anchor="middle">{month}</text>\n'

    # Draw cells
    level_map = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    for week in range(53):
        for day in range(7):
            d = start_date + timedelta(days=week * 7 + day)
            if d > end_date:
                continue
            date_str = d.strftime("%Y-%m-%d")
            level_str = contribs_by_date.get(date_str, {}).get("level", "NONE")
            level = level_map.get(level_str, 0)
            color = COLORS[min(level, 4)]
            x = 22 + week * 14
            y = 25 + day * 16
            svg += f'<rect x="{x}" y="{y}" width="11" height="11" fill="{color}" rx="2"/>\n'

    # Legend
    svg += f'''
  <text x="720" y="20" font-family="JetBrains Mono, monospace" font-size="8" fill="{FG}">Less</text>
'''
    for i, color in enumerate(COLORS):
        svg += f'<rect x="{750 + i * 12}" y="12" width="10" height="10" fill="{color}" rx="2"/>\n'
    svg += f'<text x="{750 + len(COLORS) * 12 + 10}" y="20" font-family="JetBrains Mono, monospace" font-size="8" fill="{FG}">More</text>'

    svg += '''</svg>'''
    return svg

def main():
    print("Fetching GitHub data...")
    repos = fetch_repos()
    user = fetch_user_stats()
    contrib_html = fetch_contributions()
    contributions = parse_contributions(contrib_html)
    print(f"Fetched {len(repos)} repos, {len(contributions)} contribution days")

    print("Generating SVGs...")
    os.makedirs(ASSETS_DIR, exist_ok=True)

    stats_svg = generate_stats_svg(user, repos)
    with open(f"{ASSETS_DIR}/stats.svg", "w") as f:
        f.write(stats_svg)
    print("Generated assets/stats.svg")

    languages_svg = generate_languages_svg(repos)
    with open(f"{ASSETS_DIR}/languages.svg", "w") as f:
        f.write(languages_svg)
    print("Generated assets/languages.svg")

    streak_svg = generate_streak_svg(contributions)
    with open(f"{ASSETS_DIR}/streak.svg", "w") as f:
        f.write(streak_svg)
    print("Generated assets/streak.svg")

    heatmap_svg = generate_heatmap_svg(contributions)
    with open(f"{ASSETS_DIR}/heatmap.svg", "w") as f:
        f.write(heatmap_svg)
    print("Generated assets/heatmap.svg")

    # Also save data for debugging
    with open(f"{ASSETS_DIR}/data.json", "w") as f:
        json.dump({
            "repos": repos,
            "user": user,
            "contributions": contributions,
            "generated_at": datetime.now().isoformat(),
        }, f, indent=2)
    print("Generated assets/data.json")

if __name__ == "__main__":
    main()