import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import requests

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; MyDailyDashboard/1.0)"})

# iTunes namespace used by most podcast RSS feeds
_ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"


def fetch_podcast_episodes(podcast, max_episodes=2, days_back=7):
    """Return the most recent episodes from a podcast RSS feed."""
    try:
        resp = _SESSION.get(podcast["rss"], timeout=12)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        cutoff = datetime.now() - timedelta(days=days_back)
        episodes = []

        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()

            # Some feeds use <enclosure> for the audio URL
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

            # For "days_back" filter: if we have a date and it's too old, skip.
            # But always include at least the most recent episode regardless of age.
            if pub_date and pub_date < cutoff and episodes:
                continue

            # Description: prefer itunes:summary, fall back to <description>
            summary = (
                item.findtext(f"{{{_ITUNES}}}summary")
                or item.findtext("description")
                or ""
            )
            summary = _strip_html(summary).strip()
            if len(summary) > 220:
                summary = summary[:217].rsplit(" ", 1)[0] + "…"

            duration = item.findtext(f"{{{_ITUNES}}}duration") or ""

            episodes.append(
                {
                    "title": title,
                    "link": link,
                    "date": pub_date.strftime("%b %d, %Y") if pub_date else "Recent",
                    "summary": summary,
                    "duration": _fmt_duration(duration),
                }
            )

            if len(episodes) >= max_episodes:
                break

        time.sleep(0.3)
        return episodes

    except Exception as exc:
        print(f"  Warning: could not fetch {podcast['name']}: {exc}")
        return []


def _strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fmt_duration(raw):
    """Convert HH:MM:SS or seconds int to a readable string."""
    if not raw:
        return ""
    raw = str(raw).strip()
    if ":" in raw:
        parts = raw.split(":")
        if len(parts) == 3:
            h, m, _ = parts
            return f"{int(h)}h {int(m)}m" if int(h) else f"{int(m)}m"
        if len(parts) == 2:
            return f"{int(parts[0])}m"
    try:
        secs = int(raw)
        h, remainder = divmod(secs, 3600)
        m = remainder // 60
        return f"{h}h {m}m" if h else f"{m}m"
    except ValueError:
        return ""
