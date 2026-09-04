"""Regenerate the animated hero SVG from live GitHub stats."""
import json
import os
import subprocess
from pathlib import Path

USER = "slowtalks"
OUT = Path("assets/hero-v3.svg")

QUERY = """
{
  user(login: "%s") {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
    }
  }
}
""" % USER


def gh_api(query: str) -> dict:
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)["data"]


def compute(data: dict) -> dict:
    u = data["user"]
    repos = u["repositories"]["nodes"]

    stars = sum(r["stargazerCount"] for r in repos)
    followers = u["followers"]["totalCount"]
    repo_count = u["repositories"]["totalCount"]
    commits = (
        u["contributionsCollection"]["totalCommitContributions"]
        + u["contributionsCollection"]["restrictedContributionsCount"]
    )

    lang_totals: dict[str, tuple[int, str]] = {}
    for r in repos:
        for edge in r["languages"]["edges"]:
            name = edge["node"]["name"]
            color = edge["node"]["color"] or "#8B5CF6"
            size, _ = lang_totals.get(name, (0, color))
            lang_totals[name] = (size + edge["size"], color)

    total = sum(s for s, _ in lang_totals.values()) or 1
    top = sorted(
        [(n, s, c) for n, (s, c) in lang_totals.items()],
        key=lambda x: -x[1],
    )[:4]

    return {
        "stars": stars,
        "commits": commits,
        "repos": repo_count,
        "followers": followers,
        "langs": [(n, s / total * 100, c) for n, s, c in top],
        "total_bytes": total,
    }


def ring_offset(value: int, cap: int = 20) -> float:
    """Rough visual fill: caps at `cap` to always leave a nice partial arc."""
    circumference = 238.7
    ratio = min(value / cap, 0.92) if value else 0.05
    return round(circumference * (1 - ratio), 1)


def render(stats: dict) -> str:
    BAR_MAX = 820
    langs = stats["langs"]

    # widths in the animated bar
    widths = [round(pct / 100 * BAR_MAX, 1) for _, pct, _ in langs]
    offsets = [0.0]
    for w in widths[:-1]:
        offsets.append(round(offsets[-1] + w, 1))

    # legend items (2 per row, up to 4)
    legend_positions = [(0, 0), (180, 0), (380, 0), (560, 0)]
    legend_svg = ""
    for i, ((name, pct, color), (x, y)) in enumerate(zip(langs, legend_positions)):
        legend_svg += (
            f'<g transform="translate({x},{y})">'
            f'<circle cx="6" cy="8" r="5" fill="{color}"/>'
            f'<text x="18" y="12">{name}</text>'
            f'<text x="{18 + max(60, len(name) * 7)}" y="12" fill="#c9a8ff">{pct:.1f}%</text>'
            f'</g>'
        )

    bars_svg = ""
    for i, ((_, _, color), w, off) in enumerate(zip(langs, widths, offsets)):
        delay = 0.7 + i * 0.2
        bars_svg += (
            f'<rect x="{off}" y="0" width="0" height="14" fill="{color}">'
            f'<animate attributeName="width" from="0" to="{w}" dur="1.2s" fill="freeze" begin="{delay}s"/>'
            f'</rect>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 340" width="900" height="340" font-family="'JetBrains Mono','Segoe UI',monospace">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1a0f2e"/>
      <stop offset="50%" stop-color="#0e0820"/>
      <stop offset="100%" stop-color="#0b0b0f"/>
    </linearGradient>
    <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#c9a8ff"/>
      <stop offset="100%" stop-color="#8B5CF6"/>
    </linearGradient>
    <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#8B5CF6" stop-opacity="0"/>
      <stop offset="50%" stop-color="#c9a8ff" stop-opacity="1"/>
      <stop offset="100%" stop-color="#8B5CF6" stop-opacity="0"/>
    </linearGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="2.5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="langclip"><rect x="0" y="0" width="820" height="14" rx="7"/></clipPath>
  </defs>

  <rect width="900" height="340" rx="16" fill="url(#bg)" stroke="#8B5CF6" stroke-opacity="0.4" stroke-width="1.5"/>

  <g opacity="0.06" stroke="#8B5CF6" stroke-width="0.5">
    <path d="M0 60H900M0 120H900M0 180H900M0 240H900M0 300H900"/>
    <path d="M60 0V340M180 0V340M300 0V340M420 0V340M540 0V340M660 0V340M780 0V340"/>
  </g>

  <rect y="0" width="200" height="2" fill="url(#scan)">
    <animate attributeName="x" from="-200" to="900" dur="4s" repeatCount="indefinite"/>
  </rect>
  <rect y="338" width="200" height="2" fill="url(#scan)">
    <animate attributeName="x" from="900" to="-200" dur="4s" repeatCount="indefinite"/>
  </rect>

  <g transform="translate(40, 70)">
    <text font-size="10" font-weight="600" fill="#c9d1d9" opacity="0.7" letter-spacing="1.5">$ WHOAMI</text>
    <text y="42" font-size="42" font-weight="800" fill="#ffffff">slow<tspan fill="#8B5CF6">_<animate attributeName="opacity" values="0;1;1;0" dur="1.2s" repeatCount="indefinite"/></tspan></text>
    <text y="72" font-size="13" font-weight="500" fill="#c9a8ff" opacity="0.85">// building quiet things from home</text>
    <text y="92" font-size="13" font-weight="500" fill="#c9a8ff" opacity="0.6">// slowtalks.be · python / html / js</text>
  </g>

  <g transform="translate(475, 50)">
    <g>
      <circle cx="45" cy="45" r="38" stroke="#161b22" stroke-width="6" fill="none"/>
      <circle cx="45" cy="45" r="38" stroke="url(#ring)" stroke-width="6" fill="none" stroke-linecap="round"
              stroke-dasharray="238.7" stroke-dashoffset="238.7" transform="rotate(-90 45 45)" filter="url(#glow)">
        <animate attributeName="stroke-dashoffset" from="238.7" to="{ring_offset(stats['stars'])}" dur="1.4s" fill="freeze" begin="0.2s"/>
      </circle>
      <text x="45" y="53" text-anchor="middle" font-size="26" font-weight="700" fill="#c9a8ff">{stats['stars']}</text>
      <text x="45" y="108" text-anchor="middle" font-size="10" font-weight="600" fill="#c9d1d9" opacity="0.7" letter-spacing="1.5">STARS</text>
    </g>
    <g transform="translate(105,0)">
      <circle cx="45" cy="45" r="38" stroke="#161b22" stroke-width="6" fill="none"/>
      <circle cx="45" cy="45" r="38" stroke="url(#ring)" stroke-width="6" fill="none" stroke-linecap="round"
              stroke-dasharray="238.7" stroke-dashoffset="238.7" transform="rotate(-90 45 45)" filter="url(#glow)">
        <animate attributeName="stroke-dashoffset" from="238.7" to="{ring_offset(stats['commits'], cap=50)}" dur="1.4s" fill="freeze" begin="0.35s"/>
      </circle>
      <text x="45" y="53" text-anchor="middle" font-size="26" font-weight="700" fill="#c9a8ff">{stats['commits']}</text>
      <text x="45" y="108" text-anchor="middle" font-size="10" font-weight="600" fill="#c9d1d9" opacity="0.7" letter-spacing="1.5">COMMITS</text>
    </g>
    <g transform="translate(210,0)">
      <circle cx="45" cy="45" r="38" stroke="#161b22" stroke-width="6" fill="none"/>
      <circle cx="45" cy="45" r="38" stroke="url(#ring)" stroke-width="6" fill="none" stroke-linecap="round"
              stroke-dasharray="238.7" stroke-dashoffset="238.7" transform="rotate(-90 45 45)" filter="url(#glow)">
        <animate attributeName="stroke-dashoffset" from="238.7" to="{ring_offset(stats['repos'], cap=15)}" dur="1.4s" fill="freeze" begin="0.5s"/>
      </circle>
      <text x="45" y="53" text-anchor="middle" font-size="26" font-weight="700" fill="#c9a8ff">{stats['repos']}</text>
      <text x="45" y="108" text-anchor="middle" font-size="10" font-weight="600" fill="#c9d1d9" opacity="0.7" letter-spacing="1.5">REPOS</text>
    </g>
    <g transform="translate(315,0)">
      <circle cx="45" cy="45" r="38" stroke="#161b22" stroke-width="6" fill="none"/>
      <circle cx="45" cy="45" r="38" stroke="url(#ring)" stroke-width="6" fill="none" stroke-linecap="round"
              stroke-dasharray="238.7" stroke-dashoffset="238.7" transform="rotate(-90 45 45)" filter="url(#glow)">
        <animate attributeName="stroke-dashoffset" from="238.7" to="{ring_offset(stats['followers'], cap=20)}" dur="1.4s" fill="freeze" begin="0.65s"/>
      </circle>
      <text x="45" y="53" text-anchor="middle" font-size="26" font-weight="700" fill="#c9a8ff">{stats['followers']}</text>
      <text x="45" y="108" text-anchor="middle" font-size="10" font-weight="600" fill="#c9d1d9" opacity="0.7" letter-spacing="1.5">FOLLOWERS</text>
    </g>
  </g>

  <g transform="translate(40, 210)">
    <text font-size="10" font-weight="600" fill="#c9d1d9" opacity="0.7" letter-spacing="1.5">$ CAT ~/.LANGS</text>
    <g transform="translate(0, 20)">
      <rect x="0" y="0" width="820" height="14" rx="7" fill="#161b22"/>
      <g clip-path="url(#langclip)">
        {bars_svg}
      </g>
    </g>
    <g transform="translate(0, 55)" font-size="11" font-weight="600" fill="#c9d1d9">
      {legend_svg}
    </g>
  </g>

  <text x="40" y="322" font-size="10" font-weight="600" fill="#c9d1d9" opacity="0.4" letter-spacing="1.2">$ echo "slow and steady. ship anyway." | ./life.sh</text>
</svg>
"""


def main() -> None:
    data = gh_api(QUERY)
    stats = compute(data)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(stats), encoding="utf-8")
    print(f"wrote {OUT} — stars={stats['stars']} commits={stats['commits']} "
          f"repos={stats['repos']} followers={stats['followers']}")


if __name__ == "__main__":
    main()
