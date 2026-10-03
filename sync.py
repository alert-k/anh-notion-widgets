"""Notion -> docs/data.json (widgets) ; ensure today's Daily journal ; GitHub commit count -> Journal.
Run locally or from GitHub Actions (env NOTION, optional GH_USER, DB ids from ids.json or IDS_JSON env)."""
import json, os, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone
from collections import Counter
from lib import api, ids, query_all, rt, title_of, ROOT

if os.environ.get("IDS_JSON"):
    I = json.loads(os.environ["IDS_JSON"])
else:
    I = ids()
KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
today = now.date().isoformat()
GH_USER = os.environ.get("GH_USER", "alert-k")


def prop(pg, name):
    v = pg["properties"].get(name, {})
    t = v.get("type")
    x = v.get(t)
    if t == "select": return x and x["name"]
    if t == "date": return x and x["start"]
    if t == "formula": return x and x.get(x["type"])
    if t == "rollup": return x and x.get(x["type"])
    if t in ("rich_text", "title"): return "".join(i["plain_text"] for i in x)
    return x


# ---- 1. today's Daily journal (template body) ----
dj = query_all(I["journal"], {"and": [{"property": "Type", "select": {"equals": "Daily"}},
                                      {"property": "Date", "date": {"equals": today}}]})
if not dj:
    H = lambda t: {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rt(t)}}
    P = lambda: {"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}
    dj = [api("POST", "/pages", {"parent": {"database_id": I["journal"]}, "properties": {
        "Title": {"title": rt(f"{today} Daily")}, "Type": {"select": {"name": "Daily"}},
        "Date": {"date": {"start": today}}},
        "children": [H("🌟 오늘의 Highlight"), P(), H("🙏 감사 3가지"), P(), H("📚 배운 것"), P(),
                     H("🧠 오늘의 생각"), P(), H("🔁 내일 할 일 (Top 3)"), P()]})]

# ---- 2. GitHub commits today (public search; ceiling: private repos not counted) ----
try:
    q = urllib.parse.quote(f"author:{GH_USER} author-date:{today}")
    req = urllib.request.Request(f"https://api.github.com/search/commits?q={q}&per_page=1",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "anh-sync"})
    n = json.load(urllib.request.urlopen(req, timeout=30))["total_count"]
    api("PATCH", f"/pages/{dj[0]['id']}", {"properties": {"GitHub 커밋": {"number": n}}})
except Exception as e:  # never block sync on GitHub
    print("github skipped:", e)

# ---- 3. data.json ----
out = {"updated": now.isoformat(timespec="minutes"), "today": today}

rm = query_all(I["roadmap"])
ph = {}
for r in rm:
    k = prop(r, "Phase") or "?"
    d = ph.setdefault(k, {"total": 0, "done": 0, "est": 0, "min": 0})
    d["total"] += 1; d["done"] += prop(r, "Status") == "완료"
    d["est"] += prop(r, "Est hours") or 0; d["min"] += prop(r, "누적(분)") or 0
out["roadmap"] = [{"phase": k, **v} for k, v in sorted(ph.items())]

# titles of private-ish areas (취업) are never exported
tasks = query_all(I["tasks"], {"property": "Done", "checkbox": {"equals": False}})
out["tasks"] = [{"t": title_of(t), "due": prop(t, "Due"), "area": prop(t, "Area"), "q": prop(t, "Quadrant")}
                for t in tasks if prop(t, "Area") != "취업" and prop(t, "Due")]
out["tasks_open"] = len(tasks)

jr = query_all(I["journal"], {"property": "Type", "select": {"equals": "Daily"}})
score = {prop(j, "Date"): prop(j, "루틴 점수(%)") or 0 for j in jr if prop(j, "Date")}
streak, d = 0, now.date()
if score.get(d.isoformat(), 0) < 50:  # today still in progress -> start from yesterday
    d -= timedelta(days=1)
while score.get(d.isoformat(), 0) >= 50:
    streak += 1; d -= timedelta(days=1)
out["streak"] = streak
out["today_score"] = score.get(today, 0)
out["month_days_ok"] = sum(1 for k, v in score.items() if k[:7] == today[:7] and v >= 50)

wk = (now.date() - timedelta(days=6)).isoformat()
ss = query_all(I["sessions"], {"property": "Date", "date": {"on_or_after": wk}})
out["study_week_min"] = sum(prop(s, "Minutes") or 0 for s in ss)

apps = Counter(prop(a, "Status") for a in query_all(I["apps"]))
out["apps"] = dict(apps)  # counts only, no company names

os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "docs", "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("synced", today, "streak", streak, "tasks", len(out["tasks"]))
