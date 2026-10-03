# ANH 올인원 Notion

| 파일 | 역할 |
|---|---|
| `build.py` | Notion에 허브 7개 + DB 17개 생성, TOSS 로드맵 72유닛 시드 (재실행해도 중복 생성 안 함, 진행은 `ids.json`) |
| `art.py` | 일레이나 테마 커버/아이콘 생성·업로드 (영상 프레임은 `art_private/`에만 저장, 커밋 안 됨) |
| `sync.py` | Notion → `docs/data.json`, 오늘 Daily Journal 자동 생성, GitHub 커밋 수 기록 |
| `anh.py` | CLI 캡처: `memo / task / log / study / post` |
| `docs/*.html` | 위젯 3종 (dash, cal, focus) — GitHub Pages로 호스팅 후 Notion `/embed` |
| `.github/workflows/sync.yml` | 30분마다 sync (Secrets: `NOTION`, `IDS_JSON`) |

실행: `.env`에 `NOTION=<토큰>` → `python build.py` → `python art.py` → `python sync.py`.
공개 data.json에는 취업(Area=취업) Task 제목·회사명·메모 본문을 넣지 않습니다.
