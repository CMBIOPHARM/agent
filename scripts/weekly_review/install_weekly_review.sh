#!/usr/bin/env bash
# Agent 03 주간 정리 v0(Word)를 매주 일요일 10:00 KST LaunchAgent로 등록하거나 해제한다.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
program="${script_dir}/run_weekly_review.sh"
label="com.cmbiopharm.weekly-review"
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

# 일요일(0) 10:00. Mac 시간대는 Asia/Seoul이어야 한다.
schedule='{"Weekday":0,"Hour":10,"Minute":0}'

plutil -create xml1 "${plist}"
plutil -insert Label -string "${label}" "${plist}"
plutil -insert ProgramArguments -json "[\"/bin/bash\",\"${program}\"]" "${plist}"
plutil -insert StartCalendarInterval -json "${schedule}" "${plist}"
plutil -insert ProcessType -string Background "${plist}"
plutil -insert StandardOutPath -string "${log_dir}/weekly-review-launchd.log" "${plist}"
plutil -insert StandardErrorPath -string "${log_dir}/weekly-review-launchd.log" "${plist}"

plutil -lint "${plist}"
launchctl bootstrap "${domain}" "${plist}"
echo "등록 완료: ${label} (일요일 10:00, 주간 정리 v0)"
echo "상태 로그: ${log_dir}/weekly-review.log"
