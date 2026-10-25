# Agent 03 — 매일 업무일지 요약·점검, 주간 정리

- 기록일: 2026-10-17
- 상태: 운영 중 — 주간 정리 v0(일요일 10:00, Mac launchd `com.cmbiopharm.weekly-review`). 일일요약은 2026-10-18 대표 지시로 중지(launchd 해제, 스크립트는 수동 실행용으로 유지)
- 상위 규칙: 최상단 `AGENTS.md`. 이 문서는 그 규칙을 구체화하며 변경하지 않는다.
- 관련: `Agent 04` 주간 업무지시·주간 요약(`CMBIOPHARM/rnd`의 `agents/AGENT-04-주간업무지시.md`)

## 1. 목적과 책임 범위

대표(박태준)가 매일 저녁 직원 업무일지를 3분 안에 파악하도록 **일일요약·점검 초안(v0)**을 만든다.
대표가 읽고 수정 반영을 지시하면 그때 v1 이상을 만들어 공유 드라이브 `업무일지`에 올린다. 자동 실행은 v0만 만든다.
Agent 03의 역할은 `매일 루틴 업무`로 등록돼 있으며, 이 업무일지 요약·점검이 첫 업무다.

| 대상 | 담당 범위 | 일지 형식 |
|---|---|---|
| 문재훈 주임연구원 | 실험 실행·기록(합성, 슬러리·화장품 제형, 분무건조, 열처리, 체분급, BET·pH/EC·탭밀도, 분석 의뢰) | 날짜별 `일일_업무보고서_YYMMDD_문재훈.docx` |
| 배현민 이사 | 장비 전체·조달·외부 의뢰·업체 소통 | 누적 `업무보고 모음(…).hwpx`, `금일자(M/D)` 단위 |

대상자는 `config/daily_worklog_people.tsv`에서 관리한다. 직원이 늘거나 형식이 바뀌면 이 표만 고친다.

하는 일:

1. **요약**: 사람별 한 일 / 결과·이상·문제 / 내일·이후 계획 / 대표 확인·결정 필요 / 미완료.
2. **점검**: 미작성, 전일 `익일 계획`·`TO DO NEXT` 대비 이행 여부, 날짜·요일 오기, 같은 날짜 중복 기재와 기재본 간 차이, 7일 이내 일정·마감.

평가 문구는 쓰지 않는다. 기록된 사실과 기록의 빈칸만 적는다.

## 2. 실행 조건과 주기

| 작업 | 주기 | 기기 | 등록 |
|---|---|---|---|
| 일일요약·점검 | **중지**(2026-10-18). 필요하면 `--date`로 수동 실행 | Mac mini | launchd 해제됨 |
| 주간 정리 v0 (Word) | 매주 일요일 10:00 KST | Mac mini | launchd `com.cmbiopharm.weekly-review` |
| v1 발행 감시 (대표 메모) | 10분마다 | Mac mini | launchd `com.cmbiopharm.weekly-release` |

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
3. 주간 정리에서만 쓰는 입력(§4-2): `업무일지/주간_업무중점/<지난주 월요일>주/`의 대표 완성본 `*_업무지시_이름_V숫자.pdf`(가장 높은 V), Mac의 `rnd` 기본 저장소(`~/orca/rnd`, origin/main), 대표가 매주 넣는 사내 카톡 백업(`09. 인사/01. 차주업무지시/사내 카톡 백업/`, `KAKAO_DIR`). 모두 읽기만 한다.

원본 추출은 결정적 스크립트가 하고, 요약 모델에는 추출 묶음만 넘긴다. 모델은 도구·MCP·네트워크 없이 실행된다.

## 4. 출력과 저장 위치

| 단계 | 누가 언제 | 저장 위치 | 파일명 |
|---|---|---|---|
| v0 초안 | 자동, 월~금 20:30 | 대표 내 드라이브 `09. 인사/01. 차주업무지시/YYYY-MM-DD주/` | `YYYY-MM-DD_일일요약_v0.docx` |
| v1 이상 | 대표가 읽고 수정 반영을 지시할 때 | 공유 드라이브 `CMBIOPHARM/업무일지/` | `YYYY-MM-DD_일일요약_v1.docx`, `_v2` … |

- 주 폴더 `YYYY-MM-DD주`는 **그 주 월요일 날짜**다(예: 2026-10-16 요약은 `2026-10-12주`). 없으면 만든다. Agent 04는 토·일에 같은 상위 폴더에 **다음 주 월요일** 폴더를 만들므로, 한 주 폴더에 그 주 업무지시 초안과 그 주 일일요약 v0이 함께 모인다. 대표는 주 단위로 한 번에 검토한다.
- v0 파일명이 이미 있으면 덮어쓰지 않고 `_v0-2`, `_v0-3`을 붙인다. v1 이상 번호는 대표 검토본에만 쓴다.
- 공유 드라이브에 이미 같은 번호가 있으면(확장자 무관, 기존 `.gdoc` 포함) 다음 번호를 쓴다.
- `MODE=shadow`(시험용)는 Drive에 쓰지 않고 Mac 로컬 `~/Library/Application Support/CMBIOPHARM/daily-worklog/out/YYYY-MM-DD주/`에 만든다.
- 실행마다 중간 산출물(`bundle.md`, `checks.json`, `input.md`, `summary.md`)은 `~/Library/Application Support/CMBIOPHARM/daily-worklog/runs/<날짜_시각>/`에 남는다. 직원 기록이 담기므로 Git에 넣지 않는다.
- 문서 구성(원본은 `scripts/daily_worklog/prompt.md`): `한눈에` → 사람별 5개 절 → `점검` → `읽은 원본`.

### 4-1. v1 배포 절차 (대표 지시가 있을 때만)

1. 대표가 지정한 날짜·주의 최신 v0(대표가 Drive에서 직접 고친 내용 포함)를 읽는다.
2. 대표의 수정 지시를 반영한 수정본(.md 또는 .docx)을 만든다. 지시에 없는 내용은 바꾸지 않는다.
3. 날짜마다 다음 명령으로 공유 드라이브에 저장한다. 주 단위 지시면 그 주 날짜를 모두 반복한다.

```bash
G=~/Library/CloudStorage/GoogleDrive-jpark@cmbiopharm.com
python3 -I scripts/daily_worklog/publish_summary.py --release \
  --markdown <수정본.md 또는 .docx> --stem YYYY-MM-DD_일일요약 \
  --dest-dir "$G/공유 드라이브/CMBIOPHARM/업무일지"
```

4. 출력된 최종 경로와 파일명을 대표에게 보고한다. v0은 지우지 않는다.

### 4-2. 주간 정리 v0 (Word, 매주 일요일)

대표가 정한 양식(2026-10-18)이다. 사람별 Word 파일 하나, 2쪽 구성이다.

- 저장: `09. 인사/01. 차주업무지시/<차주 월요일>주/<차주 월요일>주_주간정리_<이름>_v0.docx`. Agent 04 차주 업무지시 초안과 같은 폴더다. 같은 이름이 있으면 `_v0-2`.
- 맨 위 빨간 테두리 `초안 v0 · 대표 검토 전 · 배포 금지`, 제목 `주간 정리 — 이름 직급`, 지난주·차주 기간.
- **앞쪽 — 1. 지난주 중점 대비 수행 (업무일지)**
  - 지난주 대표 완성본(최고 V)의 중점 한 줄과 할 일 표의 각 행을 `중점 항목`으로 옮긴다.
  - 표: `# | 중점 항목 | 수행 내용(업무일지) | 상태`. 상태는 `완료 / 일부 / 미완료 / 미확인`(색 구분). 일지 근거가 없으면 `미확인`.
  - `중점 외 수행`, `기록 점검`(미작성일, 중복 기재, 요일 오기, 일지와 리포 불일치).
  - 카톡에서 지난주 안에 하라고 한 지시가 완성본에 없으면 `(카톡 MM-DD)` 행으로 더해 대조한다.
- **뒤쪽(새 쪽) — 2. 차주 권장 업무 방향 (대표 지시·rnd 리포 기준)**
  - 방향 한 줄, 표: `# | 권장 업무 | 완료 기준`. 5~7행, 이월은 `(이월)`, 추정은 `(제안)`. 근거(지시·리포 경로)는 JSON에만 남기고 문서에는 싣지 않는다(2026-10-25 대표 지시).
  - 카톡의 대표 이행 지시(차주·기한 없음·미완료)는 맨 앞 행에 두고 근거를 `카톡 지시 MM-DD(요일)`로 적는다. 5~7행 한도에 세지 않는다.
  - `대표 결정 대기`, `미룬 것`. 참고란(요일 정정, 읽은 리포 문서)은 싣지 않는다.
- 사내 카톡 백업(2026-10-19 대표 지시): 대표가 매주 1회 카톡 내보내기 파일(`.txt`·`.csv`, 또는 그것이 든 `.zip`)을 넣는다. 파일 이름은 자유다. 지난주 월~일(실행 전날까지) 날짜의 대화 줄만 뽑고, 여러 백업에 겹친 같은 줄은 한 번만 넣는다. 인코딩은 UTF-8·UTF-16·CP949를 모두 읽는다. 지난주 이전에 수정된 파일은 건너뛴다. 백업이 없으면 카톡 지시 없이 만들고 참고란에 적는다. 대화 원문은 Mac 작업 폴더(`runs/`)에만 남고 Git에 넣지 않는다.
- 만드는 방법: 스크립트가 완성본 PDF(macOS PDFKit)와 지난주 월~토 일지, 지난주 카톡 대화를 추출하고 rnd 커밋 목록을 붙인다. Opus(`WEEKLY_MODEL`)가 rnd 리포 안에서 읽기 전용 도구(`Read`·`Glob`·`Grep`)로 관련 문서를 읽고 JSON을 낸다. `render_weekly_docx.py`가 표·쪽 나눔이 있는 Word로 만든다.
- 수동 실행: `bash scripts/weekly_review/run_weekly_review.sh --next-monday YYYY-MM-DD [--only 이름] [--mode shadow]`
- v1 이상은 아래 §4-3 메모 규칙으로만 발행한다.

### 4-3. v1 발행 규칙 — 대표 메모 (2026-10-18 대표 지시)

1. 대표가 v0 폴더(`09. 인사/01. 차주업무지시/<주>/`)에 메모장으로 수정 내역·지시를 적어 `.txt`(또는 `.md`)로 저장한다. 파일 이름은 자유다.
2. **첫 줄(빈 줄 제외)을 `v1발행`으로 시작**한다(띄어쓰기 무관, `v1발행 가능`·`v1 발행 아래 수정 필요`처럼 뒤에 글이 붙어도 되고 `v2발행`도 같다). 첫 줄이 이렇게 시작하지 않으면 일반 메모로 보고 건드리지 않는다.
3. 대상자: **메모 파일명**에 이름(문재훈, 배현민)이 있으면 그 사람만, 없으면 그 폴더의 주간정리 v0 전원. 본문에 나온 이름은 대상 판단에 쓰지 않는다(예: `배현민_v0피드백.txt`).
4. Mac launchd `com.cmbiopharm.weekly-release`가 10분마다 최근 8주 v0 폴더를 확인한다. 발행 대상 메모를 찾으면 다음을 진행한다.
   - 메모(최우선), v0을 만든 JSON, Drive v0 Word의 현재 텍스트(대표가 직접 고친 내용 포함), 사내 카톡 백업의 지난주 월요일~오늘 대화를 Opus에 넘긴다. 카톡은 메모가 카톡 지시를 가리킬 때만 쓴다.
   - 메모에 적힌 것만 바꾸고 나머지는 v0 그대로 둔다. 메모가 요구하면 rnd 리포를 읽기 전용으로 확인한다.
   - 맨 위를 `vN · 대표 검토 반영본 · 날짜`(남색 테두리)로 바꾼 Word를 만든다.
   - **공유 드라이브 `CMBIOPHARM/업무일지/주간_업무중점/<주>/<주>_주간정리_<이름>_vN.docx`**에 저장한다. N은 1부터 비어 있는 다음 번호이며 덮어쓰지 않는다. 대표 완성본 `_업무지시_이름_V숫자.pdf`와 이름이 겹치지 않는다.
5. 같은 폴더에 `<메모이름>_결과.txt`를 남긴다. 발행 경로, 반영한 것, 반영하지 못한 지시와 이유가 적힌다. 모호한 지시는 임의로 해석하지 않고 `미반영`으로 돌려준다.
6. 같은 내용의 메모는 다시 발행하지 않는다. 고쳐 저장하면(첫 줄 `v1발행` 유지) 다음 번호(v2…)로 다시 발행한다. 실패해도 같은 내용으로 반복하지 않으며, 메모를 고쳐 저장하면 재시도한다.
- 처리 기록: `~/Library/Logs/CMBIOPHARM/weekly-release.log`, 작업 파일 `~/Library/Application Support/CMBIOPHARM/weekly-review/releases/`, 처리한 메모 목록 `release_state.json`.
- 2026-10-18 시험(시험 폴더, cp949 메모): v1 발행, 결과 메모 작성, 같은 메모 재발행 안 함 확인. 모호한 지시 1건은 `미반영`으로 돌려줌.
- 2026-10-18 시험: `--next-monday 2026-10-19 --mode shadow --only 문재훈`. 완성본 V3 5개 행 대조, 리포 문서 10개 근거, 권장 7개.

## 5. 사용할 도구와 실행 환경

| 파일 | 역할 |
|---|---|
| `scripts/daily_worklog/run_daily_worklog.sh` | 실행 진입점. 잠금, 로그, 추출 → 요약 → 저장 → 확인 |
| `scripts/daily_worklog/collect_worklogs.py` | 원본 추출, 기계 점검(미작성, 작성일자 요일, 중복 기재) |
| `scripts/daily_worklog/prompt.md` | 요약 규칙과 문서 형식 |
| `scripts/daily_worklog/publish_summary.py` | Markdown → HTML → docx(`textutil`), v0 또는 `--release` v1 이상으로 저장, 바이트 비교 확인 |
| `scripts/daily_worklog/install_daily_worklog.sh` | launchd 등록·해제(`--remove`) |
| `config/daily_worklog.conf` | `MODE`, `MODEL`, 원본(`RAW_DIR`)·v0(`DRAFT_DIR`)·공유(`SHARE_DIR`) 경로 |
| `config/daily_worklog_people.tsv` | 대상자 등록부 |
| `scripts/weekly_review/run_weekly_review.sh` | 주간 정리 진입점. 사람별 생성·Word 변환·저장, 로그 `weekly-review.log` |
| `scripts/weekly_review/collect_week.py` | 완성본 PDF·주간 일지·rnd 커밋 목록 추출 |
| `scripts/weekly_review/prompt_weekly.md` | 주간 정리 규칙과 JSON 형식 |
| `scripts/weekly_review/render_weekly_docx.py` | JSON → Word(표, 상태 색, 쪽 나눔). 표준 라이브러리만 사용 |
| `scripts/weekly_review/install_weekly_review.sh` | 일요일 10:00 launchd 등록·해제(`--remove`) |
| `scripts/weekly_review/release_watch.py`, `run_release_watch.sh` | 대표 메모 `v1발행` 감시와 v1 이상 발행(§4-3) |
| `scripts/weekly_review/prompt_revise.md` | v1 반영 규칙(메모에 적힌 것만 수정) |
| `scripts/weekly_review/install_release_watch.sh` | 10분 주기 발행 감시 launchd 등록·해제(`--remove`) |

- Mac 기본 도구만 쓴다: `/usr/bin/python3`(3.9, 표준 라이브러리), `textutil`, `plutil`, `osascript`, `perl`(시간 제한).
- 요약: `claude -p --model claude-sonnet-5-5 --tools "" --strict-mcp-config --setting-sources ""`, 10분 제한.
- **macOS 권한(필수)**: launchd가 띄운 프로세스는 `~/Library/CloudStorage`(Google Drive)를 읽지 못한다("Operation not permitted", 2026-10-18 확인). 모든 Agent 03 launchd 작업은 전용 실행기 `~/Library/Application Support/CMBIOPHARM/bin/cmb-drive-runner`(소스 `scripts/macos_runner/`)를 거쳐 실행하고, **이 실행기 하나에만 전체 디스크 접근 권한**을 준다. 실행기는 자식으로 스크립트를 띄우고 기다리므로 자식(bash·python·claude)이 그 권한으로 Drive에 접근한다. 다시 빌드하면 권한을 다시 줘야 한다.
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
- 2026-10-17 시험: `--date 2026-10-16 --mode shadow` 정상(문재훈 미작성, 배현민 10/16자 5회 기재 감지, 기재본 차이 기록). v0 → `_v0-2`, `--release` v1 → v2 → v3 번호 증가 확인.

## 7. 로그·오류 보고, 기존 생성기에서 이전

- 로그: `~/Library/Logs/CMBIOPHARM/daily-worklog.log` (`START`, `READ`, `SAVE`, `DONE`, `FAIL`, `SKIP`), launchd 출력은 `daily-worklog-launchd.log`.
- 실패하면 macOS 알림을 띄우고 중간 산출물을 지우지 않는다. 정상 실행은 알리지 않는다.
- 이전 생성기(클로드 웹 예약 작업, 2026-10-14~16 `업무일지/`에 `YYYY-MM-DD_일일요약` 구글 문서 생성)는 2026-10-17 대표가 삭제했다. 그 3개 문서는 그대로 둔다. 이 에이전트가 유일한 일일요약 생성기다.

## 8. 다른 에이전트와의 인계

- **Agent 04(주간 업무지시·주간 요약)**: 주간 정리 v0(§4-2)이 Agent 04 문서 §4-2의 일요일 `주간 요약·차주 정리` 작업을 대표 양식으로 대신한다. 그 일요일 작업은 Mac에 따로 등록하지 않는다. 토요일 차주 업무지시 초안(클라우드)은 그대로 둔다.
- **Agent 04 입력**: Agent 04가 `일일 요약`을 입력으로 쓸 때 같은 상위 폴더 `09. 인사/01. 차주업무지시/YYYY-MM-DD주/`(그 주 월요일)의 `_일일요약_v0*.docx`와 공유 드라이브의 v1 이상을 읽는다. 둘 다 있으면 가장 높은 v 번호가 대표 검토본이다.
- Agent 01(연구개발)은 일지의 실험 결과를 연구 문서로 옮길 때 원본 일지를 직접 본다. 요약은 참고용이다.
- 저장 위치·기기·실행 주기 변경은 Agent 00이 조정한다.

## 9. 금지와 사람의 판단이 필요한 작업

- 원본 일지를 수정·이동·삭제하지 않는다. 직원에게 메일·메시지를 보내지 않는다.
- 요약·중간 산출물을 Git에 커밋하지 않는다. 내용을 Drive와 요약 모델 밖으로 보내지 않는다.
- 사람 평가, 담당 변경, 업무 지시는 하지 않는다(대표 판단, 주간 지시는 Agent 04 초안).
- v0을 공유 드라이브나 직원 폴더에 자동으로 올리지 않는다. v1 이상은 대표 지시가 있을 때만 4-1 절차로 만든다.
- 사람 판단 필요: v1 배포 여부와 수정 내용, 저장 위치 변경.

## 수정 이력

| 일시 | 내용 |
|---|---|
| 2026-10-25 | 반복된 EDEADLK(10-25 일요일 실행 실패, 배현민 메모 미발행) 근본 수정: launchd 프로세스는 Drive 미내려받기 파일을 열 수 없어 `cmb-materialize`로 내려받기 정책을 켬. 주간·발행 LaunchAgent 재등록 |
| 2026-10-25 | 대표 지시: 주간 정리 양식에서 뒤쪽 근거 열과 참고란 삭제(JSON에는 유지) |
| 2026-10-19 | 감시 잠금이 10-18 16:58 실패 이후 남아 모든 실행이 건너뛰어지던 문제 수정(exec 제거, 2시간 넘은 잠금 정리). 대상자는 메모 파일명 기준 |
| 2026-10-19 | v1발행 첫 줄 뒤에 글이 붙어도 인식(대표 메모 `v1발행 가능`이 감지되지 않았던 문제). v1 발행 때 카톡 백업도 함께 넘김 |
| 2026-10-19 | 대표 지시: 사내 카톡 백업(`KAKAO_DIR`)의 이행 지시를 주간 정리 v0에 반영(앞쪽 대조 행, 뒤쪽 맨 앞 행). 10-19주 배현민 v0-2에 BET 외주 위탁(rnd cb60675, 원래 10-26주 반영용)을 이번 주 지시로 추가 |
| 2026-10-17 | 최초 작성. 추출·요약·저장 스크립트와 launchd 설치기 추가, 10/16 데이터로 shadow 시험 |
| 2026-10-18 | v1 발행 규칙 추가: v0 폴더에 첫 줄 `v1발행` 메모 → 10분 안에 공유 드라이브 `주간_업무중점/<주>/`에 vN 발행, `_결과.txt` 회신 |
| 2026-10-18 | 대표 지시로 일일요약 자동 실행 중지(`install_daily_worklog.sh --remove`). `collect_worklogs.py`는 주간 정리가 계속 사용 |
| 2026-10-18 | 대표 양식으로 주간 정리 v0(Word) 추가: 앞쪽 지난주 중점 대비 수행(업무일지), 뒤쪽 차주 권장 업무(rnd 리포), 일요일 10:00, Opus |
| 2026-10-17 | 대표 지시 반영: 초안은 v0으로 내 드라이브 `09. 인사/01. 차주업무지시/YYYY-MM-DD주/`에 저장, 검토 후 v1부터 공유 드라이브 `업무일지`, 문재훈 직급 `주임연구원`, 이전 클로드 웹 생성기 삭제로 `MODE=live` |
