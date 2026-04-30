"""
Sports scores and box scores via ESPN's public API (no key required).
Fetches yesterday's results for NBA, MLB, NFL, and college basketball.
"""

import time
from datetime import datetime, timedelta

import requests

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; MyDailyDashboard/1.0)"})

ESPN = "https://site.api.espn.com/apis/site/v2/sports"

SPORTS = {
    "NBA":  "basketball/nba",
    "MLB":  "baseball/mlb",
    "NFL":  "football/nfl",
    "NCAA Basketball": "basketball/mens-college-basketball",
}

# Keywords used to detect favourite team games
FAVOURITE_TEAMS = [
    {"name": "Washington Wizards",    "sport": "NBA",            "keywords": ["Wizards"]},
    {"name": "Washington Nationals",  "sport": "MLB",            "keywords": ["Nationals"]},
    {"name": "Washington Commanders", "sport": "NFL",            "keywords": ["Commanders"]},
    {"name": "UNC Tar Heels",         "sport": "NCAA Basketball","keywords": ["North Carolina", "Tar Heels"]},
    {"name": "Davidson Wildcats",     "sport": "NCAA Basketball","keywords": ["Davidson"]},
]


def fetch_sports(date_str=None):
    """Return scored games for all sports for a given date (YYYYMMDD, default yesterday)."""
    if not date_str:
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    all_results = {}
    for sport_name, sport_path in SPORTS.items():
        games = _scoreboard(sport_name, sport_path, date_str)
        if games:
            all_results[sport_name] = games
        time.sleep(0.2)

    return all_results


def _scoreboard(sport_name, sport_path, date_str):
    try:
        resp = _SESSION.get(f"{ESPN}/{sport_path}/scoreboard", params={"dates": date_str}, timeout=10)
        resp.raise_for_status()
        events = resp.json().get("events", [])
    except Exception as exc:
        print(f"  Warning: could not fetch {sport_name} scoreboard: {exc}")
        return []

    games = []
    for event in events:
        game = _parse_event(event, sport_name, sport_path)
        if game:
            games.append(game)
    return games


def _parse_event(event, sport_name, sport_path):
    try:
        comp = event["competitions"][0]
        competitors = comp["competitors"]
        status_type = comp.get("status", {}).get("type", {})

        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

        home_name   = home["team"]["displayName"]
        away_name   = away["team"]["displayName"]
        home_score  = home.get("score", "–")
        away_score  = away.get("score", "–")
        status_desc = status_type.get("description", "")
        completed   = status_type.get("completed", False)

        # Detect favourite teams
        favourite = None
        for fav in FAVOURITE_TEAMS:
            if fav["sport"] != sport_name:
                continue
            for kw in fav["keywords"]:
                if kw.lower() in home_name.lower() or kw.lower() in away_name.lower():
                    favourite = fav["name"]
                    break

        # Headline (ESPN sometimes provides a short game recap)
        headlines = comp.get("headlines", [])
        headline = headlines[0].get("description", "") if headlines else ""

        # For favourite team games, fetch top performers
        leaders = []
        if favourite and completed:
            leaders = _top_performers(event.get("id"), sport_path)

        return {
            "home":      home_name,
            "away":      away_name,
            "home_score": home_score,
            "away_score": away_score,
            "status":    status_desc,
            "completed": completed,
            "favourite": favourite,
            "headline":  headline,
            "leaders":   leaders,
        }
    except Exception:
        return None


def _top_performers(event_id, sport_path):
    """Fetch top statistical leaders for a game."""
    if not event_id:
        return []
    try:
        resp = _SESSION.get(
            f"{ESPN}/{sport_path}/summary",
            params={"event": event_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        leaders = []
        for cat in data.get("leaders", []):
            top = (cat.get("leaders") or [{}])[0]
            athlete = top.get("athlete") or {}
            team    = top.get("team") or {}
            leaders.append({
                "category": cat.get("displayName") or cat.get("name", ""),
                "player":   athlete.get("displayName", ""),
                "value":    top.get("displayValue", ""),
                "team":     team.get("abbreviation", ""),
            })
        return leaders[:6]   # cap at 6 categories
    except Exception:
        return []
