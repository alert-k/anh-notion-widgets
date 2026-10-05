"""Notion -> docs/data.json (widgets) ; ensure today's Daily journal ; GitHub commit count -> Journal.
Run locally or from GitHub Actions (env NOTION, optional GH_USER, DB ids from ids.json or IDS_JSON env)."""
import json, os, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone
from collections import Counter
from lib import api, ids, query_all, rt, title_of, ROOT, secret

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

# ---- 2a. schedule: fixed blocks -> free time -> study allocation (knobs below) ----
from datetime import datetime as _dt
WAKE, SLEEP = 8 * 60, 23 * 60 + 30   # awake window (minutes from midnight)
STUDY_CAP_H, CHUNK_H, BUFFER_MIN, SHARE = 4.0, 2.0, 10, 0.5  # per-day cap, session length, gap, share of free time used for study
MIN_BLOCK = 30
fmt_m = lambda m: f"{m // 60:02d}:{m % 60:02d}"
SCHEDULE_ROWS = []


def busy_for(day):
    out = []
    for r in SCHEDULE_ROWS:
        w = r["properties"]["When"]["date"]
        if not w or "T" not in w["start"]:
            continue  # all-day entries carry no time block
        s = _dt.fromisoformat(w["start"])
        e = _dt.fromisoformat(w["end"]) if w.get("end") else s + timedelta(hours=1)
        rep = prop(r, "Repeat") == "매주"
        if s.date() == day or (rep and s.date() <= day and s.weekday() == day.weekday()):
            end_m = e.hour * 60 + e.minute if e.date() == s.date() else 24 * 60
            out.append((s.hour * 60 + s.minute, end_m, title_of(r)))
    return sorted(out)


def free_blocks(busy, after=0):
    cur, free = max(WAKE, after), []
    for s, e, _ in busy:
        if s - cur >= MIN_BLOCK:
            free.append((cur, s))
        cur = max(cur, e)
    if SLEEP - cur >= MIN_BLOCK:
        free.append((cur, SLEEP))
    return free


def week_study_hours():
    """Next 7 days' free time x SHARE -> hours handed to the lab planner (clamped 1..60)."""
    tot = 0.0
    for i in range(7):
        d = now.date() + timedelta(days=i)
        after = now.hour * 60 + now.minute if i == 0 else 0
        tot += sum(e - s for s, e in free_blocks(busy_for(d), after)) / 60
    return max(1.0, min(60.0, round(tot * SHARE, 1)))


def allocate_today(rm_pages):
    """Place today's study cards into free blocks as timed Tasks. Returns timeline lines for the home report."""
    d = now.date()
    nowm = (now.hour * 60 + now.minute + 9) // 10 * 10  # round up to next 10 min
    busy = busy_for(d)
    free = free_blocks(busy, nowm)
    by_uid = {prop(p_, "Unit ID"): p_ for p_ in rm_pages}
    status = {p_["id"]: prop(p_, "Status") for p_ in rm_pages}

    def left_h(p_):
        return max((prop(p_, "Est hours") or 1) - (prop(p_, "누적(분)") or 0) / 60, 0.5)

    # cards: lab plan if available, else the next open units from the roadmap
    cards = []
    plan = LAB_PLAN or {}
    for c in plan.get("maintenance", []):
        if by_uid.get(c.get("unit_id")):
            cards.append(("복습", by_uid[c["unit_id"]], 1.0))
    seq = (plan.get("today_first") or []) + plan.get("main", [])
    pages = [by_uid[c["unit_id"]] for c in seq if by_uid.get(c.get("unit_id"))]
    if not pages:  # fallback before lab export exists
        opens = sorted((p_ for p_ in rm_pages if prop(p_, "Status") not in ("완료", "건너뜀")),
                       key=lambda p_: (prop(p_, "Status") != "진행 중", prop(p_, "#") or 0))
        pages = opens[:2]
    seen = set()
    for p_ in pages:
        if p_["id"] not in seen and status[p_["id"]] != "완료":
            seen.add(p_["id"]); cards.append(("오늘", p_, left_h(p_)))

    from vlib import rng  # Notion filters compare in UTC: use explicit KST day range
    autos = query_all(I["tasks"], {"and": [{"property": "Source", "select": {"equals": "lab 플랜"}}, rng("Due", today, today)]})
    spent = 0.0
    for t in autos:
        name = title_of(t)
        if name.startswith("[이번 주]"):
            continue
        if t["properties"]["Done"]["checkbox"]:
            spent += prop(t, "예상(h)") or 0
        elif prop(t, "Status") == "대기":
            api("PATCH", f"/pages/{t['id']}", {"archived": True})  # re-planned below from the current schedule

    budget = STUDY_CAP_H - spent
    placed, i = [], 0
    free = list(free)
    for tag, p_, h in cards:
        remaining = h
        while remaining > 0.01 and budget > 0.01 and i < len(free):
            s, e = free[i]
            mins = int(min(CHUNK_H * 60, e - s, budget * 60, remaining * 60))
            if mins < MIN_BLOCK:
                i += 1
                continue
            hrs = round(mins / 60, 1)
            P = {"Name": {"title": rt(f"[{tag}] {title_of(p_)} — {hrs}h")},
                 "Due": {"date": {"start": f"{today}T{fmt_m(s)}:00", "end": f"{today}T{fmt_m(s + mins)}:00", "time_zone": "Asia/Seoul"}},
                 "Status": {"select": {"name": "대기"}}, "Area": {"select": {"name": "토스로드맵"}}, "Type": {"select": {"name": "Daily"}},
                 "Source": {"select": {"name": "lab 플랜"}}, "예상(h)": {"number": hrs}, "중요": {"select": {"name": "높음"}},
                 "긴급": {"select": {"name": "높음"}}, "Roadmap Unit": {"relation": [{"id": p_["id"]}]}}
            api("POST", "/pages", {"parent": {"database_id": I["tasks"]}, "properties": P})
            placed.append((s, s + mins, f"📚 {tag} {title_of(p_)[:18]}"))
            free[i] = (s + mins + BUFFER_MIN, e)
            budget -= mins / 60
            remaining -= mins / 60
            if free[i][1] - free[i][0] < MIN_BLOCK:
                i += 1
    # timeline for the home report
    left = [(s, e, "🟢 여유") for s, e in free if e - s >= MIN_BLOCK]
    return [f"{fmt_m(s)}–{fmt_m(e)} {n}" for s, e, n in sorted(busy + placed + left)]


def load_schedule():
    global SCHEDULE_ROWS
    SCHEDULE_ROWS = query_all(I["schedule"])


# ---- 2b. lab.horyz.io progress -> Notion (lab is the source of truth; needs /api/roadmap/export + LAB_SYNC_KEY) ----
LAB_PLAN = None
TIMELINE = []
LAB_OK = False
ST = {"todo": "대기", "doing": "진행 중", "in_progress": "진행 중", "done": "완료", "blocked": "막힘"}


def lab_sync(rm_pages, journal_page_id):
    global LAB_PLAN, LAB_OK
    key = secret("LAB_SYNC_KEY")
    if not key:
        return 0
    req = urllib.request.Request(f"https://lab.horyz.io/api/roadmap/export?hours={week_study_hours()}",
                                 headers={"X-Sync-Key": key, "User-Agent": "anh-sync"})
    try:
        data = json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:  # endpoint not deployed yet / key mismatch -> skip, never break sync
        print("lab export skipped:", getattr(e, "code", e))
        return 0
    LAB_PLAN = data.get("plan")
    LAB_OK = True
    pr = data["progress"]
    status, skip = pr.get("unit_status", {}), set(pr.get("understood_skip", []))
    changed = 0
    for pg in rm_pages:
        uid = prop(pg, "Unit ID")
        st = status.get(uid, "todo")
        label = "건너뜀" if (uid in skip and st != "done") else ST.get(st, "진행 중")
        want = {"Status": label, "복습 예정": pr.get("recall_due", {}).get(uid),
                "복습 회차": pr.get("recall_step", {}).get(uid),
                "완료일": pr.get("recall_day0", {}).get(uid) if label == "완료" else None,
                "달성 Depth": pr.get("unit_depth", {}).get(uid)}
        have = {k: prop(pg, k) for k in want}
        if want == have:
            continue
        P = {"Status": {"select": {"name": label}},
             "복습 예정": {"date": {"start": want["복습 예정"]} if want["복습 예정"] else None},
             "복습 회차": {"number": want["복습 회차"]},
             "완료일": {"date": {"start": want["완료일"]} if want["완료일"] else None},
             "달성 Depth": {"select": {"name": want["달성 Depth"]} if want["달성 Depth"] else None}}
        api("PATCH", f"/pages/{pg['id']}", {"properties": P})
        if label == "완료" and have["Status"] != "완료":
            make_note(pg)
        changed += 1
    # weekly plans: upsert by week
    have_w = {prop(w, "Week"): w for w in query_all(I["weekly"])}
    for wp in pr.get("weekly_plans", []):
        P = {"Week": {"title": rt(wp["week"])}, "Hours": {"number": wp.get("hours")},
             "Generated": {"date": {"start": (wp.get("generated") or "")[:10]}} if wp.get("generated") else {"date": None}}
        if wp["week"] in have_w:
            api("PATCH", f"/pages/{have_w[wp['week']]['id']}", {"properties": P})
        else:
            api("POST", "/pages", {"parent": {"database_id": I["weekly"]}, "properties": P})
    # today's completions -> Journal
    day0 = pr.get("recall_day0", {})
    names = {prop(p_, "Unit ID"): title_of(p_) for p_ in rm_pages}
    done_today = [names.get(u, u) for u, d in day0.items() if d == today and status.get(u) == "done"]
    api("PATCH", f"/pages/{journal_page_id}", {"properties": {
        "Lab 완료": {"rich_text": rt(", ".join(done_today))}, **({"공부": {"checkbox": True}} if done_today else {})}})
    print("lab sync: units changed", changed, "| done today", len(done_today))
    return changed


# ---- 2c. today's tasks: lab plan + weekday routines; auto-check when lab unit is done ----
def gen_today_tasks(rm_pages):
    wd = "월화수목금토일"[now.weekday()]
    unit_by_uid = {prop(p_, "Unit ID"): p_ for p_ in rm_pages}
    unit_status = {p_["id"]: prop(p_, "Status") for p_ in rm_pages}
    auto = query_all(I["tasks"], {"or": [{"property": "Source", "select": {"equals": "lab 플랜"}},
                                         {"property": "Source", "select": {"equals": "루틴"}}]})
    existing = {title_of(t) for t in auto if prop(t, "Due") == today}
    for t in auto:
        if t["properties"]["Done"]["checkbox"]:
            continue
        rel = t["properties"]["Roadmap Unit"]["relation"]
        due = prop(t, "Due")
        if rel and unit_status.get(rel[0]["id"]) == "완료":  # checked on lab -> checked here
            api("PATCH", f"/pages/{t['id']}", {"properties": {"Done": {"checkbox": True}, "Status": {"select": {"name": "완료"}}}})
        elif due and due < today and prop(t, "Status") != "미완료":  # yesterday's leftovers stay as a record
            api("PATCH", f"/pages/{t['id']}", {"properties": {"Status": {"select": {"name": "미완료"}}}})

    def make(name, area, source, unit=None, due=None):
        P = {"Name": {"title": rt(name)}, "Due": {"date": {"start": due or today}}, "Status": {"select": {"name": "대기"}},
             "Area": {"select": {"name": area}}, "Type": {"select": {"name": "Daily"}}, "Source": {"select": {"name": source}},
             "중요": {"select": {"name": "높음"}}, "긴급": {"select": {"name": "높음"}}}
        if unit:
            P["Roadmap Unit"] = {"relation": [{"id": unit["id"]}]}
        api("POST", "/pages", {"parent": {"database_id": I["tasks"]}, "properties": P})
        existing.add(name + (due or ""))

    plan = LAB_PLAN or {}
    sun = (now.date() + timedelta(days=6 - now.weekday())).isoformat()
    wk_have = {title_of(t) for t in auto if prop(t, "Due") == sun}
    for c in plan.get("main", []) + plan.get("support", []):
        name = f"[이번 주] {c['title']}"
        u = unit_by_uid.get(c.get("unit_id"))
        if name not in wk_have and not (u and unit_status.get(u["id"]) == "완료"):
            make(name, "토스로드맵", "lab 플랜", u, due=sun)
            wk_have.add(name)
    for r in query_all(I["routines"], {"property": "Active", "checkbox": {"equals": True}}):
        days = [x["name"] for x in r["properties"]["Days"]["multi_select"]]
        name = title_of(r)
        if wd in days and name not in existing:
            make(name, prop(r, "Area") or "생활", "루틴")


# ---- 2d. study auto-fields, knowledge stubs, weekly/monthly reviews ----
def study_auto():
    """Journal(today).공부(h) = sum of today's Study Sessions; 공부 checkbox turns on (never forced off)."""
    mins = sum(prop(s, "Minutes") or 0 for s in query_all(I["sessions"], {"property": "Date", "date": {"equals": today}}))
    P = {"공부(h)": {"number": round(mins / 60, 1)}}
    if mins:
        P["공부"] = {"checkbox": True}
    api("PATCH", f"/pages/{dj[0]['id']}", {"properties": P})


def make_note(unit_page):
    """Unit finished on lab -> Knowledge stub linked to that unit (once)."""
    title = "정리 — " + title_of(unit_page)
    if query_all(I["pkm"], {"property": "Note", "title": {"equals": title}}):
        return
    H = lambda t: {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rt(t)}}
    Pp = lambda: {"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}
    api("POST", "/pages", {"parent": {"database_id": I["pkm"]}, "properties": {
        "Note": {"title": rt(title)}, "PARA": {"select": {"name": "Resources"}},
        "Roadmap Unit": {"relation": [{"id": unit_page["id"]}]}},
        "children": [H("핵심 원리 (내 말로)"), Pp(), H("직접 해본 것 · 증거"), Pp(), H("헷갈렸던 점"), Pp(), H("복습 질문")]
        + [Pp()]})


def period_review(kind, title, a, b):
    """Weekly/Monthly Journal page with computed stats; created once per period."""
    if query_all(I["journal"], {"and": [{"property": "Type", "select": {"equals": kind}},
                                        {"property": "Title", "title": {"equals": title}}]}):
        return
    rg = lambda p: {"and": [{"property": p, "date": {"on_or_after": a}}, {"property": p, "date": {"on_or_before": b}}]}
    days = query_all(I["journal"], {"and": [{"property": "Type", "select": {"equals": "Daily"}}, rg("Date")]})
    sc = [prop(d, "루틴 점수(%)") or 0 for d in days]
    study_h = round(sum(prop(d, "공부(h)") or 0 for d in days), 1)
    commits = int(sum(prop(d, "GitHub 커밋") or 0 for d in days))
    tks = query_all(I["tasks"], rg("Due"))
    done = sum(1 for t in tks if t["properties"]["Done"]["checkbox"])
    units = sum(1 for r in rm if (prop(r, "완료일") or "") and a <= prop(r, "완료일") <= b)
    line = (f"{a} ~ {b} · 기록 {len(days)}일 · 루틴 평균 {round(sum(sc) / len(sc)) if sc else 0}% · 공부 {study_h}h · "
            f"커밋 {commits} · Task {done}/{len(tks)} 완료 · 로드맵 유닛 {units}개 완료")
    H = lambda t: {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rt(t)}}
    Pp = lambda: {"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}
    api("POST", "/pages", {"parent": {"database_id": I["journal"]}, "properties": {
        "Title": {"title": rt(title)}, "Type": {"select": {"name": kind}},
        "Date": {"date": {"start": a, "end": b}}, "공부(h)": {"number": study_h}, "GitHub 커밋": {"number": commits},
        "Highlight": {"rich_text": rt(line)}},
        "children": [{"object": "block", "type": "callout", "callout": {"rich_text": rt(line), "icon": {"type": "emoji", "emoji": "📊"}}},
                     H("Keep — 계속할 것"), Pp(), H("Problem — 문제였던 것"), Pp(), H("Try — 다음에 시도할 것"), Pp()]})
    print("review created:", title)


def periodic_journals():
    d = now.date()
    if d.weekday() == 0:  # Monday -> review last week
        a, b = d - timedelta(days=7), d - timedelta(days=1)
        period_review("Weekly", a.strftime("%G-W%V") + " Weekly", a.isoformat(), b.isoformat())
    if d.day == 1:  # 1st -> review last month
        b = d - timedelta(days=1)
        period_review("Monthly", b.strftime("%Y-%m") + " Monthly", b.replace(day=1).isoformat(), b.isoformat())


# ---- 3. data.json ----
out = {"updated": now.isoformat(timespec="minutes"), "today": today}

rm = query_all(I["roadmap"])
load_schedule()
if lab_sync(rm, dj[0]["id"]):
    rm = query_all(I["roadmap"])
gen_today_tasks(rm)
TIMELINE = allocate_today(rm)
study_auto()
periodic_journals()
try:  # keep time-horizon view filters (오늘/이번 주/이번 달/올해, 로드맵 '지금') current
    from vlib import refresh
    opens = [prop(r, "#") for r in rm if prop(r, "Status") not in ("완료", "건너뜀") and prop(r, "#")]
    refresh(I, today, int(min(opens)) if opens else 1)
except SystemExit as e:
    print("view refresh skipped:", e)
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
except Exception as e:
    print("lab skipped:", e)

QO = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3}
alltasks = sorted(tasks, key=lambda t: ((prop(t, "Due") or "")[:10] != today, QO.get((prop(t, "Quadrant") or "Q9")[:2], 9), prop(t, "Due") or "9999"))
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
    "sched": "오늘 시간표" + NL + (NL.join(TIMELINE) or "일정 없음 — 시간표 DB에 입력"),
    "daily": f"{today}{NL}루틴 {bar(out['today_score'])} {out['today_score']}% · 🔥 연속 {streak}일{NL}"
             f"공부(7일) {out['study_week_min'] / 60:.1f}h · 오늘 커밋 {n}{NL}열린 Task {len(tasks)}개",
    "pins": "고정 메모" + NL + (NL.join("• " + x for x in pins) or "없음 — Inbox에서 Pin 체크"),
    "toss": f"TOSS 여정 {'⭐' * (pct_t // 25) or '☆'} {pct_t}% ({dn}/{tot}){NL}"
            f"학습 {mins / 60:.0f}h / 목록 합계 {est:.0f}h{NL}{toss_mid}{NL}일정·주간 시간은 lab.horyz.io 기준",
    "lab": "lab.horyz.io" + NL
           + (f"챌린지 {lab['challenges']}개 · 카테고리 {lab['cats']} · 리더보드 {lab['board']}명" if "challenges" in lab else "(연결 실패)")
           + (f"{NL}진행도 연동됨" if LAB_OK else f"{NL}진행도 연동 대기 (서버 export 배포 필요)"),
    "tasks": f"할 일 {len(tasks)}개{NL}" + NL.join(
        f"• {title_of(t)}" + (f"  ~{prop(t, 'Due')[5:10]}" if prop(t, "Due") else "") + f"  {(prop(t, 'Quadrant') or '')[:2]}"
        for t in alltasks[:8]),
    "apps": "지원 현황" + NL + (" · ".join(f"{k} {v}" for k, v in Counter(prop(a, "Status") for a in apps_p).items()) or "-")
            + (NL + "마감: " + ", ".join(f"{d[5:]} {t}" for d, t in dl) if dl else ""),
    "wheel": "Life Wheel (낮은 순)" + NL + NL.join(
        f"{title_of(w)[:6]} {bar((prop(w, 'Score (1-10)') or 0) * 10)} {prop(w, 'Score (1-10)') or 0}" for w in wheel[:8]),
}
for k, text in R.items():
    bid = I.get("home:" + k)
    if bid:
        api("PATCH", f"/blocks/{bid}", {"callout": {"rich_text": rt(text)}})
print("home reports updated")


# ---- 5. horyz.io posts auto-detect -> Site Posts (upsert by URL) ----
import re
SECTION_TYPE = {"research": "Research", "cve": "CVE", "bounty": "Bug Bounty"}


def fetch_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 anh-sync"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


try:
    known = {prop(r, "URL"): r for r in query_all(I["posts"]) if prop(r, "URL")}
    new = 0
    for sec, typ in SECTION_TYPE.items():
        slugs = sorted(set(re.findall(rf'href="/{sec}/([a-z0-9][a-z0-9_-]*)"', fetch_html(f"https://horyz.io/{sec}/"))))
        for slug in slugs:
            url = f"https://horyz.io/{sec}/{slug}"
            html = fetch_html(url)
            t = re.search(r"<title>(.*?)</title>", html, re.S)
            title = re.sub(r"\s*[·|—-]\s*Alert_K.*$", "", t.group(1).strip()) if t else slug
            d = re.search(r"(20\d\d-\d\d-\d\d)", html)
            props = {"Title": {"title": rt(title)}, "Site": {"select": {"name": "horyz.io"}},
                     "Type": {"select": {"name": typ}}, "Status": {"select": {"name": "발행"}}, "URL": {"url": url}}
            if d:
                props["Publish"] = {"date": {"start": d.group(1)}}
            if url in known:  # already tracked: only promote to 발행, never overwrite manual edits
                if prop(known[url], "Status") != "발행":
                    api("PATCH", f"/pages/{known[url]['id']}", {"properties": {"Status": props["Status"]}})
            else:
                api("POST", "/pages", {"parent": {"database_id": I["posts"]}, "properties": props})
                new += 1
    print("posts: new", new)
except Exception as e:  # never block sync on the public site
    print("posts skipped:", e)
