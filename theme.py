"""Elaina (Wandering Witch) theme text: retitles + lore page. Facts only from cited sources; no invented quotes."""
from lib import api, ids, rt, save_ids
I = ids(); HOME = "3ee175d9-b3e1-80fa-be67-cb06ab4d1a74"
def ttl(db, t, icon=None):
    api("PATCH", f"/databases/{I[db]}", {"title": rt(t)})
ttl("journal", "여행 일기 (Journal)"); ttl("roadmap", "TOSS 여정 (로드맵)"); ttl("ctf", "CTF / Lab 여행 기록")
ttl("posts", "Site Posts (horyz.io 발행 파이프라인)"); ttl("inbox", "Inbox (주머니 속 메모)")
# Home first callout
kids = api("GET", f"/blocks/{HOME}/children?page_size=100")["results"]
cal = next(b for b in kids if b["type"] == "callout")
api("PATCH", f"/blocks/{cal['id']}", {"callout": {"rich_text": rt(
    "재의 마녀의 여행 노트 — 보안공부 · 대학 · 취업 · 여행 일기 · TOSS 여정을 한 곳에서. 별 브로치(⭐)는 로드맵을 진행할수록 늘어나요."), "icon": {"emoji": "🧙"}}})
if "lore" not in I:
    b = lambda t, x: {"object": "block", "type": t, t: {"rich_text": rt(x)}}
    r = api("POST", "/pages", {"parent": {"page_id": HOME}, "icon": {"type": "emoji", "emoji": "📖"},
        "properties": {"title": {"title": rt("재의 마녀 도감")}}, "children": [
        b("callout", "테마 근거 메모 — 『마녀의 여행』(魔女の旅々) 일레이나. 아래 항목만 검색으로 확인된 내용입니다."),
        b("heading_3", "재의(灰) 마녀"), b("bulleted_list_item", "마녀 수련 1년 뒤 스승에게 인정받으며 받은 이름. 재색 긴 머리에서 유래."),
        b("bulleted_list_item", "스승: 별가루(Stardust) 마녀 프랑 → 이 워크스페이스의 '스승 = 로드맵·가이드' 은유."),
        b("heading_3", "소품 → 워크스페이스 모티프"),
        b("bulleted_list_item", "별 모양 브로치 = 마녀의 증표 → 로드맵 25% 단위 배지(⭐)."),
        b("bulleted_list_item", "빗자루 = 여정(취업·로드맵) / 검은 로브·뾰족 모자 = 보안 허브 / 고양이 = 지식 허브(영상 속 장면)."),
        b("bulleted_list_item", "이야기 구조: 여러 나라를 도는 일기식 여행기 → Journal을 '여행 일기', 로드맵 Phase를 '나라'처럼 사용."),
        b("heading_3", "팔레트"), b("paragraph", "크림 #f8f4ea · 블러시 #e9c8bd · 모브 #856165 · 미스트 #caddd7 · 스카이 #8fd3d8 · 바이올렛 #8a7cc4 · 사파이어(눈동자) #4a6fd0 · 잉크 #2b2328"),
        b("heading_3", "출처"),
        b("bulleted_list_item", "https://en.wikipedia.org/wiki/Wandering_Witch:_The_Journey_of_Elaina"),
        b("bulleted_list_item", "https://wandering-witch.fandom.com/wiki/Elaina"),
        b("bulleted_list_item", "https://ja.wikipedia.org/wiki/魔女の旅々 · https://dic.pixiv.net/a/灰の魔女")]})
    I["lore"] = r["id"]; save_ids(I)
print("theme ok")
