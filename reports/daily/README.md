# 일일 업무보고

- 매일 07:00 KST에 직전 24시간의 상태를 집계한다.
- 대상은 `config/repositories.tsv`에 등록된 모든 저장소다.
- 보고서는 `YYYY-MM-DD_업무보고.md` 형식으로 새로 생성한다.
- 같은 날짜의 파일이 이미 있으면 덮어쓰지 않고 `_v2`, `_v3`를 붙인다.
- 자동화는 임시 Git worktree에서 보고 파일 하나만 커밋한다.
- `origin/main`에 fast-forward push할 수 없으면 푸시하지 않고 로그에 실패를 남긴다.
- 실행 로그는 `~/Library/Logs/CMBIOPHARM/daily-operations-report.log`에 기록한다.
