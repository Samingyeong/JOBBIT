# JOBBIT 개발 기록

단계가 끝날 때마다 위쪽에 추가합니다. 각 항목은 **한 일 / 문제와 해결 / 결정 사항과 이유** 세 부분으로 씁니다.
관련 문서: [로드맵](ROADMAP.md) · [기술 결정](TECH_DECISIONS.md)

---

## 2026-11-12 · 1.5단계 — PR 검증 체계

### 한 일
- `check` 작업에 `npm run lint` 추가: ESLint 9(권장 규칙, `jsx`/`tsx`에만 React·Hooks 규칙) + jscpd 4(50토큰, 중복률 3% 초과 시 실패)
- `rust-lint` 별도 작업 추가: Tauri v2 Linux 의존 패키지 설치 → `cargo fmt --check` → `cargo clippy --locked --all-targets -- -D warnings`
- `.claude/agents/pr-reviewer.md` 읽기 전용 리뷰어 추가, `CLAUDE.md`에 PR 전 리뷰 규칙(`pr-reviewer` + `/code-review`), 개발 기록 규칙, 옵시디언용 문서 규칙 추가
- 이 개발 기록 파일 추가
- 검증: 로컬에서 `npm run check`, `npm run lint`, `cargo fmt --check`, `cargo clippy` 모두 통과. 일부러 중복 파일·미사용 변수·`key` 없는 JSX를 넣었을 때 jscpd·ESLint·React 규칙이 각각 실패하는 것도 확인 후 되돌림

### 문제와 해결
- 기존 코드가 새 검사를 통과하지 못함
  - `web/app.js`의 `safeHref`가 선언만 되고 쓰이지 않아 ESLint `no-unused-vars` 오류 → 삭제(동작 변화 없음)
  - `src-tauri/src/main.rs`, `build.rs`가 한 줄로 압축돼 `cargo fmt --check` 실패 → `cargo fmt` 적용(줄바꿈만 바뀜)
- PR 전 `/code-review`가 이 단계 변경에서 5건을 지적해 모두 수정
  - 로드맵에서 CI를 아직 돌리지 않은 `[CI]` 항목을 완료로 표시함 → CI 통과 후 체크하도록 되돌림
  - 리뷰용 diff 명령(`main...HEAD`)이 커밋 전 변경을 빠뜨림 → `git add -A` 후 base 대비 `--cached` diff로 변경
  - jscpd가 워크플로 YAML까지 검사해 CI 설정 반복만으로 기준을 넘을 수 있음 → `.github` 제외
  - `windows-build`가 `check`에 묶여 lint 실패 시 설치 파일이 안 만들어짐 → 의존 관계 제거
  - 새로 만든 서브에이전트는 다음 세션부터 등록되어 이번 세션에서 `pr-reviewer`를 바로 실행할 수 없음 → 읽기 전용 `Explore` 에이전트에 정의 파일을 따르게 하는 대체 방법을 `CLAUDE.md`에 명시
- `pr-reviewer`(대체 실행)가 지적: 로드맵 `[CI]` 표기 설명에 `rust-lint` 누락 → 추가. `web/styles.css`가 jscpd 결과에 없음 → 확인해 보니 CSS가 2줄로 압축돼 있어 jscpd 기본값(5줄 미만 파일 제외)에 걸려 빠지고 있었음 → `minLines: 1`로 바꿔 토큰 기준(50토큰)으로만 판단, CSS 포함 후에도 중복 0%
- 1단계 PR이 아직 병합 전(Windows 수동 확인 대기)이라 `main`에서 시작할 수 없음 → `step-1/docs-ci` 위에 쌓은 PR로 올리고, 1단계 병합 후 base를 `main`으로 변경

### 결정 사항과 이유
- **Rust 검사를 별도 작업으로 분리**: clippy는 Tauri Linux 패키지 설치와 컴파일로 몇 분 걸림. `check`와 동시에 돌려 데이터·lint 결과를 먼저 받기 위해(목표 1분 안팎, 실측은 PR CI 후 기록)
- **jscpd 3% / 50토큰**: 현재 중복 0%. 작은 코드베이스에서 우연한 겹침은 허용하고 복사·붙여넣기는 잡는 수준. 생성 파일(166일 JSON, lock, 빌드 결과물, 아이콘)은 검사 제외
- **React 규칙은 `jsx`/`tsx`에만 적용**: 지금 프론트엔드는 순수 JS라 적용 대상이 없음. React를 도입하면 설정 변경 없이 바로 적용됨
- **`pr-reviewer`에 Bash를 주지 않음**: Bash가 있으면 명령으로 파일을 바꿀 수 있어 읽기 전용이 보장되지 않음. 변경 내용은 `.review/`에 파일로 넘김
- **메모리 플러그인 대신 이 파일 사용**: 클라우드 세션은 끝나면 컨테이너가 지워져 로컬 메모리가 남지 않음. 저장소에 기록해야 다음 세션과 사람이 모두 읽을 수 있음

---

## 2026-11-12 · 1단계 — 문서 정리 + Windows CI

### 한 일
- v0.1 스타터를 저장소에 처음 올림(파일 29개, `npm run check` 통과 확인 후)
- `AGENTS.md`를 `CLAUDE.md`로 통합, `CODEX_HANDOFF.md`를 [로드맵](ROADMAP.md)으로 재작성
- `package-lock.json`, `src-tauri/Cargo.lock` 커밋
- GitHub Actions: `check`(main 푸시·PR·수동), `windows-build`(PR·수동만, Rust 캐시, 설치 파일 artifact)
- 검증: PR CI에서 `check` 성공, `windows-build` 성공(`.msi`와 `JOBBIT_0.1.0_x64-setup.exe` 생성). 설치 파일의 실제 실행은 사용자가 Windows에서 확인 예정

### 문제와 해결
- 첫 Windows 빌드가 `Couldn't find a .ico icon`으로 실패. 컴파일은 성공했고 설치 파일 생성 단계에서 실패 → `tauri.conf.json`의 `bundle.icon`에 기존 아이콘 경로를 명시해 해결
- Node 20 지원 종료 경고 → `actions/checkout`, `actions/setup-node`를 v5로 올림

### 결정 사항과 이유
- **Windows 빌드는 PR·수동 실행 때만**: 병합 전에 확인하면 충분하고, main 푸시마다 4분 이상 Windows 빌드를 돌릴 필요가 없음
- **아이콘은 스타터의 임시 아이콘 유지**: 캐릭터 이미지가 준비되면 `npx tauri icon`으로 교체
- **코드 서명 없음**: 지금은 개인 확인용. SmartScreen 경고는 2단계 체크리스트에 기록하고, 정식 배포 전에 서명을 검토
