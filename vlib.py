"""Notion views API helpers (Notion-Version 2025-09-03) + daily refresh of time-horizon filters."""
import calendar, json, urllib.request, urllib.error
from datetime import date, timedelta
from lib import _token, save_ids


def v(method, path, body=None):
    req = urllib.request.Request("https://api.notion.com/v1" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + _token(), "Notion-Version": "2025-09-03", "Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code} {e.read().decode()[:400]}")


def rng(prop, a, b):
    return {"and": [{"property": prop, "date": {"on_or_after": a}}, {"property": prop, "date": {"on_or_before": b}}]}


def horizons(today):
    d = date.fromisoformat(today)
    mon = d - timedelta(days=d.weekday())
    return {"오늘": {"property": "Due", "date": {"equals": today}},
            "이번 주": rng("Due", mon.isoformat(), (mon + timedelta(days=6)).isoformat()),
            "이번 달": rng("Due", d.replace(day=1).isoformat(), d.replace(day=calendar.monthrange(d.year, d.month)[1]).isoformat()),
            "올해": rng("Due", f"{d.year}-01-01", f"{d.year}-12-31")}


def now_filter(first_open):
    """roadmap '지금' view: in-progress units + the next 5 open units by '#'."""
    return {"or": [{"property": "Status", "select": {"equals": "진행 중"}},
                   {"and": [{"property": "Status", "select": {"equals": "대기"}},
                            {"property": "#", "number": {"less_than_or_equal_to": first_open + 4}}]}]}


def refresh(I, today, first_open):
    for name, flt in horizons(today).items():
        vid = I.get(f"vid:tasks:{name}")
        if vid:
            v("PATCH", f"/views/{vid}", {"filter": flt})
    vid = I.get("vid:roadmap:지금")
    if vid:
        v("PATCH", f"/views/{vid}", {"filter": now_filter(first_open)})
