# Agent 03 — 매일 업무일지 요약·점검

- 기록일: 2026-10-17
- 상태: 준비 (Mac 스크립트 작성·시험 완료, launchd 미등록, `MODE=shadow`)
- 상위 규칙: 최상단 `AGENTS.md`. 이 문서는 그 규칙을 구체화하며 변경하지 않는다.
- 관련: `Agent 04` 주간 업무지시·주간 요약(`CMBIOPHARM/rnd`의 `agents/AGENT-04-주간업무지시.md`)

## 1. 목적과 책임 범위

대표(박태준)가 매일 저녁 직원 업무일지를 3분 안에 파악하도록 **일일요약·점검 문서**를 만든다.
Agent 03의 역할은 `매일 루틴 업무`로 등록돼 있으며, 이 업무일지 요약·점검이 첫 업무다.

| 대상 | 담당 범위 | 일지 형식 |
|---|---|---|
| 문재훈 주임 | 실험 실행·기록(합성, 슬러리·화장품 제형, 분무건조, 열처리, 체분급, BET·pH/EC·탭밀도, 분석 의뢰) | 날짜별 `일일_업무보고서_YYMMDD_문재훈.docx` |
| 배현민 이사 | 장비 전체·조달·외부 의뢰·업체 소통 | 누적 `업무보고 모음(…).hwpx`, `금일자(M/D)` 단위 |

대상자는 `config/daily_worklog_people.tsv`에서 관리한다. 직원이 늘거나 형식이 바뀌면 이 표만 고친다.

하는 일:

1. **요약**: 사람별 한 일 / 결과·이상·문제 / 내일·이후 계획 / 대표 확인·결정 필요 / 미완료.
2. **점검**: 미작성, 전일 `익일 계획`·`TO DO NEXT` 대비 이행 여부, 날짜·요일 오기, 같은 날짜 중복 기재와 기재본 간 차이, 7일 이내 일정·마감.

평가 문구는 쓰지 않는다. 기록된 사실과 기록의 빈칸만 적는다.

## 2. 실행 조건과 주기

| 작업 | 주기 | 기기 | 등록 |
|---|---|---|---|
| 일일요약·점검 | 월~금 20:30 KST | Mac mini | launchd `com.cmbiopharm.daily-worklog` |

- 직원 일지는 보통 18:00~18:45에 올라온다(2026-10 기준 파일 수정 시각). 20:30은 Drive 동기화 여유를 둔 시각이다.
- 실행 날짜는 `TZ=Asia/Seoul` 기준 당일이다. 놓친 날은 `--date YYYY-MM-DD`로 수동 실행한다. 자동 보충 실행은 하지 않는다.
- 공휴일에도 실행하며, 전원 미작성이면 그 사실만 적은 문서를 만든다.

## 3. 입력 자료와 신뢰할 원본

1. **직원 업무일지 원본(읽기 전용)**: Mac Drive 마운트
   `~/Library/CloudStorage/GoogleDrive-jpark@cmbiopharm.com/공유 드라이브/CMBIOPHARM/업무일지/<이름>/`
   (Drive 폴더 ID: 문재훈 `1uxt0Ga-_-a1FlMMVUbv6mgaG_qu3RDZs`, 배현민 `1sOQEwA-mBHMlXdPJsiqn1CQLn2XkQnyk`)
   - docx: 파일명에 `YYMMDD`가 든 파일을 macOS `textutil`로 읽는다.
   - hwpx: 수정 시각이 최근인 2개 파일의 `Contents/section*.xml`에서 텍스트를 뽑고 `금일자(M/D)` 머리말로 나눈다. 머리말이 앞 문단 끝에 붙은 경우도 이름 위치에서 나눈다.
   - 같은 날짜가 여러 번 기재되면 **마지막 기재본**을 기준으로 하고, 앞 기재본에만 있던 항목은 `점검`에 적는다.
2. **직전 기록**: 최근 7일 안의 가장 가까운 이전 기록. 계획 대비 이행 대조에 쓴다.
3. `업무일지/주간_업무중점/`의 주간 완성본, `rnd` 리포는 이 에이전트의 입력이 아니다(Agent 04 담당).

원본 추출은 결정적 스크립트가 하고, 요약 모델에는 추출 묶음만 넘긴다. 모델은 도구·MCP·네트워크 없이 실행된다.

## 4. 출력과 저장 위치

- 파일명: `YYYY-MM-DD_일일요약.docx` (Drive에서 미리보기·구글 문서 열기 가능)
- `MODE=live`: `공유 드라이브/CMBIOPHARM/업무일지/` 바로 아래. 2026-10-14~16 `일일요약`이 있는 기존 위치다.
- `MODE=shadow`: Mac 로컬 `~/Library/Application Support/CMBIOPHARM/daily-worklog/out/`. Drive에 쓰지 않는다.
- 같은 이름(확장자 무관, 기존 `.gdoc` 포함)이 있으면 덮어쓰지 않고 `_v2`, `_v3`을 붙인다.
- 실행마다 중간 산출물(`bundle.md`, `checks.json`, `input.md`, `summary.md`)은 `~/Library/Application Support/CMBIOPHARM/daily-worklog/runs/<날짜_시각>/`에 남는다. 직원 기록이 담기므로 Git에 넣지 않는다.
- 문서 구성(`scripts/daily_worklog/prompt.md`가 원본): `한눈에` → 사람별 5개 절 → `점검` → `읽은 원본`.

## 5. 사용할 도구와 실행 환경

| 파일 | 역할 |
|---|---|
| `scripts/daily_worklog/run_daily_worklog.sh` | 실행 진입점. 잠금, 로그, 추출 → 요약 → 저장 → 확인 |
| `scripts/daily_worklog/collect_worklogs.py` | 원본 추출, 기계 점검(미작성, 작성일자 요일, 중복 기재) |
| `scripts/daily_worklog/prompt.md` | 요약 규칙과 문서 형식 |
| `scripts/daily_worklog/publish_summary.py` | Markdown → HTML → docx(`textutil`), 버전 붙여 저장, 바이트 비교 확인 |
| `scripts/daily_worklog/install_daily_worklog.sh` | launchd 등록·해제(`--remove`) |
| `config/daily_worklog.conf` | `MODE`, `MODEL`, 원본·저장 경로 |
| `config/daily_worklog_people.tsv` | 대상자 등록부 |

- Mac 기본 도구만 쓴다: `/usr/bin/python3`(3.9, 표준 라이브러리), `textutil`, `plutil`, `osascript`, `perl`(시간 제한).
- 요약: `claude -p --model claude-sonnet-5-5 --tools "" --strict-mcp-config --setting-sources ""`, 10분 제한.
- 등록은 **기본 저장소 `~/orca/agent`의 `main`에서** 한다. worktree 경로로 등록하지 않는다. Agent 00 통합 감시가 `main`을 fast-forward하므로 스크립트 갱신이 자동 반영된다.

```bash
cd ~/orca/agent && git pull --ff-only
bash scripts/daily_worklog/install_daily_worklog.sh          # 등록
bash scripts/daily_worklog/run_daily_worklog.sh --date 2026-10-16 --mode shadow   # 수동 시험
bash scripts/daily_worklog/install_daily_worklog.sh --remove # 해제
```

## 6. 완료 기준과 검증

- 등록부의 모든 사람에 대해 `작성` 또는 `미작성`이 문서에 있다.
- 저장한 파일이 저장 위치에 존재하고 로컬 docx와 바이트가 같다(`publish_summary.py`).
- 로그에 `SAVE <최종 경로>`와 `DONE`이 있다.
- 날짜(요일)는 스크립트·모델 모두 `Asia/Seoul` 실제 달력으로 검산한다.
- 2026-10-17 시험: `--date 2026-10-16 --mode shadow` 정상(문재훈 미작성, 배현민 10/16자 5회 기재 감지, 기재본 차이 기록). docx 변환·`_v2` 증가 확인.

## 7. 로그·오류 보고, 기존 생성기에서 이전

- 로그: `~/Library/Logs/CMBIOPHARM/daily-worklog.log` (`START`, `READ`, `SAVE`, `DONE`, `FAIL`, `SKIP`), launchd 출력은 `daily-worklog-launchd.log`.
- 실패하면 macOS 알림을 띄우고 중간 산출물을 지우지 않는다. 정상 실행은 알리지 않는다.
- **기존 생성기**: 2026-10-14~16 매일 20:15~20:20 KST에 `업무일지/` 아래 `YYYY-MM-DD_일일요약` 구글 문서를 만든 작업이 있다. 2026-10-17 현재 이 계정의 클라우드 예약 루틴 목록과 Mac launchd·crontab에서는 출처를 찾지 못했다.
- 이전 절차(`AGENTS.md`: 두 번 정상 생성 후 기존 해제):
  1. Mac에 `MODE=shadow`로 등록해 평일 두 번 이상 기존 문서와 비교한다.
  2. 대표가 기존 생성기를 찾아 끈다.
  3. `config/daily_worklog.conf`의 `MODE=live`를 커밋한다. 두 생성기가 같은 날 같은 폴더에 쓰지 않게 한다.
- 2026-10-16 기존 문서에 적힌 `_일일요약_누적` 폴더(`1RrK_DWRfWbsWK8Dd00q18nBW6Xx84Q4T`)는 조회되지 않는다. 다른 폴더로 옮기려면 `DEST_DIR`만 바꾼다.

## 8. 다른 에이전트와의 인계

- **Agent 04(주간 업무지시·주간 요약)**: Agent 04 문서가 `일일 요약`을 입력으로 쓴다. Agent 03의 `업무일지/YYYY-MM-DD_일일요약.docx`를 그 입력으로 한다. 토·일 실행 전에 그 주 월~금 요약이 있는지 Agent 03 로그로 확인할 수 있다.
- Agent 01(연구개발)은 일지의 실험 결과를 연구 문서로 옮길 때 원본 일지를 직접 본다. 요약은 참고용이다.
- 저장 위치·기기·실행 주기 변경은 Agent 00이 조정한다.

## 9. 금지와 사람의 판단이 필요한 작업

- 원본 일지를 수정·이동·삭제하지 않는다. 직원에게 메일·메시지를 보내지 않는다.
- 요약·중간 산출물을 Git에 커밋하지 않는다. 내용을 Drive와 요약 모델 밖으로 보내지 않는다.
- 사람 평가, 담당 변경, 업무 지시는 하지 않는다(대표 판단, 주간 지시는 Agent 04 초안).
- 사람 판단 필요:
  - `MODE=live` 전환과 기존 생성기 해제 시점
  - 저장 위치가 직원도 볼 수 있는 공유 드라이브여도 되는지. 대표 전용으로 하려면 `DEST_DIR`을 내 드라이브 폴더로 바꾼다.
  - 직급 표기: 등록부는 Agent 04와 같이 `문재훈 주임`이며, 10/15 보고서 직위란에는 `선임연구원`으로 적혀 있다.

## 수정 이력

| 일시 | 내용 |
|---|---|
| 2026-10-17 | 최초 작성. 추출·요약·저장 스크립트와 launchd 설치기 추가, 10/16 데이터로 shadow 시험 |
