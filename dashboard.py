#!/usr/bin/env python3
"""Daily investment portfolio dashboard — fetches news and emails a digest."""

import argparse
import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

from email_builder import build_html
from news_fetcher import fetch_news

load_dotenv()

ROOT = Path(__file__).parent
PORTFOLIO_FILE = ROOT / "portfolio.json"
OUTPUT_DIR = ROOT / "output"

EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
DAYS_BACK = int(os.getenv("DAYS_BACK", "7"))
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "3"))


def load_portfolio():
    with open(PORTFOLIO_FILE) as f:
        return json.load(f)


def collect_entities(portfolio):
    """Return a flat list of all entity dicts in display order."""
    entities = []
    for managers in portfolio["funds"].values():
        entities.extend(managers)
    entities.extend(portfolio["co_investments"])
    for bucket in portfolio["non_core_holdings"].values():
        entities.extend(bucket)
    return entities


def fetch_all_news(entities, days_back=DAYS_BACK):
    news_data = {}
    total = len(entities)
    for i, entity in enumerate(entities, 1):
        name = entity["name"]
        print(f"  [{i}/{total}] {name}")
        news_data[name] = fetch_news(entity, max_items=MAX_ARTICLES, days_back=days_back)
    return news_data


def send_email(html_content):
    subject = f"Investment Dashboard – {datetime.now().strftime('%B %d, %Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, [a.strip() for a in EMAIL_TO.split(",")], msg.as_string())

    print(f"Email sent to {EMAIL_TO}")


def save_html(html_content):
    OUTPUT_DIR.mkdir(exist_ok=True)
    filename = OUTPUT_DIR / f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    filename.write_text(html_content, encoding="utf-8")
    print(f"Dashboard saved: {filename}")
    return filename


def check_email_config():
    missing = [k for k in ("EMAIL_FROM", "EMAIL_TO", "SMTP_USER", "SMTP_PASS") if not os.getenv(k)]
    return missing


def main():
    parser = argparse.ArgumentParser(description="MyDailyDashboard — investment email digest")
    parser.add_argument("--preview", action="store_true", help="Save HTML only, do not send email")
    parser.add_argument("--days", type=int, default=None, help="Days of news to include (default: 7)")
    args = parser.parse_args()

    days_back = args.days if args.days is not None else DAYS_BACK

    print("Loading portfolio...")
    portfolio = load_portfolio()
    entities = collect_entities(portfolio)
    print(f"Fetching news for {len(entities)} entities (last {days_back} days)...")

    news_data = fetch_all_news(entities, days_back=days_back)

    print("Building dashboard...")
    html = build_html(portfolio, news_data)
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
