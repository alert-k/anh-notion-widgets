// shared helpers: data loading (?demo for design preview), site hotkeys, icons
const SITES = { h: "https://horyz.io/", l: "https://lab.horyz.io/" };
addEventListener("keydown", e => {
  if (e.target.tagName === "TEXTAREA" || e.metaKey || e.ctrlKey || e.altKey) return;
  const u = SITES[e.key]; if (u) open(u, "_blank", "noopener");
});
const pct = (a, b) => b ? Math.round(a / b * 100) : 0;
const iso = d => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
const STAR = '<polygon points="12,2 14.9,8.6 22,9.3 16.6,14 18.2,21 12,17.3 5.8,21 7.4,14 2,9.3 9.1,8.6"/>';
const ICON = {
  flame: '<path d="M12 3s5 4.6 5 9.4A5 5 0 0 1 7 12.4C7 10.6 8 9.4 9 8.4c0 1.8.8 2.8 2 3 0-3-1-5.600 1-8.400z"/>',
  book: '<path d="M4 5.500A2.500 2.500 0 0 1 6.500 3H20v15H6.500A2.500 2.500 0 0 0 4 20.500z"/><path d="M4 20.500A2.500 2.500 0 0 1 6.500 18H20v3H6.500A2.500 2.500 0 0 1 4 20.500z"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="m8.500 12.200 2.400 2.400 4.600-5"/>',
};
const ico = n => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${ICON[n]}</svg>`;
function demo() {
  const t = new Date(), d = n => { const x = new Date(t); x.setDate(x.getDate() - n); return iso(x); };
  return {
    updated: t.toISOString().slice(0, 16), today: iso(t), streak: 6, today_score: 71, study_week_min: 640, tasks_open: 9,
    roadmap: [{ phase: "00 Foundation", total: 13, done: 5, est: 280, min: 3300 }, { phase: "01 System", total: 8, done: 2, est: 320, min: 1800 }, { phase: "02 Web", total: 7, done: 0, est: 275, min: 0 }],
    apps: { 관심: 2, 서류: 1 },
    study_days: [90, 120, 0, 60, 150, 100, 120].map((m, i) => ({ d: d(6 - i), m })),
    routine_hist: Array.from({ length: 28 }, (_, i) => ({ d: d(27 - i), s: [null, 20, 45, 60, 85, 100, 70][(i * 5 + 3) % 7] })),
    tasks: [{ t: "과목 등록", due: d(-1), q: "Q1 중요·긴급" }, { t: "STAR 경험 작성", due: d(-3), q: "Q2 중요" }, { t: "이력서 초안", due: d(-6), q: "Q1 중요·긴급" }, { t: "블로그 주제", due: d(0), q: "Q2 중요" }],
  };
}
const load = () => location.search.includes("demo") ? Promise.resolve(demo())
  : fetch("data.json?" + Date.now()).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
