# JOBBIT 로드맵

관련 문서: [개발 기록](DEVLOG.md) · [기술 결정](TECH_DECISIONS.md)

단계마다 **계획 제시 → 사용자 승인 → 구현 → PR + CI 검증** 순서로 진행합니다.
기존 앱을 처음부터 다시 쓰지 않습니다. 166일 계획, 완료 기록, 메모, 백업/복원, 오프라인 우선 동작은 모든 단계에서 유지합니다.

검증 표기:
- **[로컬]** Linux 개발 환경에서 직접 실행해 확인
- **[CI]** GitHub Actions(`check` / `rust-lint` / `windows-build`)로 확인
- **[수동]** 실제 Windows PC에서 사람이 직접 확인해야 함 (CI로 대체 불가)

---

## 1단계 — 문서 정리 + Windows CI
브랜치: `step-1/docs-ci`

- [x] `AGENTS.md`를 `CLAUDE.md`로 통합, Codex 분담 내용 제거
- [x] `CODEX_HANDOFF.md`를 이 로드맵으로 정리
- [x] `package-lock.json`, `src-tauri/Cargo.lock` 커밋
- [x] `check` 작업: push(main)·PR·수동 실행 시 `npm run check` **[CI]**
- [x] `windows-build` 작업: PR·수동 실행 시에만 `tauri build`, Rust 캐시 사용, 설치 파일을 artifact로 업로드 **[CI]**

## 1.5단계 — PR 검증 체계
브랜치: `step-1.5/pr-checks`

`[CI]` 항목은 PR의 CI가 통과한 뒤에 체크합니다.

- [ ] `check` 작업에 `npm run lint` 추가: ESLint(권장 규칙 + `jsx`/`tsx` React 규칙) + jscpd **[로컬][CI]**
  - jscpd: 50토큰 이상 겹침을 중복으로 보고, 중복률 **3% 초과 시 실패**
  - 제외: `web/data/`(166일 JSON 등), lock 파일, `src-tauri/target`·`gen`, 아이콘, `node_modules`
- [ ] `rust-lint` 별도 작업(ubuntu): Tauri Linux 의존 패키지 설치 → `cargo fmt --check`, `cargo clippy -D warnings` **[CI]**
- [x] 기존 코드 정리: `cargo fmt` 적용, 쓰이지 않는 `safeHref` 제거 (동작 변화 없음)
- [x] `.claude/agents/pr-reviewer.md`: 읽기 전용(Read/Grep/Glob) 리뷰 서브에이전트, "반드시 수정 / 권장 / 참고" 보고
- [x] `CLAUDE.md`: PR 전 `pr-reviewer`와 `/code-review`를 둘 다 실행하고 결과를 PR 본문에 첨부. "반드시 수정"(또는 `/code-review`의 버그 지적)이 남으면 PR 금지, 사용자가 명시적으로 승인한 경우에만 사유를 적고 예외
- [x] [개발 기록](DEVLOG.md) 추가, 단계가 끝날 때마다 한 일 / 문제와 해결 / 결정 사항과 이유를 기록하는 규칙
- [x] `docs/` 문서는 옵시디언 볼트로 열 수 있게 일반 마크다운 상대 링크만 사용(`[[위키링크]]` 금지), `.obsidian/`은 커밋하지 않음

## 2단계 — 데스크톱 펫 오버레이 + TODO 패널 분리
목표: Tauri 2로 **창 두 개**를 분리합니다. 하나는 항상 위에 떠 있는 작고 투명한 펫 창이고, 다른 하나는 펫을 클릭하면 열리는 일반 TODO/대시보드 패널입니다.

구현 원칙:
- 클릭 통과·투명 창은 공식 Tauri 문서와 명시적 capability 권한으로 구현합니다. API를 추측해서 쓰지 않습니다.
- 현재 localStorage 스키마(`jobbit-progress-v1`)와 호환을 유지합니다. 바꿔야 하면 문서화된 마이그레이션을 둡니다.
- 이동, 저장, HTML 이스케이프, 완료 로직 테스트를 추가합니다.

완료 기준:
- [ ] 166일 데이터 보존 (`npm run check`) **[로컬][CI]**
- [ ] 웹 동작 테스트(이동·저장·이스케이프·완료) 통과 **[로컬][CI]**
- [ ] Windows 설치 파일 빌드 성공 **[CI]**
- [ ] CI artifact에서 설치 파일 다운로드 후 설치 가능 **[수동]**
  - ⚠️ 코드 서명이 안 된 설치 파일이라 Windows SmartScreen 경고("Windows의 PC 보호")가 뜹니다. **추가 정보 → 실행**으로 진행하세요. 브라우저가 다운로드를 경고할 수도 있습니다. 정식 배포 전에는 코드 서명을 별도로 검토해야 합니다.
- [ ] 투명 펫 창이 다른 앱 위에 표시됨 **[수동]**
- [ ] 펫을 화면 어디로든 드래그할 수 있음 **[수동]**
- [ ] 펫을 클릭하면 오늘의 할 일 패널이 열림 **[수동]**
- [ ] 패널을 닫아도 펫은 종료되지 않음 **[수동]**
- [ ] 펫 바깥 영역의 클릭을 가로채지 않음 **[수동]**
- [ ] 항상 위 표시를 끌 수 있음 **[수동]**
- [ ] 재시작 후 체크 상태·메모·증거 링크 유지 **[수동]**
- [ ] AI 없이 TODO 기능이 모두 동작함 **[수동]**

## 3단계 — 로컬 저장소와 알림
- [ ] SQLite 저장소(공식 Tauri 플러그인) + localStorage에서 1회 이관 + 스키마 버전 관리
- [ ] OS 알림 설정(예약/끄기), 부팅 시 자동 시작(선택)
- [ ] 되돌릴 수 있는 일정 편집 이력

## 4단계 — GitHub 증거 연동
- [ ] 사용자의 명시적 동의와 최소 권한으로 GitHub 연결
- [ ] PR·커밋·테스트 결과를 증거 링크로 첨부 (자동 완료 처리는 하지 않음)

## 5단계 — Skill 기반 AI 기능 (opt-in)
- [ ] `daily-planner`, `task-evaluator`, `interview-simulator`, `weekly-retrospective`를 사용자가 직접 켜는 기능으로 연동
- [ ] 평가 세트, 실행 로그, 비용 상한
- [ ] AI 결과로 완료 상태나 일정을 자동으로 바꾸지 않음

---

## 개발 보조 도구 (Claude Code 플러그인, 필요한 것만)
`frontend-design`, `superpowers`, `context7`, `playwright`, `github`. 설치 전에 출처, 권한, 라이선스를 확인합니다.
