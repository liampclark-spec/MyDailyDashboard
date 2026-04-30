from datetime import datetime


def build_html(portfolio, news_data, podcast_data=None, stocks_data=None, sports_data=None):
    today = datetime.now().strftime("%A, %B %d, %Y")

    total_managers = sum(len(v) for v in portfolio["funds"].values())
    total_co = len(portfolio["co_investments"])
    total_non_core = sum(len(v) for v in portfolio["non_core_holdings"].values())

    sections = []

    # --- Fund Managers ---
    fund_content = ""
    for category, managers in portfolio["funds"].items():
        fund_content += _category_header(category)
        for mgr in managers:
            fund_content += _entity_card(mgr["name"], news_data.get(mgr["name"], []))
    sections.append(_section("Fund Managers", fund_content, bg="#ffffff"))

    # --- Co-Investments ---
    co_content = ""
    for inv in portfolio["co_investments"]:
        name = inv["name"]
        meta_parts = []
        if inv.get("aka"):
            meta_parts.append(f"F.K.A. {inv['aka']}")
        if inv.get("ticker"):
            meta_parts.append(inv["ticker"])
        subtitle = " &nbsp;·&nbsp; ".join(meta_parts) if meta_parts else None
        co_content += _entity_card(name, news_data.get(name, []), subtitle=subtitle)
    sections.append(_section("Co-Investments", co_content, bg="#f8fafc"))

    # --- Non-Core Holdings ---
    has_nc = any(v for v in portfolio["non_core_holdings"].values())
    if has_nc:
        nc_content = ""
        for bucket, entities in portfolio["non_core_holdings"].items():
            if not entities:
                continue
            nc_content += _category_header(bucket)
            for ent in entities:
                nc_content += _entity_card(ent["name"], news_data.get(ent["name"], []))
        sections.append(_section("Non-Core Holdings", nc_content, bg="#ffffff"))

    # --- Stocks ---
    if stocks_data:
        sections.append(_stocks_section(stocks_data))

    # --- Sports ---
    if sports_data:
        sections.append(_sports_section(sports_data))

    # --- Podcasts ---
    if podcast_data:
        sections.append(_podcast_section(podcast_data))

    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Investment Dashboard – {today}</title>
</head>
<body style="margin:0;padding:0;background:#eef1f6;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#eef1f6;padding:24px 0;">
<tr><td align="center">
<table width="680" cellpadding="0" cellspacing="0" style="max-width:680px;width:100%;">

  {_header(today, total_managers, total_co, total_non_core)}
  {body}
  {_footer()}

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Podcast section ───────────────────────────────────────────────────────────

def _podcast_section(podcast_data):
    content = ""
    for pod in podcast_data:
        content += _podcast_card(pod)
    return _section("Podcasts &amp; Media", content, bg="#ffffff")


def _podcast_card(pod):
    name = pod["name"]
    episodes = pod.get("episodes", [])
    note = pod.get("note")

    header = f'<div style="font-size:14px;font-weight:600;color:#0f2044;">{name}</div>'
    if note:
        header += f'<div style="font-size:11px;color:#94a3b8;margin-top:2px;">{note}</div>'

    if episodes:
        eps_html = ""
        for ep in episodes:
            duration_str = f" &nbsp;·&nbsp; {ep['duration']}" if ep.get("duration") else ""
            summary_str = ""
            if ep.get("summary"):
                summary_str = (
                    f'<div style="margin-top:4px;font-size:12px;color:#64748b;line-height:1.5;">'
                    f'{ep["summary"]}</div>'
                )
            eps_html += f"""
      <div style="margin-top:8px;padding:8px 12px;background:#f0fdf4;
                  border-left:3px solid #16a34a;border-radius:0 4px 4px 0;">
        <a href="{ep['link']}" style="font-size:13px;color:#15803d;text-decoration:none;
                                      font-weight:500;line-height:1.45;">{ep['title']}</a>
        <div style="margin-top:2px;font-size:11px;color:#94a3b8;">
          {ep['date']}{duration_str}
        </div>
        {summary_str}
      </div>"""
    else:
        eps_html = (
            '<div style="margin-top:6px;font-size:12px;color:#cbd5e1;font-style:italic;">'
            "No recent episodes found</div>"
        )

    return f"""
    <div style="margin-bottom:14px;padding:14px 16px;border:1px solid #e2e8f0;
                border-radius:7px;background:#ffffff;">
      {header}
      {eps_html}
    </div>"""


# ── Investment news section helpers ──────────────────────────────────────────

def _header(today, total_managers, total_co, total_non_core):
    return f"""
  <tr><td style="background:#0f2044;padding:32px 36px;border-radius:10px 10px 0 0;">
    <div style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:-0.2px;">
      Daily Investment Dashboard
    </div>
    <div style="color:#7fa3d8;font-size:13px;margin-top:6px;">{today}</div>
    <table cellpadding="0" cellspacing="0" style="margin-top:20px;">
      <tr>
        {_stat_pill(total_managers, "Fund Managers")}
        {_stat_pill(total_co, "Co-Investments")}
        {_stat_pill(total_non_core, "Non-Core Holdings")}
      </tr>
    </table>
  </td></tr>"""


def _stat_pill(count, label):
    return f"""
        <td style="padding-right:12px;">
          <table cellpadding="0" cellspacing="0">
            <tr>
              <td style="background:#1d3461;border-radius:20px;padding:5px 14px;">
                <span style="color:#ffffff;font-size:14px;font-weight:600;">{count}</span>
                <span style="color:#7fa3d8;font-size:12px;margin-left:5px;">{label}</span>
              </td>
            </tr>
          </table>
        </td>"""


def _section(title, content, bg="#ffffff"):
    return f"""
  <tr><td style="background:{bg};padding:28px 36px;">
    <div style="font-size:17px;font-weight:700;color:#0f2044;padding-bottom:12px;
                border-bottom:2px solid #e2e8f0;margin-bottom:20px;">{title}</div>
    {content}
  </td></tr>"""


def _category_header(label):
    return f"""
    <div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;
                letter-spacing:1px;margin:20px 0 10px;">{label}</div>"""


def _entity_card(name, articles, subtitle=None):
    header = f'<div style="font-size:14px;font-weight:600;color:#0f2044;">{name}</div>'
    if subtitle:
        header += f'<div style="font-size:11px;color:#94a3b8;margin-top:2px;">{subtitle}</div>'

    if articles:
        news_html = ""
        for a in articles:
            summary_html = ""
            if a.get("summary"):
                summary_html = (
                    f'<div style="margin-top:4px;font-size:12px;color:#475569;line-height:1.5;">'
                    f'{a["summary"]}</div>'
                )
            news_html += f"""
      <div style="margin-top:8px;padding:8px 12px;background:#f1f5fb;
                  border-left:3px solid #2563eb;border-radius:0 4px 4px 0;">
        <a href="{a['link']}" style="font-size:13px;color:#1d4ed8;text-decoration:none;
                                     font-weight:500;line-height:1.45;">{a['title']}</a>
        <div style="margin-top:2px;font-size:11px;color:#94a3b8;">
          {a['source']} &nbsp;·&nbsp; {a['date']}
        </div>
        {summary_html}
      </div>"""
    else:
        news_html = (
            '<div style="margin-top:6px;font-size:12px;color:#cbd5e1;font-style:italic;">'
            "No recent news found</div>"
        )

    return f"""
    <div style="margin-bottom:14px;padding:14px 16px;border:1px solid #e2e8f0;
                border-radius:7px;background:#ffffff;">
      {header}
      {news_html}
    </div>"""


def _footer():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    return f"""
  <tr><td style="background:#0f2044;padding:16px 36px;border-radius:0 0 10px 10px;text-align:center;">
    <div style="color:#4a6fa5;font-size:11px;">Generated {ts} &nbsp;·&nbsp; MyDailyDashboard</div>
  </td></tr>"""


# ── Stocks section ────────────────────────────────────────────────────────────

def _stocks_section(stocks_data):
    content = ""
    for stock in stocks_data:
        content += _stock_card(stock)
    return _section("My Stocks", content, bg="#f8fafc")


def _stock_card(stock):
    ticker  = stock["ticker"]
    name    = stock["name"]
    price   = stock.get("price")
    chg     = stock.get("change")
    chg_pct = stock.get("change_pct")
    news    = stock.get("news", [])

    # Price pill
    if price is not None and chg_pct is not None:
        up = chg_pct >= 0
        arrow    = "▲" if up else "▼"
        clr      = "#16a34a" if up else "#dc2626"
        bg_clr   = "#f0fdf4" if up else "#fef2f2"
        price_pill = (
            f'<span style="background:{bg_clr};color:{clr};font-size:12px;font-weight:600;'
            f'padding:2px 8px;border-radius:12px;white-space:nowrap;">'
            f'${price:,.2f} &nbsp;{arrow} {abs(chg_pct):.2f}%</span>'
        )
    else:
        price_pill = '<span style="font-size:12px;color:#94a3b8;">Price unavailable</span>'

    header = f"""
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
        <div>
          <span style="font-size:14px;font-weight:700;color:#0f2044;">{ticker}</span>
          <span style="font-size:12px;color:#64748b;margin-left:6px;">{name}</span>
        </div>
        {price_pill}
      </div>"""

    news_html = ""
    for a in news:
        summary_html = (
            f'<div style="margin-top:3px;font-size:12px;color:#475569;line-height:1.5;">{a["summary"]}</div>'
            if a.get("summary") else ""
        )
        news_html += f"""
      <div style="margin-top:8px;padding:8px 12px;background:#f1f5fb;
                  border-left:3px solid #7c3aed;border-radius:0 4px 4px 0;">
        <a href="{a['link']}" style="font-size:13px;color:#6d28d9;text-decoration:none;
                                     font-weight:500;line-height:1.45;">{a['title']}</a>
        <div style="margin-top:2px;font-size:11px;color:#94a3b8;">
          {a['source']} &nbsp;·&nbsp; {a['date']}
        </div>
        {summary_html}
      </div>"""

    if not news_html:
        news_html = '<div style="margin-top:6px;font-size:12px;color:#cbd5e1;font-style:italic;">No recent earnings or news found</div>'

    return f"""
    <div style="margin-bottom:14px;padding:14px 16px;border:1px solid #e2e8f0;
                border-radius:7px;background:#ffffff;">
      {header}
      {news_html}
    </div>"""


# ── Sports section ────────────────────────────────────────────────────────────

def _sports_section(sports_data):
    yesterday = (
        __import__("datetime").datetime.now() -
        __import__("datetime").timedelta(days=1)
    ).strftime("%A, %B %d")

    content = f'<div style="font-size:12px;color:#64748b;margin-bottom:16px;">Results for {yesterday}</div>'

    for sport_name, games in sports_data.items():
        if not games:
            continue
        content += _category_header(sport_name)
        for game in games:
            content += _game_card(game)

    return _section("Sports", content, bg="#ffffff")


def _game_card(game):
    home, away   = game["home"], game["away"]
    hs, as_      = game["home_score"], game["away_score"]
    status       = game["status"]
    favourite    = game.get("favourite")
    headline     = game.get("headline", "")
    leaders      = game.get("leaders", [])

    # Determine winner highlight
    try:
        h_int, a_int = int(hs), int(as_)
        home_bold = "font-weight:700;" if h_int > a_int else ""
        away_bold = "font-weight:700;" if a_int > h_int else ""
    except (ValueError, TypeError):
        home_bold = away_bold = ""

    fav_badge = ""
    if favourite:
        fav_badge = (
            f'<span style="background:#fef3c7;color:#b45309;font-size:10px;font-weight:700;'
            f'padding:1px 7px;border-radius:10px;margin-left:8px;">★ {favourite}</span>'
        )

    score_line = f"""
      <div style="font-size:13px;color:#1e293b;padding:6px 0;">
        <span style="{away_bold}">{away}</span>
        <span style="color:#94a3b8;margin:0 6px;">vs</span>
        <span style="{home_bold}">{home}</span>
        <span style="color:#64748b;margin-left:10px;font-size:12px;">{away} {as_} – {hs} {home}</span>
        <span style="color:#94a3b8;font-size:11px;margin-left:8px;">{status}</span>
        {fav_badge}
      </div>"""

    if headline:
        score_line += (
            f'<div style="font-size:12px;color:#475569;padding:2px 0 4px;font-style:italic;">'
            f'{headline}</div>'
        )

    # Box score leaders for favourite team games
    leaders_html = ""
    if leaders:
        rows = "".join(
            f'<span style="margin-right:14px;white-space:nowrap;">'
            f'<span style="color:#94a3b8;font-size:10px;">{l["category"].upper()}</span> '
            f'<span style="font-size:12px;font-weight:600;color:#1e293b;">{l["player"]}</span> '
            f'<span style="font-size:12px;color:#64748b;">{l["value"]}</span>'
            f'</span>'
            for l in leaders
        )
        leaders_html = (
            f'<div style="background:#f8fafc;padding:6px 10px;border-radius:4px;'
            f'margin-top:4px;flex-wrap:wrap;display:flex;">{rows}</div>'
        )

    border = "border-left:3px solid #f59e0b;" if favourite else "border-left:3px solid #e2e8f0;"

    return f"""
    <div style="margin-bottom:10px;padding:10px 14px;border:1px solid #e2e8f0;{border}
                border-radius:7px;background:#ffffff;">
      {score_line}
      {leaders_html}
    </div>"""
