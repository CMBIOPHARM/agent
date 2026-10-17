#!/usr/bin/env bash
# Agent 03 매일 업무일지 요약·점검을 평일 20:30 KST LaunchAgent로 등록하거나 해제한다.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
program="${script_dir}/run_daily_worklog.sh"
label="com.cmbiopharm.daily-worklog"
plist="${HOME}/Library/LaunchAgents/${label}.plist"
domain="gui/$(id -u)"
log_dir="${HOME}/Library/Logs/CMBIOPHARM"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "이 설치기는 macOS용입니다." >&2
  exit 1
fi

if [[ "${1:-}" == "--remove" ]]; then
  launchctl bootout "${domain}" "${plist}" 2>/dev/null || true
  rm -f "${plist}"
  echo "해제 완료: ${label}"
  exit 0
fi

if [[ ! -x "${program}" ]]; then
  echo "실행 파일을 찾지 못함: ${program}" >&2
  exit 1
fi

mkdir -p "${HOME}/Library/LaunchAgents" "${log_dir}"
launchctl bootout "${domain}" "${plist}" 2>/dev/null || true

# 월(1)~금(5) 20:30. Mac 시간대는 Asia/Seoul이어야 한다.
schedule='['
for weekday in 1 2 3 4 5; do
  schedule+="{\"Weekday\":${weekday},\"Hour\":20,\"Minute\":30},"
done
schedule="${schedule%,}]"

plutil -create xml1 "${plist}"
plutil -insert Label -string "${label}" "${plist}"
plutil -insert ProgramArguments -json "[\"/bin/bash\",\"${program}\"]" "${plist}"
plutil -insert StartCalendarInterval -json "${schedule}" "${plist}"
plutil -insert ProcessType -string Background "${plist}"
plutil -insert StandardOutPath -string "${log_dir}/daily-worklog-launchd.log" "${plist}"
plutil -insert StandardErrorPath -string "${log_dir}/daily-worklog-launchd.log" "${plist}"

plutil -lint "${plist}"
launchctl bootstrap "${domain}" "${plist}"
echo "등록 완료: ${label} (월~금 20:30, 매일 업무일지 요약·점검)"
echo "상태 로그: ${log_dir}/daily-worklog.log"
