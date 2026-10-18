#!/usr/bin/env bash
# Agent 03 — 주간 정리 v0(Word). 앞쪽: 지난주 중점 대비 수행(업무일지), 뒤쪽: 차주 권장 업무(rnd 리포).
# 사용: run_weekly_review.sh [--next-monday YYYY-MM-DD] [--mode shadow|live] [--only 이름]
# 원본 일지와 rnd 리포는 읽기만 한다. Git 커밋·푸시와 외부 전송은 하지 않는다.
set -uo pipefail

export PATH="${HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export TZ="Asia/Seoul"
export GIT_TERMINAL_PROMPT=0

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "${script_dir}/../.." && pwd)"
conf="${repo_dir}/config/daily_worklog.conf"
people="${repo_dir}/config/daily_worklog_people.tsv"
drive_root="${HOME}/Library/CloudStorage/GoogleDrive-jpark@cmbiopharm.com"
log_dir="${HOME}/Library/Logs/CMBIOPHARM"
log_file="${log_dir}/weekly-review.log"
state_dir="${HOME}/Library/Application Support/CMBIOPHARM/weekly-review"
lock_dir="${TMPDIR:-/tmp}/cmbiopharm-weekly-review.lock"

next_monday=""
mode_override=""
only=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --next-monday) next_monday="$2"; shift 2 ;;
    --mode) mode_override="$2"; shift 2 ;;
    --only) only="$2"; shift 2 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 64 ;;
  esac
done

mkdir -p "${log_dir}" "${state_dir}"
exec >>"${log_file}" 2>&1

stamp() { date '+%Y-%m-%d %H:%M:%S %Z'; }
log() { printf '[%s] %s\n' "$(stamp)" "$*"; }
notify() {
  /usr/bin/osascript -e "display notification \"$1\" with title \"Agent 03 주간 정리\"" >/dev/null 2>&1 || true
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
# 기본값: 오늘 이후 처음 오는 월요일(일요일 실행이면 내일)
next_monday="${next_monday:-$(/usr/bin/python3 -I -c 'import datetime as d; t=d.date.today(); print((t+d.timedelta(days=7-t.weekday())).isoformat())')}"
raw_dir="${drive_root}/${RAW_DIR}"
rnd_dir="${RND_DIR:-${CMBIOPHARM_RND_DIR:-$(cd -- "${repo_dir}/.." && pwd)/rnd}}"
model="${WEEKLY_MODEL:-claude-opus-5-5}"

log "START 차주 ${next_monday} mode=${mode} model=${model} repo=$(git -C "${repo_dir}" rev-parse --short HEAD 2>/dev/null || echo '?')"
[[ -d "${raw_dir}" ]] || fail "Drive 원본 폴더 없음(마운트 확인): ${raw_dir}"
git -C "${rnd_dir}" rev-parse --verify --quiet origin/main >/dev/null || fail "rnd 리포를 찾지 못함: ${rnd_dir}"
git -C "${rnd_dir}" fetch --quiet origin || log "WARN rnd fetch 실패. 로컬 origin/main 기준으로 진행"

run_dir="${state_dir}/runs/${next_monday}_$(date '+%m%d-%H%M%S')"
mkdir -p "${run_dir}"
if ! /usr/bin/python3 -I "${script_dir}/collect_week.py" --raw-dir "${raw_dir}" --people "${people}" \
    --rnd-dir "${rnd_dir}" --next-monday "${next_monday}" --out-dir "${run_dir}" \
    | while IFS= read -r line; do log "READ ${line}"; done; then
  fail "입력 추출 실패 (${run_dir})"
fi

if [[ "${mode}" == "live" ]]; then
  [[ -d "${drive_root}/${DRAFT_DIR}" ]] || fail "v0 저장 위치 없음(마운트 확인): ${drive_root}/${DRAFT_DIR}"
  dest_dir="${drive_root}/${DRAFT_DIR}/${next_monday}주"
else
  dest_dir="${state_dir}/out/${next_monday}주"
fi

failures=0
while IFS=$'\t' read -r name title _rest; do
  [[ -z "${name}" || "${name}" == \#* ]] && continue
  [[ -n "${only}" && "${only}" != "${name}" ]] && continue
  [[ -s "${run_dir}/${name}.md" ]] || { log "FAIL [${name}] 입력 묶음 없음"; failures=$((failures + 1)); continue; }

  cat "${script_dir}/prompt_weekly.md" "${run_dir}/${name}.md" > "${run_dir}/${name}.input.md"
  # rnd 리포 안에서 읽기 전용 도구만 허용한다. 사람당 25분 제한.
  if ! (cd "${rnd_dir}" && /usr/bin/perl -e 'alarm shift; exec @ARGV' 1500 \
      claude -p --model "${model}" --tools Read Glob Grep --allowedTools Read Glob Grep \
      --strict-mcp-config --no-session-persistence --setting-sources "" \
      < "${run_dir}/${name}.input.md" > "${run_dir}/${name}.json" 2> "${run_dir}/${name}.err"); then
    log "FAIL [${name}] 정리 생성 실패: $(head -c 300 "${run_dir}/${name}.err" | tr '\n' ' ')"
    failures=$((failures + 1)); continue
  fi

  docx="${run_dir}/${name}.docx"
  if ! /usr/bin/python3 -I "${script_dir}/render_weekly_docx.py" --json "${run_dir}/${name}.json" \
      --name "${name}" --title "${title}" --next-monday "${next_monday}" --output "${docx}" >/dev/null; then
    log "FAIL [${name}] Word 변환 실패 (${run_dir}/${name}.json)"
    failures=$((failures + 1)); continue
  fi

  if ! final="$(/usr/bin/python3 -I "${repo_dir}/scripts/daily_worklog/publish_summary.py" --make-dir \
      --markdown "${docx}" --dest-dir "${dest_dir}" --stem "${next_monday}주_주간정리_${name}" | tail -n 1)" \
      || [[ ! -f "${final}" ]]; then
    log "FAIL [${name}] 저장 실패. 로컬 유지: ${docx}"
    failures=$((failures + 1)); continue
  fi
  log "SAVE [${name}] ${final}"
done < "${people}"

if [[ "${failures}" -gt 0 ]]; then
  fail "차주 ${next_monday} 실패 ${failures}건 (${run_dir})"
fi
log "DONE 차주 ${next_monday} mode=${mode}"
