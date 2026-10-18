#!/usr/bin/env bash
# 일일 업무보고를 매일 07:00 KST에 실행하도록 LaunchAgent를 등록하거나 해제한다.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
program="${script_dir}/generate_daily_report.sh"
label="com.cmbiopharm.daily-operations-report"
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

plutil -create xml1 "${plist}"
plutil -insert Label -string "${label}" "${plist}"
plutil -insert ProgramArguments -json "[\"/bin/bash\",\"${program}\"]" "${plist}"
plutil -insert StartCalendarInterval -json '{"Hour":7,"Minute":0}' "${plist}"
plutil -insert ProcessType -string Background "${plist}"
plutil -insert StandardOutPath -string "${log_dir}/daily-operations-report-launchd.log" "${plist}"
plutil -insert StandardErrorPath -string "${log_dir}/daily-operations-report-launchd.log" "${plist}"

plutil -lint "${plist}"
launchctl bootstrap "${domain}" "${plist}"
echo "등록 완료: ${label} (매일 07:00 KST)"
echo "상태 로그: ${log_dir}/daily-operations-report.log"
