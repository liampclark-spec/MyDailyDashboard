"""
Stock prices via yfinance and earnings/news via NewsAPI.
"""

import os
import time
from datetime import datetime, timedelta

import requests
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; MyDailyDashboard/1.0)"})

# Display name and NewsAPI search terms per ticker
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
    results = []
    for stock in STOCKS:
        print(f"  {stock['ticker']}")
        data = _fetch_one(stock, max_news, days_back)
        results.append(data)
        time.sleep(0.3)
    return results


def _fetch_one(stock, max_news, days_back):
    price_info = _get_price(stock["ticker"])
    news = _get_news(stock["ticker"], stock["search"], max_news, days_back)
    return {**stock, **price_info, "news": news}


def _get_price(ticker_symbol):
    try:
        hist = yf.Ticker(ticker_symbol).history(period="2d")
        if len(hist) >= 2:
            prev_close = round(hist["Close"].iloc[-2], 2)
            last_close = round(hist["Close"].iloc[-1], 2)
            change     = round(last_close - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2)
        elif len(hist) == 1:
            last_close = round(hist["Close"].iloc[-1], 2)
            change, change_pct, prev_close = None, None, None
        else:
            return {"price": None, "prev_close": None, "change": None, "change_pct": None}

        return {
            "price":      last_close,
            "prev_close": prev_close,
            "change":     change,
            "change_pct": change_pct,
        }
    except Exception as exc:
        print(f"  Warning: price fetch failed for {ticker_symbol}: {exc}")
        return {"price": None, "prev_close": None, "change": None, "change_pct": None}


def _get_news(ticker_symbol, search_terms, max_news, days_back):
    if not NEWSAPI_KEY:
        return []

    # Bias toward earnings, results, and price-moving events
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
