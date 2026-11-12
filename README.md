# JOBBIT Starter — 취준 데스크톱 메이트 (v0.1)

실제 2027 상반기 취준 마스터플랜 `.xlsx`에서 **166일 과제**와 **32개 역량 평가 기준**을 가져온 오프라인 우선 투두 앱입니다.

## 지금 동작하는 기능
- 오늘(또는 가장 가까운 날짜)의 미션 표시
- 전날/다음날 보기
- 매일 세부 체크리스트, 결과물/완료 기준, 증거 링크와 메모
- 완료/미완료 표시, 직무별 진도와 주간 진도
- 로컬 자동 저장 (`localStorage`) 및 JSON 백업/복구
- 토끼 캐릭터와 퀘스트 진행 말풍선

## 실행 (Windows 기준)
1. Node.js 22+ 설치
2. 압축 해제한 폴더에서 터미널 열기
3. `npm run web` → `http://localhost:1420` 열기 (의존성 설치 불필요)

### Tauri 데스크톱 빌드 (실제 Windows에서 검증 필요)
1. [Tauri v2 사전요건](https://v2.tauri.app/start/prerequisites/)에 따라 Rust, Windows C++ Build Tools, WebView2 설치
2. `npm install`
3. `npm run desktop` — 개발 실행
4. `npm run build:desktop` — Windows 실행파일 빌드

Windows 빌드는 GitHub Actions의 `windows-build` 작업이 PR과 수동 실행(Actions → CI → Run workflow) 때 검증하고, 설치 파일을 artifact로 올립니다. 코드 서명이 없어 설치 시 SmartScreen 경고가 뜹니다. 투명 창·클릭 통과·드래그 같은 화면 동작은 CI로 확인할 수 없어 [`docs/ROADMAP.md`](docs/ROADMAP.md)의 수동 체크리스트로 확인합니다.

## 데이터 구조
- `web/data/plan.json`: 원본 Excel `일별계획` 시트의 166일
- `web/data/competencies.json`: `역량평가기준` 32개
- 브라우저 저장 키 `jobbit-progress-v1`
- 출처 `.xlsx` 수정 후: `python scripts/export_plan.py <원본.xlsx>` (artifact_tool 필요)

## 남은 기능
단계별 계획과 완료 기준은 [`docs/ROADMAP.md`](docs/ROADMAP.md)에 있습니다.

- [ ] 작은 독립 펫 오버레이 창, 클릭 통과 및 드래그
- [ ] SQLite 기반 상태 저장과 백업 마이그레이션
- [ ] OS 부팅시 자동 시작, 알림 예약/끄기
- [ ] GitHub OAuth 및 PR/테스트 증거 연결
- [ ] Skill/Agent 호출과 평가 권한 검증
- [ ] Playwright E2E
- [x] Tauri Windows 빌드 CI (설치 파일 수동 검증은 2단계)

## 안전 원칙
- AI가 완료를 자동 판정하거나 일정을 수정하지 않음
- GitHub 등 외부 권한 연동 전 사용자 승인
- 사용자 데이터/프롬프트를 원격에 보내지 않음
- 서드파티 플러그인은 출처, 권한, 라이선스 검토 후 설치

## 출처 및 참고
- WindowPet (MIT): https://github.com/SeakMengs/WindowPet (코드를 복제한 것은 아님)
- Tauri 2: https://v2.tauri.app/
- Claude Plugin Marketplace: https://claude.com/marketplace/plugins
