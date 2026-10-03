"""Restructure views: Tasks by time horizon (오늘/이번 주/이번 달/올해/전체), Roadmap compact. Re-runnable."""
from datetime import datetime, timedelta, timezone
from lib import ids, save_ids
from vlib import v, horizons, now_filter

I = ids()
today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()


def ds_of(key): return v("GET", f"/databases/{I[key]}")["data_sources"][0]["id"]
def props(ds): return {k: x["id"] for k, x in v("GET", f"/data_sources/{ds}")["properties"].items()}


def vis(ds, shown):
    return [{"property_id": pid, "visible": name in shown} for name, pid in props(ds).items()]


def group(ds, name, gtype):
    return {"type": gtype, "property_id": props(ds)[name], "sort": {"type": "ascending"}}


def views(key): return [r["id"] for r in v("GET", f"/views?database_id={I[key]}")["results"]]


def build(key, default_name, specs):
    ds = ds_of(key)
    ids_ = views(key)
    for extra in ids_[1:]:
        v("DELETE", f"/views/{extra}")
    for k in [k for k in I if k.startswith(f"view:{key}:") or k.startswith(f"vid:{key}:")]:
        del I[k]
    first, rest = specs[0], specs[1:]
    for i, s in enumerate([first] + rest):
        body = {"name": s["name"], "type": s.get("type", "table")}
        cfg = {"type": body["type"]}
        if s.get("group"): cfg["group_by"] = group(ds, *s["group"])
        if s.get("shown") and body["type"] == "table": cfg["properties"] = vis(ds, s["shown"])
        if s.get("cal"): cfg["date_property_id"] = props(ds)[s["cal"]]
        if len(cfg) > 1: body["configuration"] = cfg
        if s.get("filter"): body["filter"] = s["filter"]
        if s.get("sorts"): body["sorts"] = s["sorts"]
        if i == 0:
            r = v("PATCH", f"/views/{ids_[0]}", body)
        else:
            body.update({"database_id": I[key], "data_source_id": ds})
            r = v("POST", "/views", body)
        I[f"vid:{key}:{s['name']}"] = r["id"]; save_ids(I)
        print("view", key, s["name"])


H = horizons(today)
T_SHOWN = {"Name", "Done", "Due", "Area", "Type", "Quadrant", "Project", "Status"}
G = ("Done", "checkbox")
build("tasks", "오늘", [
    {"name": "오늘", "filter": H["오늘"], "group": G, "shown": T_SHOWN},
    {"name": "이번 주", "filter": H["이번 주"], "group": G, "shown": T_SHOWN},
    {"name": "이번 달", "filter": H["이번 달"], "group": G, "shown": T_SHOWN},
    {"name": "올해", "filter": H["올해"], "group": G, "shown": T_SHOWN},
    {"name": "전체", "group": G, "shown": T_SHOWN, "sorts": [{"property": "Due", "direction": "ascending"}]},
    {"name": "보드", "type": "board", "group": ("Status", "select")},
    {"name": "캘린더", "type": "calendar", "cal": "Due"}])

R_SHOWN = {"Unit", "#", "Status", "Est hours", "Progress(%)", "복습 예정"}
S = [{"property": "#", "direction": "ascending"}]
build("roadmap", "지금", [
    {"name": "지금", "filter": now_filter(1), "sorts": S, "shown": R_SHOWN},
    {"name": "Phase별", "group": ("Phase", "select"), "sorts": S, "shown": R_SHOWN},
    {"name": "전체 (번호순)", "sorts": S, "shown": R_SHOWN}])
print("views2 done")
