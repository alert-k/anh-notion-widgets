"""Build the ANH all-in-one workspace under the 'ANH 올인원' page. Resumable: finished steps are in ids.json."""
import json, os
from lib import api, ids, save_ids, rt

PARENT = "3ee175d9-b3e1-80fa-be67-cb06ab4d1a74"
ROADMAP = os.environ.get("ROADMAP_JSON", r"C:\Users\hwang\orca\redteam-lab\api-server\roadmap_content.json")
I = ids()

AREAS = ["보안", "대학", "취업", "토스로드맵", "생활"]
C = ["blue", "green", "orange", "purple", "pink", "yellow", "red", "brown", "gray"]


def sel(*names):
    return {"select": {"options": [{"name": n, "color": C[i % len(C)]} for i, n in enumerate(names)]}}


# ---- block helpers ----
def blk(t, text, **kw):
    return {"object": "block", "type": t, t: {"rich_text": rt(text), **kw}}
def h(n, text): return blk(f"heading_{n}", text)
def p(text=""): return blk("paragraph", text)
def bullet(text): return blk("bulleted_list_item", text)
def num(text): return blk("numbered_list_item", text)
def todo(text): return blk("to_do", text, checked=False)
def callout(text, emoji="💡"): return blk("callout", text, icon={"type": "emoji", "emoji": emoji})
def link(pid): return {"object": "block", "type": "link_to_page", "link_to_page": {"type": "page_id", "page_id": pid}}
def cols(*columns):
    return {"object": "block", "type": "column_list", "column_list": {"children": [
        {"object": "block", "type": "column", "column": {"children": c}} for c in columns]}}


def page(key, parent, title, icon, children=None):
    if key in I:
        return I[key]
    r = api("POST", "/pages", {"parent": {"page_id": parent}, "icon": {"type": "emoji", "emoji": icon},
                               "properties": {"title": {"title": rt(title)}}, "children": children or []})
    I[key] = r["id"]; save_ids(I)
    return r["id"]


def db(key, parent, title, icon, props):
    if key in I:
        return I[key]
    r = api("POST", "/databases", {"parent": {"page_id": parent}, "icon": {"type": "emoji", "emoji": icon},
                                   "title": rt(title), "is_inline": True, "properties": props})
    I[key] = r["id"]; save_ids(I)
    return r["id"]


def relate(a, prop, b, back):
    """dual relation a.prop <-> b.back"""
    if f"rel:{a}:{prop}" in I:
        return
    r = api("PATCH", f"/databases/{I[a]}", {"properties": {prop: {"relation": {
        "database_id": I[b], "type": "dual_property", "dual_property": {}}}}})
    synced = r["properties"][prop]["relation"]["dual_property"]["synced_property_name"]
    api("PATCH", f"/databases/{I[b]}", {"properties": {synced: {"name": back}}})
    I[f"rel:{a}:{prop}"] = back; save_ids(I)


def addprop(key, props):
    if f"props:{key}:{','.join(props)}" in I:
        return
    api("PATCH", f"/databases/{I[key]}", {"properties": props})
    I[f"props:{key}:{','.join(props)}"] = 1; save_ids(I)


def rollup(rel, target, fn):
    return {"rollup": {"relation_property_name": rel, "rollup_property_name": target, "function": fn}}


T = {"title": {}}
TXT = {"rich_text": {}}
D = {"date": {}}
CB = {"checkbox": {}}
N = {"number": {"format": "number"}}
URL = {"url": {}}

# ================= hubs =================
home = PARENT
hub = {}
for k, t, e in [("act", "실행 (Inbox·Task·Project·Goal)", "🎯"), ("log", "기록 (Journal·Life Wheel·Mandalart)", "📝"),
                ("sec", "보안 공부 (TOSS 로드맵·CTF)", "🛡️"), ("study", "학습 (대학·자격증·세션)", "📚"),
                ("job", "취업 (지원·STAR·SWOT)", "💼"), ("pkm", "지식 (PARA·제텔카스텐)", "🧠"),
                ("guide", "가이드 (단축키·연동·Claude)", "⌨️")]:
    hub[k] = page("hub:" + k, home, t, e)

# ================= 실행 =================
db("goals", hub["act"], "Goals (OKR)", "🏆", {
    "Objective": T, "Area": sel(*AREAS), "Quarter": sel("2026 Q4", "2027 Q1", "2027 Q2", "2027 Q3"),
    "Status": sel("예정", "진행 중", "완료", "보류"), "KR 1": TXT, "KR 2": TXT, "KR 3": TXT})
db("projects", hub["act"], "Projects", "🚀", {
    "Name": T, "Area": sel(*AREAS), "Status": sel("예정", "진행 중", "완료", "보류"),
    "Period": D, "Objective (SMART)": TXT})
db("tasks", hub["act"], "Tasks", "✅", {
    "Name": T, "Done": CB, "Status": sel("대기", "진행 중", "완료"), "Area": sel(*AREAS), "Due": D,
    "Type": sel("Daily", "Periodic", "Strategic", "One-time"),
    "중요": sel("높음", "낮음"), "긴급": sel("높음", "낮음"),
    "Quadrant": {"formula": {"expression":
        'if(prop("중요") == "높음" and prop("긴급") == "높음", "Q1 🔥 중요·긴급", '
        'if(prop("중요") == "높음", "Q2 🌱 중요·비긴급", '
        'if(prop("긴급") == "높음", "Q3 ⚡ 비중요·긴급", "Q4 💤 비중요·비긴급")))'}}})
db("inbox", hub["act"], "Inbox (통합 메모)", "📥", {
    "Memo": T, "Type": sel("To-do", "아이디어", "스티커", "지식"), "Pin": CB,
    "Status": sel("미처리", "처리 중", "완료"), "Created": {"created_time": {}}})
relate("tasks", "Project", "projects", "Tasks")
relate("projects", "Goal", "goals", "Projects")
addprop("projects", {"Progress": rollup("Tasks", "Done", "percent_checked"),
                     "Task 수": rollup("Tasks", "Name", "count")})
addprop("goals", {"Project 수": rollup("Projects", "Name", "count")})

# ================= 기록 =================
db("journal", hub["log"], "Journal (Daily / Weekly / Monthly)", "📓", {
    "Title": T, "Type": sel("Daily", "Weekly", "Monthly"), "Date": D,
    "기분": sel("😄", "🙂", "😐", "😞", "😫"), "에너지": {"number": {"format": "number"}},
    "만족도": sel("★", "★★", "★★★", "★★★★", "★★★★★"),
    "기상": TXT, "취침": TXT, "공부(h)": N, "GitHub 커밋": N,
    "운동": CB, "물": CB, "독서": CB, "명상": CB, "공부": CB, "코딩": CB, "수면": CB,
    "루틴 점수(%)": {"formula": {"expression":
        'round((' + "+".join(f'if(prop("{x}"),1,0)' for x in ["운동", "물", "독서", "명상", "공부", "코딩", "수면"]) + ')/7*100)'}},
    "Highlight": TXT, "Keep": TXT, "Problem": TXT, "Try": TXT})
db("wheel", hub["log"], "Life Wheel", "🎡", {
    "Area": T, "Score (1-10)": N, "Date": D, "메모": TXT})
if "mandalart" not in I:
    cells = [["" for _ in range(9)] for _ in range(9)]
    areas = ["보안 실력", "학업", "취업", "건강", "재정", "관계", "취미", "마음"]
    pos = [(3, 3), (3, 4), (3, 5), (4, 3), (4, 5), (5, 3), (5, 4), (5, 5)]  # 중앙 3x3 블록의 8칸
    cells[4][4] = "비전"
    for (r, c), a in zip(pos, areas):
        cells[r][c] = a
    rows = [{"object": "block", "type": "table_row", "table_row": {"cells": [rt(x) if x else [] for x in row]}} for row in cells]
    page("mandalart", hub["log"], "Mandalart (9×9)", "🧭", [
        callout("가운데 '비전' → 주변 8영역 → 각 영역을 바깥 3×3 블록으로 펼쳐 총 64개 목표를 채우세요. 비어 있는 칸이 있어도 괜찮아요.", "🧭"),
        {"object": "block", "type": "table", "table": {"table_width": 9, "has_column_header": False,
                                                       "has_row_header": False, "children": rows}}])

# ================= 보안 / TOSS 로드맵 =================
rm = json.load(open(ROADMAP, encoding="utf-8"))
phases = rm["phases"]
db("roadmap", hub["sec"], "TOSS 로드맵", "🗺️", {
    "Unit": T, "Unit ID": TXT,
    "Phase": sel(*[f'{p_["order"]:02d} {p_["title"]}' for p_ in phases]),
    "Window": TXT, "Kind": sel("study", "lab", "project", "research", "review"),
    "Depth": sel("L1", "L2", "L3", "L4", "L5"), "Est hours": N,
    "Status": sel("대기", "진행 중", "완료")})
db("ctf", hub["sec"], "CTF / Lab Log", "🚩", {
    "Challenge": T, "Date": D, "Platform": sel("HTB", "Dreamhack", "picoCTF", "redteam-lab", "기타"),
    "Category": sel("pwn", "web", "rev", "crypto", "forensics", "misc", "cloud"),
    "Result": sel("해결", "부분", "실패"), "Minutes": N, "Writeup": URL, "배운 점": TXT})

addprop("roadmap", {"#": N})
if "roadmap:nowindow" not in I:
    api("PATCH", f"/databases/{I['roadmap']}", {"properties": {"Window": None}}); I["roadmap:nowindow"] = 1; save_ids(I)
ORDER = {u["id"]: n + 1 for n, u in enumerate(u for ph in phases for u in ph["units"])}
if "roadmap:seeded" not in I:
    seeded = set()
    for ph in reversed(phases):
        pname = f'{ph["order"]:02d} {ph["title"]}'
        for u in reversed(ph["units"]):
            g = u.get("guide", {})
            kids = []
            if u.get("modern_note"):
                kids.append(callout(u["modern_note"], "📌"))
            if g.get("order"):
                kids += [h(3, "학습 순서")] + [num(x) for x in g["order"]]
            if g.get("by_hand"):
                kids += [h(3, "직접 해볼 것")] + [todo(x) for x in g["by_hand"]]
            if g.get("by_ai"):
                kids += [h(3, "AI 활용")] + [bullet(x) for x in g["by_ai"]]
            if u.get("evidence"):
                kids += [h(3, "증거(Evidence)"), p(" · ".join(u["evidence"]))]
            depth = (u.get("depth_target") or "")[:2]
            props = {"Unit": {"title": rt(u["title"])}, "Unit ID": {"rich_text": rt(u["id"])},
                     "#": {"number": ORDER[u["id"]]}, "Phase": {"select": {"name": pname}},
                     "Est hours": {"number": u.get("est_hours") or 0}, "Status": {"select": {"name": "대기"}}}
            if u.get("kind") in ("study", "lab", "project", "research", "review"):
                props["Kind"] = {"select": {"name": u["kind"]}}
            if depth in ("L1", "L2", "L3", "L4", "L5"):
                props["Depth"] = {"select": {"name": depth}}
            api("POST", "/pages", {"parent": {"database_id": I["roadmap"]}, "properties": props, "children": kids[:100]})
            seeded.add(u["id"])
    I["roadmap:seeded"] = len(seeded); save_ids(I)

# ================= 학습 =================
db("subjects", hub["study"], "Subjects (과목·목표)", "📘", {
    "Subject": T, "Type": sel("전공", "교양", "자격증", "보안", "외국어", "독서"),
    "Status": sel("예정", "진행 중", "완료"), "Deadline": D, "Goal": TXT})
db("sessions", hub["study"], "Study Sessions", "⏱️", {
    "Session": T, "Date": D, "Minutes": N, "Focus": sel("1", "2", "3", "4", "5"), "Notes": TXT})
relate("sessions", "Subject", "subjects", "Sessions")
relate("sessions", "Roadmap Unit", "roadmap", "Sessions")
addprop("subjects", {"누적(분)": rollup("Sessions", "Minutes", "sum")})
addprop("roadmap", {"누적(분)": rollup("Sessions", "Minutes", "sum")})
addprop("roadmap", {"Progress(%)": {"formula": {"expression":
    'if(prop("Est hours") > 0, min(100, round(prop("누적(분)") / 60 / prop("Est hours") * 100)), 0)'}}})
relate("tasks", "Roadmap Unit", "roadmap", "Tasks")
relate("tasks", "Subject", "subjects", "Tasks")

# ================= 취업 =================
db("apps", hub["job"], "지원 현황", "📮", {
    "Company": T, "Position": TXT, "Status": sel("관심", "지원예정", "서류", "코테", "면접", "합격", "탈락"),
    "Deadline": D, "Interview": D, "Link": URL, "Resume ver": TXT, "Notes": TXT,
    "D-day": {"formula": {"expression":
        'if(empty(prop("Deadline")), "", "D" + format(dateBetween(prop("Deadline"), now(), "days") * -1))'}}})
db("star", hub["job"], "STAR 경험 아카이브", "⭐", {
    "경험": T, "Tag": sel("프로젝트", "CTF", "대외활동", "인턴", "수업", "연구"),
    "Situation": TXT, "Task": TXT, "Action": TXT, "Result": TXT, "Date": D})
if "swot" not in I:
    q = lambda t, e: [h(3, f"{e} {t}"), bullet("")]
    page("swot", hub["job"], "My SWOT", "🧩", [cols(q("Strength", "💪") + q("Opportunity", "🚀"),
                                                    q("Weakness", "🩹") + q("Threat", "⚠️"))])
if "links" not in I:
    page("links", hub["job"], "취업 사이트 모음", "🔗", [
        h(3, "공고"), bullet("원티드 https://www.wanted.co.kr"), bullet("사람인 https://www.saramin.co.kr"),
        bullet("잡코리아 https://www.jobkorea.co.kr"), bullet("캐치 https://www.catch.co.kr"),
        bullet("토스 채용 https://toss.im/career/jobs"), bullet("KISA 인력양성 https://www.kisa.or.kr"),
        h(3, "보안"), bullet("KISA 보안공지 https://knvd.krcert.or.kr"), bullet("Dreamhack https://dreamhack.io"),
        bullet("HackerOne https://hackerone.com/hacktivity"), bullet("Bugcrowd https://bugcrowd.com")])

# ================= 지식 =================
db("pkm", hub["pkm"], "Knowledge (PARA + Zettelkasten)", "🗃️", {
    "Note": T, "PARA": sel("Projects", "Areas", "Resources", "Archives"),
    "ZK 분류": sel("000 자기이해", "100 사고방식", "200 학습·연구", "300 일·생산성", "400 인간관계",
                  "500 건강·생활", "600 돈·경제", "700 기술·도구", "800 창작·표현", "900 세계·미래"),
    "Source": URL, "Tag": {"multi_select": {}}})
if "pkm:self" not in I:
    api("PATCH", f"/databases/{I['pkm']}", {"properties": {"연결 노트": {"relation": {
        "database_id": I["pkm"], "type": "single_property", "single_property": {}}}}})
    I["pkm:self"] = 1; save_ids(I)

print("OK", len(I), "ids; roadmap units:", I.get("roadmap:seeded"))

# ================= 내 사이트 연동 (horyz.io / lab.horyz.io) =================
def bm(url): return {"object": "block", "type": "bookmark", "bookmark": {"url": url}}

db("posts", hub["sec"], "Site Posts (horyz.io 발행 파이프라인)", "✍️", {
    "Title": T, "Site": sel("horyz.io", "lab.horyz.io"),
    "Type": sel("CVE", "Bug Bounty", "CTF Writeup", "Research", "Lab 챌린지", "Tutorial"),
    "Status": sel("아이디어", "초안", "검수", "발행"), "Publish": D, "URL": URL, "Notes": TXT})
relate("posts", "Roadmap Unit", "roadmap", "Posts")
relate("ctf", "Post", "posts", "CTF Logs")
sites = page("sites", home, "My Sites", "🌐", [
    callout("horyz.io = 포트폴리오·블로그 / lab.horyz.io = 레드팀 랩. 발행할 글은 보안 허브의 'Site Posts' DB에서 상태로 관리합니다.", "🌐"),
    bm("https://horyz.io/"), bm("https://lab.horyz.io/")])

# ================= Home =================
if "home:filled" not in I:
    api("PATCH", f"/blocks/{home}/children", {"children": [
        callout("ANH 올인원 — 보안공부 · 대학 · 취업 · 데일리로그 · TOSS 로드맵을 한 곳에서. 위젯은 아래 '위젯' 섹션, 사용법은 ⌨️ 가이드.", "🏠"),
        h(2, "🎯 오늘"), p("(위젯 임베드 자리 — widgets/README 의 embed 단계 실행 후 채워집니다)"),
        h(2, "바로가기"),
        cols([link(hub["act"]), link(hub["log"]), link(hub["study"])],
             [link(hub["sec"]), link(hub["job"]), link(hub["pkm"])],
             [link(sites), link(hub["guide"])]),
        h(2, "🧩 위젯")]})
    I["home:filled"] = 1; save_ids(I)
print("sites OK")

# ================= 가이드 =================
if "guide:filled" not in I:
    code = lambda t: {"object": "block", "type": "code", "code": {"rich_text": rt(t), "language": "shell"}}
    api("PATCH", f"/blocks/{hub['guide']}/children", {"children": [
        h(2, "⌨️ Notion 기본 단축키"),
        bullet("Ctrl+K 검색 · Ctrl+P 빠른 이동 · Ctrl+N 새 페이지 · Ctrl+[ / ] 뒤로·앞으로"),
        bullet("Ctrl+Shift+L 다크모드 · Ctrl+\\ 사이드바 · Ctrl+Shift+U 상위 페이지"),
        bullet("/ 블록 삽입 · @ 멘션/날짜(@today) · Ctrl+Shift+↑↓ 블록 이동 · Ctrl+E 코드"),
        bullet("Ctrl+Alt+T 토글 · Ctrl+Shift+1~3 제목 · Ctrl+Shift+4 체크박스 · Ctrl+Shift+9 코드블록"),
        h(2, "🧩 위젯 단축키 (위젯을 클릭해 포커스 후)"),
        bullet("h → horyz.io · l → lab.horyz.io · 포커스 위젯: Space 시작/정지, r 리셋"),
        h(2, "💻 터미널 캡처 (anh CLI)"),
        code('python anh.py memo "아이디어 문장" --type 아이디어 --pin\npython anh.py task "SQLD 과제" --area 대학 --due 2026-10-10 --quad Q1\npython anh.py log "오늘 fd-c-memory 끝"\npython anh.py study fd-c-memory 50     # 로드맵 Unit ID 또는 과목명\npython anh.py post "CVE writeup" --type CVE --site horyz.io'),
        h(2, "🤖 Claude 연동"),
        bullet("Claude Code가 이 폴더에서 `python anh.py ...`를 호출하면 Inbox/Journal/Study에 바로 기록됩니다. 세션 끝에 한 줄 로그: Stop 훅에 `python <경로>/anh.py log \"Claude 세션 종료\"` 추가."),
        bullet("Journal·Roadmap 페이지를 Claude에게 통째로 넘겨 주간 회고(KPT) 초안을 만들게 할 때는 Notion 페이지 링크를 붙여 넣으세요."),
        h(2, "📱 iOS/macOS 단축어 (직접 만들기 5분)"),
        num("단축어 앱 → 새 단축어 → '텍스트 요청' (질문: 메모를 입력하세요)"),
        num("'URL 콘텐츠 가져오기' → POST https://api.notion.com/v1/pages"),
        num("헤더: Authorization = Bearer <NOTION 토큰>, Notion-Version = 2022-06-28, Content-Type = application/json"),
        num("본문(JSON): parent.database_id = Inbox DB id(ids.json의 inbox), properties.Memo.title[0].text.content = 위 텍스트"),
        num("제어센터/액션 버튼/Siri에 추가. 같은 방식으로 Tasks, Journal도 만들 수 있어요."),
        callout("Notion API는 버튼 블록·DB 뷰·DB 템플릿을 만들 수 없어서, '퀵버튼'은 위 CLI/단축어/위젯과 Notion 기본 'New' 버튼으로 대체했습니다. 원하면 Notion에서 DB 템플릿 버튼을 직접 추가하세요.", "⚠️")]})
    I["guide:filled"] = 1; save_ids(I)

# ================= lab.horyz.io 동기화용 스키마 =================
addprop("roadmap", {"복습 예정": D, "복습 회차": N, "완료일": D, "달성 Depth": sel("L1", "L2", "L3", "L4", "L5", "L6"),
                    "Status": sel("대기", "진행 중", "완료", "막힘", "건너뜀")})
addprop("journal", {"Lab 완료": TXT})
db("weekly", hub["study"], "주간 계획 (lab.horyz.io 연동)", "🗓️", {"Week": T, "Hours": N, "Generated": D})
print("lab schema OK")

# ================= 오늘 할 일 자동화 스키마 =================
addprop("tasks", {"Source": sel("수동", "lab 플랜", "루틴"), "Status": sel("대기", "진행 중", "완료", "미완료")})
db("routines", hub["act"], "반복 루틴 (요일마다 오늘 할 일 자동 생성)", "🔁", {
    "Routine": T, "Active": CB, "Days": {"multi_select": {"options": [{"name": d, "color": C[i % 9]} for i, d in enumerate("월화수목금토일")]}},
    "Area": sel(*AREAS), "Notes": TXT})
if "routines:seeded" not in I:
    for name, area, note in [("알바 가기", "생활", "요일을 고르고 Active 체크하면 그 요일마다 오늘 할 일에 자동 생성돼요"),
                              ("글 정리하기", "보안", "요일을 고르고 Active 체크"),
                              ("Journal 작성하기", "생활", "매일이면 월~일 모두 선택")]:
        api("POST", "/pages", {"parent": {"database_id": I["routines"]}, "properties": {
            "Routine": {"title": rt(name)}, "Active": {"checkbox": False}, "Area": {"select": {"name": area}},
            "Notes": {"rich_text": rt(note)}}})
    I["routines:seeded"] = 1; save_ids(I)
print("tasks automation schema OK")
