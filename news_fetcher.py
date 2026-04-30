"""
News fetching via NewsAPI.org (primary) with Google News RSS as fallback.

Sign up for a free API key at https://newsapi.org — the free tier allows
100 requests/day, more than enough for this portfolio.

Set NEWSAPI_KEY in your .env file to enable the primary source.
Without a key, the script falls back to Google News RSS (works on most
standard internet connections but may be rate-limited).
"""

import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

_SESSION = requests.Session()
_SESSION.headers.update(
    {"User-Agent": "Mozilla/5.0 (compatible; MyDailyDashboard/1.0)"}
)


def fetch_news(entity, max_items=3, days_back=7):
    """Fetch recent news articles for a portfolio entity."""
    if NEWSAPI_KEY:
        articles = _fetch_newsapi(entity, max_items, days_back)
    else:
        articles = _fetch_gnews_rss(entity, max_items, days_back)

    time.sleep(0.3)
    return articles


# ── NewsAPI ───────────────────────────────────────────────────────────────────

def _fetch_newsapi(entity, max_items, days_back):
    query = entity.get("search_query") or entity["name"]
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {
        "q": query,
        "from": from_date,
        "sortBy": "publishedAt",
        "pageSize": max_items,
        "language": "en",
        "apiKey": NEWSAPI_KEY,
    }
    try:
        resp = _SESSION.get("https://newsapi.org/v2/everything", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for item in data.get("articles", [])[:max_items]:
            pub_date = None
            if item.get("publishedAt"):
                try:
                    pub_date = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
                    pub_date = pub_date.replace(tzinfo=None)
                except Exception:
                    pass
            summary = _truncate(item.get("description") or "", 250)
            articles.append(
                {
                    "title": _clean_title(item.get("title") or ""),
                    "link": item.get("url") or "",
                    "source": (item.get("source") or {}).get("name", "Unknown"),
                    "date": pub_date.strftime("%b %d, %Y") if pub_date else "Recent",
                    "summary": summary,
                }
            )
        return articles
    except Exception as exc:
        print(f"  Warning: NewsAPI failed for {entity['name']}: {exc}")
        return _fetch_gnews_rss(entity, max_items, days_back)


# ── Google News RSS fallback ──────────────────────────────────────────────────

def _fetch_gnews_rss(entity, max_items, days_back):
    query = entity.get("search_query") or f'"{entity["name"]}"'
    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )
    try:
        resp = _SESSION.get(url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        cutoff = datetime.now() - timedelta(days=days_back)
        articles = []

        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_str = item.findtext("pubDate") or ""
            source_el = item.find("source")
            source = (
                source_el.text.strip()
                if source_el is not None and source_el.text
                else "Unknown"
            )

            pub_date = None
            if pub_str:
                try:
                    pub_date = parsedate_to_datetime(pub_str).replace(tzinfo=None)
                except Exception:
                    pass

            if pub_date and pub_date < cutoff:
                continue

            articles.append(
                {
                    "title": _clean_title(title),
                    "link": link,
                    "source": source,
                    "date": pub_date.strftime("%b %d, %Y") if pub_date else "Recent",
                }
            )

            if len(articles) >= max_items:
                break

        return articles

    except Exception as exc:
        print(f"  Warning: could not fetch news for {entity['name']}: {exc}")
        return []


def _truncate(text, length):
    if len(text) <= length:
        return text
    return text[:length - 1].rsplit(" ", 1)[0] + "…"


def _clean_title(title):
    return re.sub(r"\s+-\s+[^-]+$", "", title).strip()
