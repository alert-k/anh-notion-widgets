"""Rebuild Home as a dense multi-column dashboard. Report callouts are filled by sync.py (ids stored as home:*)."""
import urllib.request, json
from lib import api, ids, rt, save_ids, _token, VER
I = ids(); HOME = "3ee175d9-b3e1-80fa-be67-cb06ab4d1a74"; B = "https://alert-k.github.io/anh-notion-widgets/"


def move(pid):
    req = urllib.request.Request(f"https://api.notion.com/v1/pages/{pid}/move", method="POST",
        data=json.dumps({"parent": {"type": "page_id", "page_id": I["vault"]}}).encode(),
        headers={"Authorization": "Bearer " + _token(), "Notion-Version": VER, "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30).read()


for k in ["hub:act", "hub:log", "hub:sec", "hub:study", "hub:job", "hub:pkm", "hub:guide", "sites", "lore"]:
    if I.get(k) and f"moved:{k}" not in I:
        move(I[k]); I[f"moved:{k}"] = 1; save_ids(I)

# clear old body (keep child pages)
for b in api("GET", f"/blocks/{HOME}/children?page_size=100")["results"]:
    if b["type"] != "child_page":
        api("DELETE", f"/blocks/{b['id']}")

def co(text, emoji, color="default"):
    return {"object": "block", "type": "callout", "callout": {"rich_text": rt(text), "icon": {"type": "emoji", "emoji": emoji}, "color": color}}
def lk(kind, i): return {"object": "block", "type": "link_to_page", "link_to_page": {"type": kind, kind: i}}
def col(*kids): return {"object": "block", "type": "column", "column": {"children": list(kids)}}
def row(*cols): return {"object": "block", "type": "column_list", "column_list": {"children": list(cols)}}
def emb(u): return {"object": "block", "type": "embed", "embed": {"url": B + u}}
def bm(u): return {"object": "block", "type": "bookmark", "bookmark": {"url": u}}
def hd(t): return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rt(t)}}
def dv(): return {"object": "block", "type": "divider", "divider": {}}
hub = lambda k: lk("page_id", I[k])

top = [
 co("🧙 재의 마녀의 여행 노트 — 오늘도 한 걸음. 별 브로치 ⭐는 TOSS 여정이 25% 진행될 때마다 하나씩 늘어나요.", "⭐", "gray_background"),
 row(
  col(hd("⚡ 퀵 링크"), hub("hub:act"), hub("hub:log"), hub("hub:sec"), hub("hub:study"), hub("hub:job"), hub("hub:pkm"), hub("hub:guide"), hub("sites"), hub("lore")),
  col(co("loading…", "📅", "blue_background"), co("loading…", "📌", "yellow_background")),
  col(co("loading…", "🗺️", "purple_background"), co("loading…", "🧪", "green_background"))),
 dv(),
 row(col(emb("dash.html")), col(emb("cal.html")), col(emb("focus.html"))),
 dv(),
 row(
  col(co("loading…", "✅", "red_background"), hub("hub:act")),
  col(co("loading…", "📮", "orange_background"), hub("hub:job")),
  col(co("loading…", "🎡", "pink_background"), hub("hub:log"))),
 dv(),
 row(col(bm("https://horyz.io/")), col(bm("https://lab.horyz.io/"))),
]
res = api("PATCH", f"/blocks/{HOME}/children", {"children": top})
# collect callout ids in order: daily, pins, toss, lab, tasks, apps, wheel
ids_ = []
def walk(bid):
    for b in api("GET", f"/blocks/{bid}/children?page_size=100")["results"]:
        if b["type"] == "callout": ids_.append(b["id"])
        elif b["type"] in ("column_list", "column"): walk(b["id"])
for b in api("GET", f"/blocks/{HOME}/children?page_size=100")["results"]:
    if b["type"] == "column_list": walk(b["id"])
names = ["daily", "pins", "toss", "lab", "tasks", "apps", "wheel"]
for n, i in zip(names, ids_): I[f"home:{n}"] = i
save_ids(I); print(len(ids_), "report callouts")
