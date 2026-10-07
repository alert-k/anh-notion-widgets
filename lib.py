"""Notion API client (stdlib only) + id store shared by build/sync/anh."""
import json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
IDS = os.path.join(ROOT, "ids.json")
VER = "2022-06-28"


def _token():
    t = os.environ.get("NOTION")
    if t:
        return t
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.startswith("NOTION="):
                return line.split("=", 1)[1].strip().strip("\"'")
    sys.exit("NOTION token missing (env NOTION or .env)")


def secret(name):
    """env var, else .env file (local runs)."""
    if os.environ.get(name):
        return os.environ[name]
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return None


def api(method, path, body=None):
    req = urllib.request.Request(
        "https://api.notion.com/v1" + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Authorization": "Bearer " + _token(), "Notion-Version": VER,
                 "Content-Type": "application/json"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                time.sleep(0.3)  # ~3 req/s limit
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode()
            if e.code in (429, 502, 503, 504) and attempt < 5:
                time.sleep(2 ** attempt)
                continue
            sys.exit(f"{method} {path} -> {e.code}: {msg[:600]}")
    sys.exit("unreachable")


def ids():
    return json.load(open(IDS, encoding="utf-8")) if os.path.exists(IDS) else {}


def save_ids(d):
    json.dump(d, open(IDS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def query_all(db_id, flt=None):
    out, cur = [], None
    while True:
        body = {"page_size": 100}
        if flt:
            body["filter"] = flt
        if cur:
            body["start_cursor"] = cur
        r = api("POST", f"/databases/{db_id}/query", body)
        out += r["results"]
        if not r["has_more"]:
            return out
        cur = r["next_cursor"]


def rt(s):
    return [{"type": "text", "text": {"content": s[:1900]}}]


def title_of(page):
    for p in page["properties"].values():
        if p["type"] == "title":
            return "".join(x["plain_text"] for x in p["title"])
    return ""
