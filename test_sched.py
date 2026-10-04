"""Check: fixed blocks are removed from the awake window and leftover time is what gets allocated."""
from datetime import date, datetime, timedelta
src = open("sync.py", encoding="utf-8").read()
a, b = src.index("# ---- 2a. schedule"), src.index("def week_study_hours")
ns = {"timedelta": timedelta, "prop": lambda r, k: r.get(k), "title_of": lambda r: r["t"], "now": datetime(2026, 10, 5, 7, 0)}
exec(src[a:b], ns)
d = date(2026, 10, 5)  # Monday
rows = [{"t": "학교", "Repeat": "없음", "properties": {"When": {"date": {"start": "2026-10-05T12:00:00.000+09:00", "end": "2026-10-05T17:00:00.000+09:00"}}}},
        {"t": "알바", "Repeat": "매주", "properties": {"When": {"date": {"start": "2026-09-28T17:00:00.000+09:00", "end": "2026-09-28T23:00:00.000+09:00"}}}},
        {"t": "종일", "Repeat": "없음", "properties": {"When": {"date": {"start": "2026-10-05"}}}}]
ns["SCHEDULE_ROWS"] = rows
busy = ns["busy_for"](d)
assert [(s, e) for s, e, _ in busy] == [(720, 1020), (1020, 1380)], busy      # weekly repeat matches Monday, all-day ignored
assert ns["free_blocks"](busy) == [(480, 720), (1380, 1410)], ns["free_blocks"](busy)  # 08-12 and 23:00-23:30
assert ns["busy_for"](date(2026, 10, 6)) == []                                 # Tuesday: no school, no weekly 알바
print("schedule checks ok")
