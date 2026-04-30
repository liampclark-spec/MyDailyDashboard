#!/usr/bin/env python3
"""Daily investment portfolio dashboard — fetches news and emails a digest."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from email_builder import build_html
from news_fetcher import fetch_news
from podcast_fetcher import fetch_podcast_episodes
from sports_fetcher import fetch_sports
from stocks_fetcher import fetch_all_stocks, STOCKS

load_dotenv()

ROOT = Path(__file__).parent
PORTFOLIO_FILE = ROOT / "portfolio.json"
PODCASTS_FILE = ROOT / "podcasts.json"
OUTPUT_DIR = ROOT / "output"

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")
DAYS_BACK = int(os.getenv("DAYS_BACK", "7"))
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "3"))
MAX_EPISODES = int(os.getenv("MAX_EPISODES", "2"))


def load_portfolio():
    with open(PORTFOLIO_FILE) as f:
        return json.load(f)


def load_podcasts():
    with open(PODCASTS_FILE) as f:
        return json.load(f)


def collect_entities(portfolio):
    entities = []
    for managers in portfolio["funds"].values():
        entities.extend(managers)
    entities.extend(portfolio["co_investments"])
    for bucket in portfolio["non_core_holdings"].values():
        entities.extend(bucket)
    return entities


def fetch_all_news(entities, days_back):
    news_data = {}
    total = len(entities)
    for i, entity in enumerate(entities, 1):
        name = entity["name"]
        print(f"  [{i}/{total}] {name}")
        news_data[name] = fetch_news(entity, max_items=MAX_ARTICLES, days_back=days_back)
    return news_data


def fetch_all_podcasts(podcasts, days_back):
    print(f"Fetching episodes for {len(podcasts)} podcasts...")
    result = []
    for i, pod in enumerate(podcasts, 1):
        print(f"  [{i}/{len(podcasts)}] {pod['name']}")
        episodes = fetch_podcast_episodes(pod, max_episodes=MAX_EPISODES, days_back=days_back)
        result.append({**pod, "episodes": episodes})
    return result


def send_email(html_content):
    subject = f"Investment Dashboard – {datetime.now().strftime('%B %d, %Y')}"
    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=[a.strip() for a in EMAIL_TO.split(",")],
        subject=subject,
        html_content=html_content,
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print(f"Email sent — status {response.status_code} → {EMAIL_TO}")


def save_html(html_content):
    OUTPUT_DIR.mkdir(exist_ok=True)
    filename = OUTPUT_DIR / f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    filename.write_text(html_content, encoding="utf-8")
    print(f"Dashboard saved: {filename}")
    return filename


def check_email_config():
    return [k for k in ("SENDGRID_API_KEY", "EMAIL_FROM", "EMAIL_TO") if not os.getenv(k)]


def main():
    parser = argparse.ArgumentParser(description="MyDailyDashboard — investment email digest")
    parser.add_argument("--preview", action="store_true", help="Save HTML only, do not send email")
    parser.add_argument("--days", type=int, default=None, help="Days of news/episodes to include (default: 7)")
    args = parser.parse_args()

    days_back = args.days if args.days is not None else DAYS_BACK

    print("Loading portfolio...")
    portfolio = load_portfolio()
    entities = collect_entities(portfolio)

    print(f"Fetching news for {len(entities)} entities (last {days_back} days)...")
    news_data = fetch_all_news(entities, days_back=days_back)

    podcasts = load_podcasts()
    podcast_data = fetch_all_podcasts(podcasts, days_back=days_back)

    print(f"Fetching prices and news for {len(STOCKS)} stocks...")
    stocks_data = fetch_all_stocks(max_news=MAX_ARTICLES, days_back=days_back)

    print("Fetching sports scores...")
    sports_data = fetch_sports()

    print("Building dashboard...")
    html = build_html(
        portfolio, news_data,
        podcast_data=podcast_data,
        stocks_data=stocks_data,
        sports_data=sports_data,
    )
    output_path = save_html(html)

    if args.preview:
        print(f"\nPreview mode — open in browser:\n  {output_path.resolve()}")
        return

    missing = check_email_config()
    if missing:
        print(
            f"\nEmail not configured (missing: {', '.join(missing)}).\n"
            f"Copy .env.example to .env and fill in your credentials.\n"
            f"Preview saved at: {output_path.resolve()}"
        )
        sys.exit(0)

    print("Sending email...")
    send_email(html)


if __name__ == "__main__":
    main()
