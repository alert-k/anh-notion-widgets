"""Starter content so DBs aren't empty. Idempotent via ids.json flag. Titles marked (예시) are placeholders to rename."""
import json, os
from datetime import datetime, timedelta, timezone
from lib import api, ids, rt, save_ids, query_all, title_of
I = ids()
if "seeded:starter" in I: raise SystemExit("already seeded")
today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
T = lambda s: {"title": rt(s)}; X = lambda s: {"rich_text": rt(s)}; S = lambda s: {"select": {"name": s}}
def mk(db, props): return api("POST", "/pages", {"parent": {"database_id": I[db]}, "properties": props})["id"]

g1 = mk("goals", {"Objective": T("TOSS 보안 직무 준비"), "Area": S("취업"), "Quarter": S("2026 Q4"), "Status": S("진행 중"),
    "KR 1": X("TOSS 여정 Phase 00–01 완료"), "KR 2": X("horyz.io 글 4편 발행"), "KR 3": X("지원서 3곳 제출")})
g2 = mk("goals", {"Objective": T("이번 학기 학업 유지"), "Area": S("대학"), "Quarter": S("2026 Q4"), "Status": S("예정"),
    "KR 1": X("과목별 목표는 Subjects에 입력")})
pr = {}
for k, name, area, g in [("toss", "TOSS 여정 Phase 00–01", "토스로드맵", g1), ("blog", "horyz.io 글 발행", "보안", g1),
                         ("lab", "redteam-lab 완성도 높이기", "보안", g1), ("job", "취업 서류 준비", "취업", g1)]:
    pr[k] = mk("projects", {"Name": T(name), "Area": S(area), "Status": S("진행 중"), "Goal": {"relation": [{"id": g}]}})

units = {}
for p in query_all(I["roadmap"]):
    units[p["properties"]["#"]["number"]] = p
first = [units[n] for n in (1, 2, 3)]
for u in first:
    mk("tasks", {"Name": T(title_of(u) + " — 학습 시작"), "Status": S("대기"), "Area": S("토스로드맵"), "Type": S("Periodic"),
                 "중요": S("높음"), "긴급": S("낮음"), "Project": {"relation": [{"id": pr["toss"]}]}, "Roadmap Unit": {"relation": [{"id": u["id"]}]}})
for name, area, typ, pj, imp, urg in [
    ("이력서·경력기술서 초안 작성", "취업", "Strategic", "job", "높음", "높음"),
    ("STAR 경험 3개 작성", "취업", "Strategic", "job", "높음", "낮음"),
    ("horyz.io 첫 글 주제 정리", "보안", "One-time", "blog", "높음", "낮음"),
    ("lab.horyz.io 챌린지 풀이 정리", "보안", "Periodic", "lab", "낮음", "낮음"),
    ("이번 학기 과목을 Subjects에 등록", "대학", "One-time", None, "높음", "높음")]:
    p = {"Name": T(name), "Status": S("대기"), "Area": S(area), "Type": S(typ), "중요": S(imp), "긴급": S(urg)}
    if pj: p["Project"] = {"relation": [{"id": pr[pj]}]}
    mk("tasks", p)

phases = sorted({p["properties"]["Phase"]["select"]["name"] for p in units.values()})
for ph in phases:
    mk("subjects", {"Subject": T("TOSS · " + ph), "Type": S("보안"), "Status": S("예정")})
for n in ("(예시) 전공 과목 1", "(예시) 전공 과목 2"):
    mk("subjects", {"Subject": T(n), "Type": S("전공"), "Status": S("진행 중"), "Goal": X("이름·목표를 바꿔서 사용")})

mk("apps", {"Company": T("토스 (Toss)"), "Position": X("보안 직무 — 공고 확인 후 입력"), "Status": S("관심"),
            "Link": {"url": "https://toss.im/career/jobs"}, "Notes": X("공고가 열리면 Deadline·Resume ver 입력")})
mk("star", {"경험": T("redteam-lab 구축·운영 (초안)"), "Tag": S("프로젝트"),
            "Situation": X("레드팀 학습 환경을 직접 만들어 공부와 공개를 병행"), "Task": X("챌린지·로드맵·학습 콘텐츠를 갖춘 랩 구축"),
            "Action": X("API 서버, 프론트, 배포, 콘텐츠 작성을 직접 수행 — 세부 내용 보강 필요"), "Result": X("lab.horyz.io 로 공개 운영 — 수치 보강 필요"),
            "Date": {"date": {"start": today}}})
for a in ["보안 실력", "학업", "취업", "건강", "재정", "관계", "취미", "마음"]:
    mk("wheel", {"Area": T(a), "Score (1-10)": {"number": 5}, "Date": {"date": {"start": today}}, "메모": X("지금 점수를 1~10으로 바꿔 보세요")})
for t, typ, pin in [("📌 Inbox는 anh CLI·단축어·위젯으로 채워져요", "To-do", True),
                    ("lab.horyz.io 진행도 연동: GitHub Secret LAB_TOKEN 추가 필요", "To-do", True)]:
    mk("inbox", {"Memo": T(t), "Type": S(typ), "Pin": {"checkbox": pin}, "Status": S("미처리")})
for z in ["000 자기이해", "100 사고방식", "200 학습·연구", "300 일·생산성", "400 인간관계", "500 건강·생활", "600 돈·경제", "700 기술·도구", "800 창작·표현", "900 세계·미래"]:
    mk("pkm", {"Note": T(z + " — 인덱스"), "ZK 분류": S(z), "PARA": S("Areas")})
for n, par in [("TOSS 여정", "Projects"), ("보안 (Security)", "Areas"), ("horyz.io 운영", "Projects")]:
    mk("pkm", {"Note": T(n), "PARA": S(par)})
mk("posts", {"Title": T("redteam-lab 회고"), "Site": S("horyz.io"), "Type": S("Research"), "Status": S("아이디어")})
mk("posts", {"Title": T("Lab 챌린지 풀이 시리즈"), "Site": S("lab.horyz.io"), "Type": S("Lab 챌린지"), "Status": S("아이디어")})
I["seeded:starter"] = 1; save_ids(I); print("seeded")
