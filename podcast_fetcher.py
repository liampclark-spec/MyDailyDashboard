import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

_NS = {
    "atom":  "http://www.w3.org/2005/Atom",
    "yt":    "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def fetch_podcast_episodes(podcast, max_episodes=2, days_back=7):
    """Fetch recent episodes for a podcast entry."""
    name = podcast["name"]
    try:
        if podcast.get("youtube_url"):
            episodes = _from_youtube_channel(podcast["youtube_url"], max_episodes, days_back)
        elif podcast.get("youtube_playlist_id"):
            episodes = _from_youtube_playlist(podcast["youtube_playlist_id"], max_episodes, days_back)
        elif podcast.get("search_query"):
            episodes = _from_news_search(podcast["search_query"], max_episodes, days_back)
        elif podcast.get("rss"):
            episodes = _from_rss(podcast["rss"], max_episodes, days_back)
        else:
            episodes = []
    except Exception as exc:
        print(f"  Warning: unexpected error for {name}: {exc}")
        episodes = []

    time.sleep(0.3)
    return episodes


# ── YouTube channel ───────────────────────────────────────────────────────────

def _from_youtube_channel(url, max_episodes, days_back):
    channel_id = _resolve_channel_id(url)
    if not channel_id:
        print(f"  Warning: could not resolve channel ID for {url}")
        return []
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    return _parse_youtube_feed(feed_url, max_episodes, days_back)


def _resolve_channel_id(url):
    """Fetch a YouTube page and extract the UC... channel ID."""
    try:
        resp = _SESSION.get(url, timeout=12)
        resp.raise_for_status()
        # Channel ID appears multiple times in the page as "channelId":"UCxxxxxx"
        match = re.search(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', resp.text)
        if match:
            return match.group(1)
        # Fallback: canonical link href
        match = re.search(
            r'href="https://www\.youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})"',
            resp.text,
        )
        return match.group(1) if match else None
    except Exception as exc:
        print(f"  Warning: could not resolve channel ID for {url}: {exc}")
        return None


# ── YouTube playlist ──────────────────────────────────────────────────────────

def _from_youtube_playlist(playlist_id, max_episodes, days_back):
    feed_url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
    return _parse_youtube_feed(feed_url, max_episodes, days_back)


# ── YouTube Atom feed parser (shared by channel + playlist) ──────────────────

def _parse_youtube_feed(feed_url, max_episodes, days_back):
    try:
        resp = _SESSION.get(feed_url, timeout=12)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as exc:
        print(f"  Warning: could not fetch {feed_url}: {exc}")
        return []

    cutoff = datetime.now() - timedelta(days=days_back)
    episodes = []

    for entry in root.findall("atom:entry", _NS):
        title = (entry.findtext("atom:title", "", _NS) or "").strip()

        link_el = entry.find("atom:link[@rel='alternate']", _NS)
        link = link_el.get("href", "") if link_el is not None else ""
        if not link:
            video_id = entry.findtext("yt:videoId", "", _NS)
            if video_id:
                link = f"https://www.youtube.com/watch?v={video_id}"

        pub_str = entry.findtext("atom:published", "", _NS) or ""
        pub_date = None
        if pub_str:
            try:
                pub_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass

        # Always include at least one episode; filter older ones once we have one
        if pub_date and pub_date < cutoff and episodes:
            continue

        description = ""
        media_group = entry.find("media:group", _NS)
        if media_group is not None:
            description = (media_group.findtext("media:description", "", _NS) or "").strip()
        description = _truncate(description, 250)

        episodes.append({
            "title": title,
            "link": link,
            "date": pub_date.strftime("%b %d, %Y") if pub_date else "Recent",
            "duration": "",
            "summary": description,
        })

        if len(episodes) >= max_episodes:
            break

    return episodes


# ── NewsAPI search (for non-podcast items e.g. Eye on the Market) ────────────

def _from_news_search(query, max_items, days_back):
    if not NEWSAPI_KEY:
        return []
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
        items = []
        for article in resp.json().get("articles", [])[:max_items]:
            pub_date = None
            if article.get("publishedAt"):
                try:
                    pub_date = datetime.fromisoformat(
                        article["publishedAt"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                except Exception:
                    pass
            items.append({
                "title": _clean_title(article.get("title") or ""),
                "link": article.get("url") or "",
                "date": pub_date.strftime("%b %d, %Y") if pub_date else "Recent",
                "duration": "",
                "summary": _truncate(article.get("description") or "", 250),
            })
        return items
    except Exception as exc:
        print(f"  Warning: news search failed for '{query}': {exc}")
        return []


# ── Generic RSS fallback ──────────────────────────────────────────────────────

def _from_rss(rss_url, max_episodes, days_back):
    from email.utils import parsedate_to_datetime
    _ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
    try:
        resp = _SESSION.get(rss_url, timeout=12)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        cutoff = datetime.now() - timedelta(days=days_back)
        episodes = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if not link:
                enc = item.find("enclosure")
                if enc is not None:
                    link = enc.get("url", "")
            pub_str = item.findtext("pubDate") or ""
            pub_date = None
            if pub_str:
                try:
                    pub_date = parsedate_to_datetime(pub_str).replace(tzinfo=None)
                except Exception:
                    pass
            if pub_date and pub_date < cutoff and episodes:
                continue
            summary = (
                item.findtext(f"{{{_ITUNES}}}summary")
                or item.findtext("description")
                or ""
            )
            episodes.append({
                "title": _clean_title(title),
                "link": link,
                "date": pub_date.strftime("%b %d, %Y") if pub_date else "Recent",
                "duration": "",
                "summary": _truncate(_strip_html(summary), 250),
            })
            if len(episodes) >= max_episodes:
                break
        return episodes
    except Exception as exc:
        print(f"  Warning: RSS fetch failed for {rss_url}: {exc}")
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _truncate(text, length):
    if len(text) <= length:
        return text
    return text[:length - 1].rsplit(" ", 1)[0] + "…"


def _strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_title(title):
    return re.sub(r"\s+-\s+[^-]+$", "", title).strip()
