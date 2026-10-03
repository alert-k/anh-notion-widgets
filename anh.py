"""CLI for Notion quick-capture. Usable by you, Claude Code hooks, and iOS/macOS Shortcuts (via SSH/URL).
  anh memo "text" [--type To-do|아이디어|스티커|지식] [--pin]
  anh task "title" [--area 보안] [--due 2026-10-10] [--quad Q1]
  anh log  "text"            # append to today's Daily journal Highlight
  anh study "과목/유닛ID" 50  # add study session (minutes); matches Subject or Roadmap Unit ID
  anh post "title" --type "CTF Writeup" --site horyz.io"""
import argparse, sys
from datetime import datetime, timedelta, timezone
from lib import api, ids, rt, query_all

I = ids()
today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("text"); ap.add_argument("arg2", nargs="?")
ap.add_argument("--type"); ap.add_argument("--pin", action="store_true"); ap.add_argument("--area")
ap.add_argument("--due"); ap.add_argument("--quad"); ap.add_argument("--site", default="horyz.io")
a = ap.parse_args()


def mk(db, props): return api("POST", "/pages", {"parent": {"database_id": I[db]}, "properties": props})["url"]


if a.cmd == "memo":
    print(mk("inbox", {"Memo": {"title": rt(a.text)}, "Type": {"select": {"name": a.type or "아이디어"}},
                       "Pin": {"checkbox": a.pin}, "Status": {"select": {"name": "미처리"}}}))
elif a.cmd == "task":
    p = {"Name": {"title": rt(a.text)}, "Status": {"select": {"name": "대기"}}}
    if a.area: p["Area"] = {"select": {"name": a.area}}
    if a.due: p["Due"] = {"date": {"start": a.due}}
    if a.quad:  # Q1 중요·긴급, Q2 중요, Q3 긴급
        imp = "높음" if a.quad in ("Q1", "Q2") else "낮음"; urg = "높음" if a.quad in ("Q1", "Q3") else "낮음"
        p["중요"] = {"select": {"name": imp}}; p["긴급"] = {"select": {"name": urg}}
    print(mk("tasks", p))
elif a.cmd == "log":
    r = query_all(I["journal"], {"and": [{"property": "Type", "select": {"equals": "Daily"}},
                                         {"property": "Date", "date": {"equals": today}}]})
    pid = r[0]["id"] if r else api("POST", "/pages", {"parent": {"database_id": I["journal"]}, "properties": {
        "Title": {"title": rt(today + " Daily")}, "Type": {"select": {"name": "Daily"}}, "Date": {"date": {"start": today}}}})["id"]
    api("PATCH", f"/blocks/{pid}/children", {"children": [{"object": "block", "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rt(f"{datetime.now().strftime('%H:%M')} {a.text}")}}]})
    print("logged")
elif a.cmd == "study":
    if not a.arg2: sys.exit("usage: anh study <subject|unitID> <minutes>")
    p = {"Session": {"title": rt(f"{a.text} {a.arg2}m")}, "Date": {"date": {"start": today}}, "Minutes": {"number": float(a.arg2)}}
    u = api("POST", f"/databases/{I['roadmap']}/query", {"filter": {"property": "Unit ID", "rich_text": {"equals": a.text}}})["results"]
    s = api("POST", f"/databases/{I['subjects']}/query", {"filter": {"property": "Subject", "title": {"equals": a.text}}})["results"]
    if u: p["Roadmap Unit"] = {"relation": [{"id": u[0]["id"]}]}
    if s: p["Subject"] = {"relation": [{"id": s[0]["id"]}]}
    if not (u or s): print("warn: no matching Subject/Unit, saved unlinked")
    print(mk("sessions", p))
elif a.cmd == "post":
    print(mk("posts", {"Title": {"title": rt(a.text)}, "Site": {"select": {"name": a.site}},
                       "Type": {"select": {"name": a.type or "Research"}}, "Status": {"select": {"name": "아이디어"}}}))
else:
    sys.exit(__doc__)
