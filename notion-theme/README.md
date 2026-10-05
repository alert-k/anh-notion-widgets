# ANH Notion Theme (horyz.io look)

Notion 다크 테마를 horyz.io 톤(거의 검정, 크림 글자, 헤어라인, 연두 포인트, Space Grotesk / Manrope / JetBrains Mono)으로 바꾸는 크롬 확장.
내 브라우저에서만 적용되고, 데이터를 읽거나 보내지 않는다 (CSS만 주입).

## 설치 (1분)
1. 크롬 주소창에 `chrome://extensions` → 우측 상단 **개발자 모드** 켜기
2. **압축해제된 확장 프로그램을 로드합니다** → 이 `notion-theme` 폴더 선택
3. Notion 탭 새로고침 (Notion은 다크 모드여야 함: 설정 → 모양 → 다크)

끄기: `chrome://extensions` 에서 토글. 삭제: 제거 버튼.

## 한계
- 크롬(엣지·브레이브 포함)에서만. Notion 데스크톱 앱, 모바일 앱에는 적용 안 됨.
- Notion이 화면 구조를 바꾸면 일부 셀렉터(둥근 모서리 등)가 안 먹을 수 있음. 색은 Notion 자체 디자인 토큰(`--c-*`)을 덮어써서 안정적.
- 한글은 Pretendard → Noto Sans KR → 맑은 고딕 순으로 시스템 글꼴 사용 (영문/숫자만 사이트 글꼴 내장).
- 라이트 테마는 건드리지 않음.
