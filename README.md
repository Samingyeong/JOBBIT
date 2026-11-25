# JOBBIT · Experience Pet

화면 위의 펫을 눌러 오늘 한 일을 기록하고, ChatGPT의 꼬리질문으로 경험을 되짚은 뒤 Obsidian에 자소서 소재로 남기는 Windows 앱입니다. 기록과 정리를 한 번에 하기 어려운 날에는 메모만 남겨 두고 나중에 이어서 정리할 수 있습니다.

## Windows에서 시작하기

1. Windows 10 또는 11에 Python 3.11~3.12와 Obsidian을 설치합니다. Codex에서 경험 인터뷰를 하려면 ChatGPT 데스크톱 앱도 설치합니다.
2. 이 저장소를 내려받고 [`ExperiencePet/install_windows.bat`](ExperiencePet/install_windows.bat)을 실행합니다. 스크립트가 가상 환경을 만들고, 의존성을 설치하고, 테스트를 실행한 뒤 펫을 띄웁니다.
3. 펫을 우클릭해 **설정**에서 사용할 Obsidian Vault 폴더를 선택합니다. 다음 실행부터는 [`ExperiencePet/run_windows.bat`](ExperiencePet/run_windows.bat)을 사용합니다.
4. 펫을 클릭하거나 `Ctrl+Alt+E`를 눌러 기록창을 엽니다.

## 경험 하나를 기록하는 흐름

1. **오늘 이야기**에서 경험을 한두 문장으로 적습니다. 관련 프로젝트가 있다면 태그를 선택합니다. Vault가 연결되어 있으면 원본 메모는 입력을 멈춘 뒤 약 1초 후에 자동 저장됩니다.
2. **ChatGPT에서 대화하기**를 누르면 경험 인터뷰 프롬프트를 준비합니다. Codex 채팅에 입력되어 있으면 Enter로 보내고, 클립보드에 복사되었다면 ChatGPT에 붙여넣어 보냅니다. 이어지는 질문에 답하면서 당시 판단, 행동, 검증 결과를 정리합니다.
3. ChatGPT가 정리한 Markdown을 복사해 **완성노트**에서 **정리본 붙여넣기**를 누릅니다. 제목과 내용을 검토한 다음 **Obsidian에 저장**을 눌러 새 노트를 만듭니다.
4. **경험모음**에서는 완성한 노트를 프로젝트별로 찾아보고, **일기달력**에서는 날짜를 눌러 원본 기록을 다시 읽을 수 있습니다.

ChatGPT 답변은 ChatGPT에서 확인하며, OpenAI API 키는 필요하지 않습니다. 선택 사항인 로컬 MCP 플러그인을 연결하면 채팅에서 정리본을 검토하고 저장을 승인한 뒤 Vault에 바로 저장할 수 있습니다. [플러그인 설치 안내](ExperiencePet/README.md#windows-설치)

## Obsidian 저장 위치

- `03 Daily Logs/` — 자동 저장된 원본 메모
- `02 Experiences/` — 검토하고 승인한 최종 경험 노트
- `01 Projects/` — 프로젝트 태그에 사용할 노트와 연결된 경험 링크

개인 Vault와 기록은 로컬에 저장됩니다. **ChatGPT에서 대화하기**로 준비하는 프롬프트에는 작성한 메모와 관련 노트 일부가 포함될 수 있습니다. GitHub 저장소에는 앱과 플러그인 소스를 제공합니다.

## 개발 및 빌드

앱 소스는 [`ExperiencePet/app/`](ExperiencePet/app), 로컬 MCP 플러그인은 [`plugins/experience-pet/`](plugins/experience-pet)에 있습니다. 의존성을 설치한 환경에서 저장소 루트 기준으로 테스트를 실행합니다.

```powershell
python -m unittest discover -s ExperiencePet/tests
python -m unittest discover -s plugins/experience-pet/server
```

실행 파일이 필요하면 Windows에서 [`ExperiencePet/build_exe_windows.bat`](ExperiencePet/build_exe_windows.bat)을 실행합니다. 결과는 `ExperiencePet/dist/ExperiencePet.exe`에 생성됩니다. [상세 사용 안내](ExperiencePet/README.md)
