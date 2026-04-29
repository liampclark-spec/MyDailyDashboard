# MyDailyDashboard

Daily investment portfolio digest — searches recent news for each fund manager and co-investment company, then emails a clean HTML report every morning.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Get a free NewsAPI key

Register at **https://newsapi.org** — the free tier gives 100 requests/day, which covers all 36 entities in the portfolio with headroom to spare.

### 3. Configure email

```bash
cp .env.example .env
```

Edit `.env` with:
- Your **NewsAPI key** from step 2
- Your **Gmail address** and a **Google App Password** (not your regular password)
  - Enable 2FA at myaccount.google.com
  - Generate an App Password at https://myaccount.google.com/apppasswords
  - Select "Mail" as the app

### 4. Preview before sending

```bash
python dashboard.py --preview
# Opens nothing automatically — open output/dashboard_YYYYMMDD_HHMM.html in your browser
```

### 5. Send the email

```bash
python dashboard.py
```

## Scheduling (daily at 7 AM weekdays)

```bash
# Open crontab
crontab -e

# Add this line (adjust the path)
0 7 * * 1-5 cd /path/to/MyDailyDashboard && python3 dashboard.py >> output/cron.log 2>&1
```

On macOS, launchd is an alternative to cron. On Windows, use Task Scheduler.

## Options

```bash
python dashboard.py --preview        # Build HTML only, do not email
python dashboard.py --days 14        # Include 14 days of news (default: 7)
```

## Updating Your Portfolio

Edit `portfolio.json`. Each fund manager and entity supports:

| Field | Description |
|-------|-------------|
| `name` | Display name (required) |
| `search_query` | Custom news search query — useful for abbreviations or combined names |
| `aka` | Former name, shown as "F.K.A." subtitle |
| `ticker` | Stock ticker shown in subtitle (e.g. Nubank = NU, Sportradar = SRAD) |

**Example — adding a new co-investment:**
```json
{ "name": "Acme Corp", "search_query": "\"Acme Corporation\" OR \"Acme Corp\"" }
```

## Files

| File | Purpose |
|------|---------|
| `dashboard.py` | Main entry point |
| `news_fetcher.py` | NewsAPI + Google News RSS fetching |
| `email_builder.py` | HTML email construction |
| `portfolio.json` | Your investment portfolio |
| `.env` | Your credentials (git-ignored) |
| `output/` | Saved HTML previews (git-ignored) |
