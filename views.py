"""Create database views (Notion-Version 2025-09-03 views API). Idempotent: view names tracked in ids.json."""
import json, os, urllib.request, urllib.error
from lib import api, ids, save_ids, _token

I = ids()


def v(method, path, body=None):
    req = urllib.request.Request("https://api.notion.com/v1" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + _token(), "Notion-Version": "2025-09-03", "Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code} {e.read().decode()[:400]}")


# ---- subjects: one 학기 select replaces 학년+학기+formula ----
SEM = ["1학년 1학기", "1학년 2학기", "2학년 1학기", "2학년 2학기", "3학년 1학기", "3학년 2학기"]
if "subjects:sem" not in I:
    api("PATCH", f"/databases/{I['subjects']}", {"properties": {
        "학기": {"select": {"options": [{"name": s} for s in SEM]}}, "학년": None, "학기 구분": None}})
    from lib import query_all
    for r in query_all(I["subjects"], {"property": "분야", "select": {"equals": "대학"}}):
        api("PATCH", f"/pages/{r['id']}", {"properties": {"학기": {"select": {"name": SEM[0]}}}})
    I["subjects:sem"] = 1; save_ids(I)


def ds_of(key):
    return v("GET", f"/databases/{I[key]}")["data_sources"][0]["id"]


def pid(ds, name):
    return v("GET", f"/data_sources/{ds}")["properties"][name]["id"]


def make(key, name, vtype="table", flt=None, sorts=None, group=None, gtype="select", cal=None):
    tag = f"view:{key}:{name}"
    if tag in I:
        return
    ds = ds_of(key)
    body = {"database_id": I[key], "data_source_id": ds, "name": name, "type": vtype}
    if flt: body["filter"] = flt
    if sorts: body["sorts"] = sorts
    cfg = {"type": vtype}
    if group:
        cfg["group_by"] = {"type": gtype, "property_id": pid(ds, group), "sort": {"type": "ascending"}}
    if cal:
        cfg["date_property_id"] = pid(ds, cal)
    if len(cfg) > 1:
        body["configuration"] = cfg
    v("POST", "/views", body)
    I[tag] = 1; save_ids(I)
    print("view:", key, name)


def rename_default(key, name):
    tag = f"viewdefault:{key}"
    if tag in I:
        return
    first = v("GET", f"/views?database_id={I[key]}")["results"][0]["id"]
    v("PATCH", f"/views/{first}", {"name": name}); I[tag] = 1; save_ids(I)


# subjects (default view was already used for a throw-away test view -> remove it if present)
for r in v("GET", f"/views?database_id={I['subjects']}")["results"]:
    info = v("GET", f"/views/{r['id']}")
    if info["name"] == "대학 · 학기별" and "view:subjects:대학 · 학기별" not in I:
        v("DELETE", f"/views/{r['id']}")
rename_default("subjects", "전체")
make("subjects", "대학 · 학기별", flt={"property": "분야", "select": {"equals": "대학"}}, group="학기")
make("subjects", "보안", flt={"property": "분야", "select": {"equals": "보안"}})
make("subjects", "자격증·어학·독서", flt={"or": [{"property": "분야", "select": {"equals": x}} for x in ("자격증", "어학", "독서")]})

# roadmap: real order + phase groups
rename_default("roadmap", "전체 (번호순)")
make("roadmap", "Phase별", sorts=[{"property": "#", "direction": "ascending"}], group="Phase")
make("roadmap", "진행 중", flt={"property": "Status", "select": {"equals": "진행 중"}}, sorts=[{"property": "#", "direction": "ascending"}])
make("roadmap", "복습 예정", flt={"property": "복습 예정", "date": {"is_not_empty": True}}, sorts=[{"property": "복습 예정", "direction": "ascending"}])

# tasks / apps / journal
rename_default("tasks", "전체")
make("tasks", "보드", vtype="board", group="Status")
make("tasks", "열린 할 일", flt={"property": "Done", "checkbox": {"equals": False}}, sorts=[{"property": "Due", "direction": "ascending"}])
make("tasks", "캘린더", vtype="calendar", cal="Due")
rename_default("apps", "전체")
make("apps", "보드", vtype="board", group="Status")
make("apps", "캘린더", vtype="calendar", cal="Deadline")
rename_default("journal", "전체")
make("journal", "캘린더", vtype="calendar", cal="Date")
make("sessions", "캘린더", vtype="calendar", cal="Date")
rename_default("sessions", "전체")
make("posts", "보드", vtype="board", group="Status")
print("views done")
