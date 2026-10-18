#!/usr/bin/env bash
# 등록된 저장소의 지난 24시간 활동을 집계해 일일 업무보고를 작성한다.
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export GIT_TERMINAL_PROMPT=0
export TZ="Asia/Seoul"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
control_repo="$(cd -- "${script_dir}/.." && pwd)"
orca_root="${CMBIOPHARM_ORCA_ROOT:-$(cd -- "${control_repo}/.." && pwd)}"
registry="${CMBIOPHARM_REPO_REGISTRY:-${control_repo}/config/repositories.tsv}"
user_home="${HOME}"
log_dir="${user_home}/Library/Logs/CMBIOPHARM"
log_file="${log_dir}/daily-operations-report.log"
hub_log="${log_dir}/agent-hub.log"
lock_dir="${TMPDIR:-/tmp}/cmbiopharm-daily-report.lock"
dry_run=0

if [[ "${1:-}" == "--dry-run" ]]; then
  dry_run=1
elif [[ -n "${1:-}" ]]; then
  echo "사용법: $0 [--dry-run]" >&2
  exit 2
fi

mkdir -p "${log_dir}"
if [[ "${dry_run}" -eq 0 ]]; then
  exec >>"${log_file}" 2>&1
fi

stamp() { date '+%Y-%m-%d %H:%M:%S %Z'; }
log() { printf '[%s] %s\n' "$(stamp)" "$*"; }

if [[ ! -f "${registry}" ]]; then
  log "FAIL 저장소 등록부를 찾지 못함: ${registry}"
  exit 1
fi

report_end="$(date '+%Y-%m-%dT%H:%M:%S%z')"
report_start="$(date -v-24H '+%Y-%m-%dT%H:%M:%S%z')"
report_date="$(date '+%Y-%m-%d')"
display_end="$(date '+%Y-%m-%d %H:%M:%S %Z')"
display_start="$(date -v-24H '+%Y-%m-%d %H:%M:%S %Z')"
hub_end="$(date '+[%Y-%m-%d %H:%M:%S')"
hub_start="$(date -v-24H '+[%Y-%m-%d %H:%M:%S')"

write_report() {
  output_file="$1"
  {
    printf '# %s 일일 업무보고\n\n' "${report_date}"
    printf -- '- 집계 기간: `%s` ~ `%s`\n' "${display_start}" "${display_end}"
    printf -- '- 생성 주체: Agent 00 Mac 자동화\n\n'

    run_count=0
    pull_count=0
    warn_count=0
    fail_count=0
    if [[ -f "${hub_log}" ]]; then
      read -r run_count pull_count warn_count fail_count < <(
        awk -v start="${hub_start}" -v end="${hub_end}" '
          $0 >= start && $0 <= end {
            if ($0 ~ /SUMMARY/) runs++
            if ($0 ~ / PULL /) pulls++
            if ($0 ~ / WARN /) warns++
            if ($0 ~ / FAIL /) fails++
          }
          END { printf "%d %d %d %d\n", runs, pulls, warns, fails }
        ' "${hub_log}"
      )
    fi

    printf '## Agent 00 운영\n\n'
    printf -- '- 통합 감시 실행: %d회\n' "${run_count}"
    printf -- '- 원격 변경 수신: %d회\n' "${pull_count}"
    printf -- '- 경고: %d건\n' "${warn_count}"
    printf -- '- 실패: %d건\n\n' "${fail_count}"

    printf '## 저장소별 변경\n\n'
    while IFS=$'\t' read -r repo_name relative_path auto_fast_forward extra; do
      [[ -z "${repo_name}" || "${repo_name}" == \#* ]] && continue
      repo_dir="${orca_root}/${relative_path}"
      printf '### %s\n\n' "${repo_name}"

      if ! git -C "${repo_dir}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        printf -- '- 상태: 저장소를 찾지 못함 — `%s`\n\n' "${repo_dir}"
        continue
      fi
      if ! git -C "${repo_dir}" fetch --prune --quiet origin; then
        printf -- '- 상태: GitHub fetch 실패\n\n'
        continue
      fi

      head_sha="$(git -C "${repo_dir}" rev-parse --short origin/main 2>/dev/null || echo '없음')"
      commit_count="$(git -C "${repo_dir}" rev-list --count --since="${report_start}" --until="${report_end}" origin/main 2>/dev/null || echo 0)"
      local_state="$(git -C "${repo_dir}" status --short --branch 2>/dev/null | head -n 1)"
      printf -- '- 원격 `main`: `%s`\n' "${head_sha}"
      printf -- '- 로컬 상태: `%s`\n' "${local_state}"
      printf -- '- 신규 커밋: %s건\n' "${commit_count}"

      if [[ "${commit_count}" -gt 0 ]]; then
        printf '\n변경 내역:\n\n'
        git -C "${repo_dir}" log origin/main --since="${report_start}" --until="${report_end}" \
          --format='- `%h` %s — %an' --reverse
        printf '\n\n'
      else
        printf '\n'
      fi

      unmerged=""
      while IFS= read -r remote_branch; do
        case "${remote_branch}" in
          origin/HEAD|origin/main) continue ;;
        esac
        if git -C "${repo_dir}" cherry origin/main "${remote_branch}" 2>/dev/null | grep -q '^+'; then
          unmerged+="${remote_branch}"$'\n'
        fi
      done < <(git -C "${repo_dir}" for-each-ref --format='%(refname:short)' refs/remotes/origin)
      unmerged="${unmerged%$'\n'}"
      if [[ -n "${unmerged}" ]]; then
        printf '미병합 원격 브랜치:\n\n'
        while IFS= read -r remote_branch; do
          printf -- '- `%s`\n' "${remote_branch}"
        done <<< "${unmerged}"
        printf '\n'
      else
        printf -- '- 미병합 원격 브랜치: 없음\n\n'
      fi
    done < "${registry}"

    drive_state="정상"
    [[ -d "${user_home}/Library/CloudStorage/GoogleDrive-jpark@cmbiopharm.com/공유 드라이브/CMBIOPHARM" ]] || drive_state="연결 안 됨"
    simulator_state="정상"
    [[ -x "${orca_root}/rnd/scripts/.venv/bin/python" ]] || simulator_state="환경 없음"
    orca_state="실행 중"
    ps -axo args= | awk '$0 == "/Applications/Orca.app/Contents/MacOS/Orca" { found=1 } END { exit !found }' || orca_state="실행 안 됨"
    sleep_value="$(pmset -g custom 2>/dev/null | awk '$1 == "sleep" {print $2; exit}')"
    disk_state="$(df -h "${orca_root}" | awk 'NR == 2 {print $3 " 사용 / " $2 " 전체 (" $5 ")"}')"

    printf '## 실행 환경\n\n'
    printf -- '- Orca: %s\n' "${orca_state}"
    printf -- '- Google Drive: %s\n' "${drive_state}"
    printf -- '- Mac 시뮬레이터: %s\n' "${simulator_state}"
    printf -- '- 시스템 잠자기 값: `%s`\n' "${sleep_value:-확인 실패}"
    printf -- '- 디스크: %s\n' "${disk_state:-확인 실패}"
  } > "${output_file}"
}

if [[ "${dry_run}" -eq 1 ]]; then
  dry_file="$(mktemp "${TMPDIR:-/tmp}/cmbiopharm-daily-report-preview.XXXXXX")"
  write_report "${dry_file}"
  sed -n '1,260p' "${dry_file}"
  rm -f "${dry_file}"
  exit 0
fi

if ! mkdir "${lock_dir}" 2>/dev/null; then
  log "SKIP 이전 일일 보고 작업이 아직 실행 중"
  exit 0
fi
trap 'rmdir "${lock_dir}" 2>/dev/null || true' EXIT

if ! git -C "${control_repo}" fetch --prune --quiet origin; then
  log "FAIL agent 저장소 fetch 실패"
  exit 1
fi

temp_parent="$(mktemp -d "${TMPDIR:-/tmp}/cmbiopharm-daily-report-worktree.XXXXXX")"
worktree="${temp_parent}/worktree"
if ! git -C "${control_repo}" worktree add --detach "${worktree}" origin/main >/dev/null; then
  log "FAIL 임시 worktree 생성 실패: ${worktree}"
  exit 1
fi

report_dir="${worktree}/reports/daily"
mkdir -p "${report_dir}"
report_name="${report_date}_업무보고.md"
version=1
while [[ -e "${report_dir}/${report_name}" ]]; do
  version=$((version + 1))
  report_name="${report_date}_업무보고_v${version}.md"
done
report_relative="reports/daily/${report_name}"
report_file="${worktree}/${report_relative}"

write_report "${report_file}"
git -C "${worktree}" add -- "${report_relative}"
if ! git -C "${worktree}" commit -m "report: ${report_date} 일일 업무보고" >/dev/null; then
  log "FAIL 일일 업무보고 커밋 실패; worktree 보존: ${worktree}"
  exit 1
fi

report_sha="$(git -C "${worktree}" rev-parse HEAD)"
if ! git -C "${worktree}" push origin HEAD:main; then
  log "FAIL 일일 업무보고 fast-forward push 실패; worktree 보존: ${worktree}"
  exit 1
fi
remote_sha="$(git -C "${worktree}" ls-remote origin refs/heads/main | awk '{print $1}')"
if [[ "${remote_sha}" != "${report_sha}" ]]; then
  log "FAIL 원격 커밋 검증 실패; worktree 보존: ${worktree}"
  exit 1
fi

git -C "${control_repo}" worktree remove "${worktree}"
rmdir "${temp_parent}" 2>/dev/null || true
log "OK ${report_relative} 생성·커밋·푸시 완료 (${report_sha:0:7})"
