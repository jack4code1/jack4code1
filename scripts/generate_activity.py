"""Render a compact activity chart using only this account's contribution counts."""

import argparse
from datetime import date, datetime, timezone
from html import escape
import json
from pathlib import Path
import subprocess

USERNAME = "jack4code1"
QUERY = '''query {
  user(login: "jack4code1") {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}'''


def fetch_days():
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={QUERY}"],
        check=True, capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    if payload.get("errors"):
        raise RuntimeError("GitHub did not return a complete contribution calendar")
    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [day for week in calendar["weeks"] for day in week["contributionDays"]]
    assert days and len({day["date"] for day in days}) == len(days)
    assert sum(day["contributionCount"] for day in days) == calendar["totalContributions"]
    assert all(isinstance(day["contributionCount"], int) and day["contributionCount"] >= 0 for day in days)
    return sorted(days, key=lambda day: day["date"])[-31:]


def render(days):
    # Keep a nonzero axis for an empty period; the plotted values remain exactly zero.
    maximum = max(4, max(day["contributionCount"] for day in days))
    top = ((maximum + 3) // 4) * 4
    x0, x1, y0, y1 = 56, 864, 73, 163
    coordinates = [(x0 + i * (x1 - x0) / max(1, len(days) - 1),
                    y1 - day["contributionCount"] / top * (y1 - y0))
                   for i, day in enumerate(days)]
    points = " ".join(f"{x:.2f},{y:.2f}" for x, y in coordinates)
    grid = []
    for i in range(5):
        y = y1 - i / 4 * (y1 - y0)
        grid.append(f'<path d="M{x0} {y}H{x1}" stroke="#2a2f45"/>')
        grid.append(f'<text x="40" y="{y+4}" text-anchor="end" class="tick">{int(top*i/4)}</text>')
    for i in (0, len(days)//3, 2*len(days)//3, len(days)-1):
        label = date.fromisoformat(days[i]["date"]).strftime("%b %d")
        grid.append(f'<text x="{coordinates[i][0]}" y="187" text-anchor="middle" class="tick">{label}</text>')
    dots = "".join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.7" fill="#7dcfff"><title>{day["date"]}: {day["contributionCount"]} contributions</title></circle>'
                   for (x, y), day in zip(coordinates, days))
    total = sum(day["contributionCount"] for day in days)
    summary = f"{USERNAME}: {total} contributions from {days[0]['date']} through {days[-1]['date']}."
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="222" viewBox="0 0 900 222" role="img" aria-labelledby="title desc">
<title id="title">Contribution activity · {USERNAME}</title>
<desc id="desc">{escape(summary)} Counts retrieved directly from GitHub. Updated {updated}.</desc>
<defs><linearGradient id="area" x2="0" y2="1"><stop stop-color="#7aa2f7" stop-opacity=".22"/><stop offset="1" stop-color="#7aa2f7" stop-opacity="0"/></linearGradient></defs>
<style>text{{font-family:Arial,Helvetica,sans-serif}}.tick{{fill:#9aa5ce;font-size:11px}}</style>
<rect width="900" height="222" rx="12" fill="#1a1b27"/>
<text x="27" y="33" fill="#7aa2f7" font-size="17" font-weight="600">Contribution activity</text>
<text x="873" y="33" text-anchor="end" fill="#9aa5ce" font-size="12">LAST {len(days)} DAYS · {total} CONTRIBUTIONS</text>
{''.join(grid)}
<polygon points="{x0},{y1} {points} {x1},{y1}" fill="url(#area)"/>
<polyline points="{points}" fill="none" stroke="#7aa2f7" stroke-width="2" stroke-linejoin="round"/>
{dots}
<text x="873" y="209" text-anchor="end" fill="#7c86a9" font-size="10">@{USERNAME} · {updated}</text>
</svg>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    days = fetch_days()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(days), encoding="utf-8")
    print(f"Activity chart generated from {len(days)} days of GitHub contributions.")


if __name__ == "__main__":
    main()
