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
        "children": [H("🧙 오늘의 여행 일기 — Highlight"), P(), H("🙏 감사 3가지"), P(), H("📚 배운 것"), P(),
                     H("🧠 오늘의 생각"), P(), H("🔁 내일 할 일 (Top 3)"), P()]})]

n = 0
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


# ---- 4. Home report callouts (private Notion only; public data.json stays minimal) ----
def get(url, token=None):
    h = {"User-Agent": "anh-sync"}
    if token:
        h["Authorization"] = "Bearer " + token
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30))


bar = lambda v, w=10: "▓" * round(w * min(v, 100) / 100) + "░" * (w - round(w * min(v, 100) / 100))
lab = {}
try:
    cats = get("https://lab.horyz.io/api/categories")["categories"]
    lab["challenges"] = sum(c.get("challenge_count", 0) for c in cats)
    lab["cats"] = len(cats)
    lab["board"] = len(get("https://lab.horyz.io/api/leaderboard")["leaderboard"])
    if os.environ.get("LAB_TOKEN"):  # ponytail: auth scheme unverified (Bearer assumed); failure just skips
        lab["progress"] = get("https://lab.horyz.io/api/roadmap/progress", os.environ["LAB_TOKEN"])
except Exception as e:
    print("lab skipped:", e)

QO = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3}
alltasks = sorted(tasks, key=lambda t: (QO.get((prop(t, "Quadrant") or "Q9")[:2], 9), prop(t, "Due") or "9999"))
tot = sum(p["total"] for p in out["roadmap"])
dn = sum(p["done"] for p in out["roadmap"])
est = sum(p["est"] for p in out["roadmap"])
mins = sum(p["min"] for p in out["roadmap"])
todo = sorted((r for r in rm if prop(r, "Status") != "완료"), key=lambda r: prop(r, "#") or 0)
doing = [title_of(r) for r in rm if prop(r, "Status") == "진행 중"][:3]
pins = [title_of(m) for m in query_all(I["inbox"], {"and": [
    {"property": "Pin", "checkbox": {"equals": True}},
    {"property": "Status", "select": {"does_not_equal": "완료"}}]})][:6]
wheel = sorted(query_all(I["wheel"]), key=lambda w: prop(w, "Score (1-10)") or 0)
apps_p = query_all(I["apps"])
dl = sorted((prop(a, "Deadline"), title_of(a)) for a in apps_p if prop(a, "Deadline") and prop(a, "Deadline") >= today)[:3]
pct_t = round(dn / tot * 100) if tot else 0
NL = "\n"
toss_mid = (f"진행 중: {', '.join(doing)}" if doing else "아직 시작 전 — 첫 유닛: " + (title_of(todo[0]) if todo else "-"))
R = {
    "daily": f"📅 {today}{NL}루틴 {bar(out['today_score'])} {out['today_score']}% · 🔥 연속 {streak}일{NL}"
             f"공부(7일) {out['study_week_min'] / 60:.1f}h · 오늘 커밋 {n}{NL}열린 Task {len(tasks)}개",
    "pins": "📌 고정 메모" + NL + (NL.join("• " + x for x in pins) or "없음 — Inbox에서 Pin 체크"),
    "toss": f"🗺️ TOSS 여정 {'⭐' * (pct_t // 25) or '☆'} {pct_t}% ({dn}/{tot}){NL}"
            f"학습 {mins / 60:.0f}h / 목록 합계 {est:.0f}h{NL}{toss_mid}{NL}일정·주간 시간은 lab.horyz.io 기준",
    "lab": "🧪 lab.horyz.io" + NL
           + (f"챌린지 {lab['challenges']}개 · 카테고리 {lab['cats']} · 리더보드 {lab['board']}명" if "challenges" in lab else "(연결 실패)")
           + (f"{NL}진행도 연동됨" if lab.get("progress") else f"{NL}진행도 연동: LAB_TOKEN 시크릿 필요"),
    "tasks": f"✅ 할 일 {len(tasks)}개{NL}" + NL.join(
        f"• {title_of(t)}" + (f"  ~{prop(t, 'Due')[5:]}" if prop(t, "Due") else "") + f"  {(prop(t, 'Quadrant') or '')[:2]}"
        for t in alltasks[:8]),
    "apps": "📮 지원 현황" + NL + (" · ".join(f"{k} {v}" for k, v in Counter(prop(a, "Status") for a in apps_p).items()) or "-")
            + (NL + "마감: " + ", ".join(f"{d[5:]} {t}" for d, t in dl) if dl else ""),
    "wheel": "🎡 Life Wheel (낮은 순)" + NL + NL.join(
        f"{title_of(w)[:6]} {bar((prop(w, 'Score (1-10)') or 0) * 10)} {prop(w, 'Score (1-10)') or 0}" for w in wheel[:8]),
}
for k, text in R.items():
    bid = I.get("home:" + k)
    if bid:
        api("PATCH", f"/blocks/{bid}", {"callout": {"rich_text": rt(text)}})
print("home reports updated")
