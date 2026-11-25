# Experience Pet v4 — 짱구 데스크톱 경험 기록 도우미

Windows 10/11 · Python 3.11~3.12 · Obsidian Vault · ChatGPT 데스크톱 앱 (별도 OpenAI API 키 불필요)

## v4에서 바뀐 내용

- 보내준 **16컷 짱구·흰둥이 모션 스프라이트**로 재생: 걷기, 기어가기, 쉬기, 잠자기, 점프, 착지, 창 위쪽 매달리기, 흰둥이와 달리기, `부리부리~` 말풍선.
- **활성 창의 테두리 좌표**를 이용해 Chrome, Notion 등의 프로그램 상단에 점프해 매달리는 *연출*. 웹페이지 HTML 탭 요소나 헤더 자체를 인식하는 기능은 아님.
- Windows에서는 `UpdateLayeredWindow` 기반의 **픽셀 단위 알파 투명 렌더링**을 우선 사용해 녹색 투명 키와 테두리가 보이지 않도록 처리. 렌더러가 실패하면 자홍색 컬러키 폴백으로 동작.
- 메모지형 기록창: 사용자가 준 초록 원·빨간 삼각형·노란 사각형 패턴, 크림색 종이, 파스텔 탭과 버튼, 설치된 둥근 한국어 글꼴 우선 사용.
- 짱구 얼굴 아이콘(`app/assets/shinchan_icon.ico`)을 기록창과 빌드 결과 EXE에 사용.
- 원본 입력 후 0.85초에 Obsidian `03 Daily Logs` 자동 저장. 최종 경험 노트는 미리보기·수정·승인 후 **새 파일** 생성. 기존 노트를 덮어쓰지 않음.

## AI 대화 연결 방식 — 정확한 한계

**이 프로그램은 OpenAI API를 쓰지 않습니다.** ChatGPT 데스크톱에 로그인한 후에도 외부 짱구 창에서 ChatGPT 응답을 자동으로 수신할 수는 없습니다. 공식 양방향 메시징 인터페이스가 없는 상태에서 UI 화면 크롤링이나 계정 쿠키 재사용은 하지 않습니다.

1. 짱구 클릭 → 기록창에서 처음 겪은 상황을 작성. 원본은 옵시디언에 자동 저장.
2. **ChatGPT에서 대화하기** 클릭 → ChatGPT 데스크톱의 `codex://new` **Codex 로컬 채팅**에 경험 인터뷰 지침을 미리 입력. 이 딥링크는 자동 전송이 아니므로 **Enter로 보내야** 함.
3. GPT가 실제 대화창에서 3~5개의 꼬리질문을 한 번에 하나씩 하고, 답을 들은 뒤 경험을 Markdown으로 정리.
4. **Experience Pet 로컬 MCP 플러그인이 연결되고 쓰기 권한이 있는 경우**, ChatGPT/Codex에서 미리보기를 보여주고 사용자가 저장을 승인하면 모델이 `save_experience_note`를 호출해 Vault에 직접 저장할 수 있음. 도구 호출의 성공 결과가 있어야 완료로 판단.
5. 플러그인을 사용할 수 없으면 ChatGPT 정리본 복사 → 짱구 기록창 `완성 노트` → 붙여넣기 → 검토 후 저장. 최종 저장은 이 경우에도 앱에서 수행.

> `codex://` 링크는 ChatGPT 데스크톱 앱의 **Codex 로컬 채팅**으로 들어갑니다. 일반 Chat 탭의 답변을 짱구 창 안에 자동 표시하는 기능은 제공되지 않습니다. 일반 Chat 탭에서 인터뷰하고 싶다면 버튼으로 복사된 지침을 Chat에 붙여 넣어 사용할 수 있습니다. 단, 로컬 MCP 도구의 사용 가능 여부는 ChatGPT 제품·계정·채팅 모드에 따라 다릅니다.
>
> **짱구 창 안에서 진짜 GPT 답변을 자동으로 주고받는 완전 통합 채팅**은 별도 OpenAI API를 이용한 기능이 필요합니다. 이 버전은 사용자가 선택한 'API 없이 ChatGPT 앱 활용' 조건을 지킵니다.

## Windows 설치

1. 저장소를 내려받으면 `ExperiencePet/`과 `plugins/` 폴더가 나란히 나옵니다. Obsidian Vault는 로컬에서 선택합니다.
2. Windows용 [Python 3.11~3.12](https://www.python.org/downloads/windows/)을 설치하고 **`ExperiencePet/install_windows.bat`**을 더블클릭합니다.
3. `설정`에서 **이미 사용하고 있는** `Career_Experience_Vault`를 선택합니다. 기존 사용자 데이터를 새 샘플 Vault로 덮어쓰지 마세요.
4. 캐릭터를 클릭해 메모장을 열고 입력하면 자동으로 원본이 저장됩니다.
5. 로컬 MCP 플러그인을 사용하려면 `ExperiencePet/install_chatgpt_plugin_windows.bat`을 실행한 뒤 ChatGPT 데스크톱 앱을 재시작하고 Plugins → My Local Plugins → Experience Pet를 설치·활성화합니다. **실제 계정에서 플러그인 설치·권한이 허용되는지 확인해야 합니다.**
6. 짱구 오른쪽 클릭으로 `설정`, `이동 멈추기/재개`, `잠시 숨기기`, `종료`를 사용할 수 있습니다. `Ctrl+Alt+E`로 메모창을 열 수 있습니다.

## EXE 빌드

`ExperiencePet/build_exe_windows.bat`을 실행하면 Windows PC의 `ExperiencePet/dist/ExperiencePet.exe`가 생성되도록 스크립트를 제공합니다. 미리 컴파일된 EXE는 ZIP에 포함되어 있지 않습니다.

**테스트 범위:** Python 단위 테스트 14개 및 Linux 가상 디스플레이 기록창 렌더링/자동 저장을 확인했습니다. 실제 Windows의 창 알파 렌더링, 창 위 매달리기, 시스템 트레이, 플러그인 설치 및 EXE 빌드는 사용자 PC에서 통합 검증이 필요합니다.

## 안전 및 개인정보

- ChatGPT 앱 로그인·비밀번호·세션 토큰을 Experience Pet이 직접 취급하지 않습니다.
- 원본 기록·프로젝트·경험 노트는 사용자가 지정한 로컬 Vault에 저장합니다.
- 플러그인은 읽기 대상을 `01 Projects`, `02 Experiences` 및 앱 자체 기록 원본으로 제한하고, 최종 경험은 `02 Experiences`에 새 파일로만 저장합니다.
- 회사 고객 정보·계약 내용·사내 비공개 수치 등을 외부 AI에 전송하지 마세요. 필요 시 익명화 후 기록하세요.

### 공식 참고 자료

- [ChatGPT desktop 딥링크](https://learn.chatgpt.com/docs/app/commands)
- [ChatGPT 데스크톱 로컬 플러그인](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt)
- [플러그인 패키징](https://developers.openai.com/plugins/build/plugins)
