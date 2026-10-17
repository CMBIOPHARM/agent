#!/usr/bin/env bash
# Agent 03 — 직원 업무일지 원본을 읽어 일일요약·점검 문서를 만든다.
# 사용: run_daily_worklog.sh [--date YYYY-MM-DD] [--mode shadow|live]
# 원본 일지는 읽기만 한다. Git 커밋·푸시와 외부 전송은 하지 않는다.
set -uo pipefail

export PATH="${HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export TZ="Asia/Seoul"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "${script_dir}/../.." && pwd)"
conf="${repo_dir}/config/daily_worklog.conf"
people="${repo_dir}/config/daily_worklog_people.tsv"
drive_root="${HOME}/Library/CloudStorage/GoogleDrive-jpark@cmbiopharm.com"
log_dir="${HOME}/Library/Logs/CMBIOPHARM"
log_file="${log_dir}/daily-worklog.log"
state_dir="${HOME}/Library/Application Support/CMBIOPHARM/daily-worklog"
lock_dir="${TMPDIR:-/tmp}/cmbiopharm-daily-worklog.lock"

day=""
mode_override=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --date) day="$2"; shift 2 ;;
    --mode) mode_override="$2"; shift 2 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 64 ;;
  esac
done

mkdir -p "${log_dir}" "${state_dir}"
exec >>"${log_file}" 2>&1

stamp() { date '+%Y-%m-%d %H:%M:%S %Z'; }
log() { printf '[%s] %s\n' "$(stamp)" "$*"; }
notify() {
  /usr/bin/osascript -e "display notification \"$1\" with title \"Agent 03 업무일지\"" >/dev/null 2>&1 || true
}
fail() {
  log "FAIL $*"
  notify "실패: $*"
  exit 1
}

if ! mkdir "${lock_dir}" 2>/dev/null; then
  log "SKIP 이전 실행이 아직 진행 중"
  exit 0
fi
trap 'rmdir "${lock_dir}" 2>/dev/null || true' EXIT

[[ -f "${conf}" ]] || fail "설정 파일 없음: ${conf}"
# shellcheck source=/dev/null
source "${conf}"
mode="${mode_override:-${MODE:-shadow}}"
[[ "${mode}" == "shadow" || "${mode}" == "live" ]] || fail "MODE 값 오류: ${mode}"
day="${day:-$(date '+%Y-%m-%d')}"
raw_dir="${drive_root}/${RAW_DIR}"
stem="${day}_일일요약"

log "START ${day} mode=${mode} repo=$(git -C "${repo_dir}" rev-parse --short HEAD 2>/dev/null || echo '?')"
[[ -d "${raw_dir}" ]] || fail "Drive 원본 폴더 없음(마운트 확인): ${raw_dir}"

run_dir="${state_dir}/runs/${day}_$(date '+%H%M%S')"
mkdir -p "${run_dir}"

if ! /usr/bin/python3 -I "${script_dir}/collect_worklogs.py" \
    --raw-dir "${raw_dir}" --people "${people}" --date "${day}" --out-dir "${run_dir}" \
    | while IFS= read -r line; do log "READ ${line}"; done; then
  fail "원본 추출 실패 (${run_dir})"
fi
[[ -s "${run_dir}/bundle.md" ]] || fail "원본 묶음이 비어 있음 (${run_dir})"

cat "${script_dir}/prompt.md" "${run_dir}/bundle.md" > "${run_dir}/input.md"
# 도구·MCP·사용자 설정 없이 입력 묶음만 보고 요약한다. 10분 안에 끝나지 않으면 중단한다.
if ! /usr/bin/perl -e 'alarm shift; exec @ARGV' 600 \
    claude -p --model "${MODEL:-claude-sonnet-5-5}" --tools "" --strict-mcp-config \
    --no-session-persistence --setting-sources "" \
    < "${run_dir}/input.md" > "${run_dir}/summary.md" 2> "${run_dir}/claude.err"; then
  fail "요약 생성 실패: $(head -c 300 "${run_dir}/claude.err" | tr '\n' ' ') (${run_dir})"
fi

# 주 폴더는 그 주 월요일 날짜(YYYY-MM-DD주). 토·일 실행분도 그 주에 넣는다.
week="$(/usr/bin/python3 -I -c 'import datetime as d,sys; x=d.date.fromisoformat(sys.argv[1]); print((x-d.timedelta(days=x.weekday())).isoformat())' "${day}")주"
if [[ "${mode}" == "live" ]]; then
  [[ -d "${drive_root}/${DRAFT_DIR}" ]] || fail "v0 저장 위치 없음(마운트 확인): ${drive_root}/${DRAFT_DIR}"
  dest_dir="${drive_root}/${DRAFT_DIR}/${week}"
else
  dest_dir="${state_dir}/out/${week}"
fi

if ! final="$(/usr/bin/python3 -I "${script_dir}/publish_summary.py" --make-dir \
    --markdown "${run_dir}/summary.md" --dest-dir "${dest_dir}" --stem "${stem}" | tail -n 1)"; then
  fail "저장 실패. 로컬 원본 유지: ${run_dir}/summary.md"
fi
[[ -n "${final}" && -f "${final}" ]] || fail "저장 확인 실패. 로컬 원본 유지: ${run_dir}/summary.md"

missing="$(/usr/bin/python3 -I -c 'import json,sys; c=json.load(open(sys.argv[1])); print(", ".join(p["name"] for p in c["people"] if p["status"]!="작성"))' "${run_dir}/checks.json")"
log "SAVE ${final}"
log "DONE ${day} mode=${mode} 미작성=[${missing:-없음}]"
