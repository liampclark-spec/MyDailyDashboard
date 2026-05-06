"""
Stock prices via Twelve Data API (free tier: 800 calls/day).
One batch request covers all 13 tickers.
Sign up for a free key at https://twelvedata.com
"""

import os
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY      = os.getenv("NEWSAPI_KEY", "")
TWELVE_DATA_KEY  = os.getenv("TWELVE_DATA_KEY", "")

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; MyDailyDashboard/1.0)"})

STOCKS = [
    {"ticker": "GOOGL", "name": "Google / Alphabet",       "search": "Alphabet OR Google GOOGL"},
    {"ticker": "KKR",   "name": "KKR",                     "search": "KKR"},
    {"ticker": "COIN",  "name": "Coinbase",                 "search": "Coinbase COIN"},
    {"ticker": "TMO",   "name": "Thermo Fisher Scientific", "search": "\"Thermo Fisher\" TMO"},
    {"ticker": "RY",    "name": "Royal Bank of Canada",     "search": "\"Royal Bank of Canada\" OR RBC"},
    {"ticker": "BXP",   "name": "BXP (Boston Properties)",  "search": "BXP OR \"Boston Properties\""},
    {"ticker": "PDD",   "name": "PDD Holdings (Temu)",      "search": "PDD Holdings OR Temu OR Pinduoduo"},
    {"ticker": "TFC",   "name": "Truist Financial",         "search": "\"Truist Financial\" OR TFC"},
    {"ticker": "MPLX",  "name": "MPLX",                     "search": "MPLX"},
    {"ticker": "MGNI",  "name": "Magnite",                  "search": "Magnite MGNI"},
    {"ticker": "SPOT",  "name": "Spotify",                  "search": "Spotify SPOT"},
    {"ticker": "CRWD",  "name": "CrowdStrike",              "search": "CrowdStrike CRWD"},
    {"ticker": "CRM",   "name": "Salesforce",               "search": "Salesforce CRM"},
]


def fetch_all_stocks(max_news=3, days_back=7):
    print("  Fetching prices (Twelve Data)...")
    price_map = _batch_prices()

    results = []
    for stock in STOCKS:
        print(f"  {stock['ticker']}")
        price_info = price_map.get(
            stock["ticker"],
            {"price": None, "prev_close": None, "change": None, "change_pct": None},
        )
        news = _get_news(stock["ticker"], stock["search"], max_news, days_back)
        results.append({**stock, **price_info, "news": news})
        time.sleep(0.15)
    return results


def _batch_prices():
    """Fetch quotes for all tickers in one Twelve Data API call."""
    if not TWELVE_DATA_KEY:
        print("  Warning: TWELVE_DATA_KEY not set — skipping prices")
        return {}

    symbols = ",".join(s["ticker"] for s in STOCKS)
    try:
        resp = _SESSION.get(
            "https://api.twelvedata.com/quote",
            params={"symbol": symbols, "apikey": TWELVE_DATA_KEY, "dp": "2"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        price_map = {}
        # Single ticker returns the object directly; multiple returns {TICKER: {...}, ...}
        if "symbol" in data:
            data = {data["symbol"]: data}

        for ticker, quote in data.items():
            try:
                price      = float(quote["close"])
                prev_close = float(quote["previous_close"])
                change     = round(price - prev_close, 2)
                change_pct = round((change / prev_close) * 100, 2)
                price_map[ticker] = {
                    "price":      round(price, 2),
                    "prev_close": round(prev_close, 2),
                    "change":     change,
                    "change_pct": change_pct,
                }
            except (KeyError, TypeError, ValueError):
                price_map[ticker] = {"price": None, "prev_close": None, "change": None, "change_pct": None}

        return price_map

    except Exception as exc:
        print(f"  Warning: price fetch failed: {exc}")
        return {}


def _get_news(ticker_symbol, search_terms, max_news, days_back):
    if not NEWSAPI_KEY:
        return []

    query = f"({search_terms}) AND (earnings OR revenue OR results OR forecast OR acquisition OR guidance)"
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {
        "q":        query,
        "from":     from_date,
        "sortBy":   "relevancy",
        "pageSize": max_news,
        "language": "en",
        "apiKey":   NEWSAPI_KEY,
    }
    try:
        resp = _SESSION.get("https://newsapi.org/v2/everything", params=params, timeout=10)
        resp.raise_for_status()
        articles = []
        for item in resp.json().get("articles", [])[:max_news]:
            pub_date = None
            if item.get("publishedAt"):
                try:
                    pub_date = datetime.fromisoformat(
                        item["publishedAt"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except Exception:
                    pass
            articles.append({
                "title":   item.get("title") or "",
                "link":    item.get("url") or "",
                "source":  (item.get("source") or {}).get("name", ""),
                "date":    pub_date.strftime("%b %d, %Y") if pub_date else "Recent",
                "summary": _truncate(item.get("description") or "", 220),
            })
        return articles
    except Exception as exc:
        print(f"  Warning: news fetch failed for {ticker_symbol}: {exc}")
        return []


def _truncate(text, length):
    if len(text) <= length:
        return text
    return text[:length - 1].rsplit(" ", 1)[0] + "…"
