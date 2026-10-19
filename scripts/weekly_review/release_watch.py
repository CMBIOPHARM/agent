#!/usr/bin/env python3
"""v0 저장 폴더의 대표 메모를 감시해 주간 정리 v1 이상을 공유 드라이브에 발행한다.

규칙(대표 지시 2026-10-18)
- v0 폴더(DRAFT_DIR/<YYYY-MM-DD>주/)에 대표가 메모장(.txt)으로 수정 내역·지시를 적어 저장한다.
- 첫 줄(빈 줄 제외)이 `v1발행`으로 시작하면(공백 허용, 뒤에 글이 붙어도 됨, v2발행 등도 같음) 발행 대상이다.
- 메모가 카톡 지시를 가리킬 수 있으므로 사내 카톡 백업의 해당 주(지난주 월요일~오늘) 대화를 함께 넘긴다.
- 대상자: 메모 파일명이나 본문에 이름이 있으면 그 사람, 없으면 그 폴더의 주간정리 v0 전원.
- 결과: 공유 드라이브 업무일지/주간_업무중점/<주>/<주>_주간정리_<이름>_v<n>.docx (n은 1부터 비어 있는 다음 번호)
- 같은 폴더에 `<메모이름>_결과.txt`를 남긴다. 메모 내용이 바뀌지 않으면 다시 발행하지 않는다.
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "daily_worklog"))
sys.path.insert(0, HERE)
import collect_worklogs as cw  # noqa: E402
from collect_week import kakao_week  # noqa: E402
from render_weekly_docx import load_json  # noqa: E402

TRIGGER = re.compile(r"^\s*v\s*(\d+)\s*발행", re.I)
WEEK_DIR = re.compile(r"^(\d{4}-\d{2}-\d{2})주$")
MEMO_EXT = (".txt", ".md")
RESULT_SUFFIX = "_결과"
LOOKBACK_WEEKS = 8


def log(msg):
    print("[%s] %s" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S KST"), msg), flush=True)


def read_memo(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-16", "cp949"):
        try:
            if enc == "utf-16" and not raw.startswith((b"\xff\xfe", b"\xfe\xff")):
                continue
            return raw.decode(enc), hashlib.sha256(raw).hexdigest()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace"), hashlib.sha256(raw).hexdigest()


def trigger_version(text):
    for line in text.splitlines():
        if line.strip():
            m = TRIGGER.match(line)
            return int(m.group(1)) if m else None
    return None


def latest_v0(folder, week, name):
    cands = glob.glob(os.path.join(folder, "%s주_주간정리_%s_v0*.docx" % (week, name)))
    cands = [c for c in cands if re.search(r"_v0(-\d+)?\.docx$", c)]
    return max(cands, key=os.path.getmtime) if cands else None


def latest_run_json(state_dir, week, name):
    runs = sorted(glob.glob(os.path.join(state_dir, "runs", "%s_*" % week)), key=os.path.getmtime, reverse=True)
    for r in runs:
        p = os.path.join(r, "%s.json" % name)
        if os.path.isfile(p):
            return p
    return None


def docx_text(path):
    res = subprocess.run(["/usr/bin/textutil", "-convert", "txt", "-stdout", path],
                         capture_output=True, text=True, timeout=120)
    return res.stdout.strip() if res.returncode == 0 else "(v0 문서 텍스트를 읽지 못함)"


def write_result(memo_path, lines):
    stem = os.path.splitext(memo_path)[0]
    path = stem + RESULT_SUFFIX + ".txt"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("처리 결과 — %s\n\n" % dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
        fh.write("\n".join(lines) + "\n")
    return path


def revise_one(cfg, week, folder, name, title, memo_text, work_dir, kakao=""):
    v0 = latest_v0(folder, week, name)
    if not v0:
        return False, "%s: v0 파일이 없음" % name
    run_json = latest_run_json(cfg.state_dir, week, name)
    parts = [open(os.path.join(HERE, "prompt_revise.md"), encoding="utf-8").read(),
             "# 대상: %s %s, %s주 주간 정리\n" % (name, title, week),
             "## 대표 메모\n" + memo_text.strip(),
             "## v0 원본 JSON\n" + (open(run_json, encoding="utf-8").read() if run_json else "(없음)"),
             "## v0 현재 문서 텍스트 (%s)\n%s" % (os.path.basename(v0), docx_text(v0)),
             "## 사내 카톡 백업 (지난주 월요일~오늘)\n" + (kakao or "(없음)")]
    inp = os.path.join(work_dir, "%s.input.md" % name)
    out = os.path.join(work_dir, "%s.json" % name)
    err = os.path.join(work_dir, "%s.err" % name)
    with open(inp, "w", encoding="utf-8") as fh:
        fh.write("\n\n".join(parts))
    with open(inp, "rb") as fin, open(out, "wb") as fout, open(err, "wb") as ferr:
        rc = subprocess.call(
            ["/usr/bin/perl", "-e", "alarm shift; exec @ARGV", "1500", "claude", "-p", "--model", cfg.model,
             "--tools", "Read", "Glob", "Grep", "--allowedTools", "Read", "Glob", "Grep",
             "--strict-mcp-config", "--no-session-persistence", "--setting-sources", ""],
            stdin=fin, stdout=fout, stderr=ferr, cwd=cfg.rnd_dir)
    if rc != 0:
        return False, "%s: v1 내용 생성 실패(rc=%d)" % (name, rc)

    share_dir = os.path.join(cfg.share_root, "%s주" % week)
    os.makedirs(share_dir, exist_ok=True)
    stem = "%s주_주간정리_%s" % (week, name)
    # 발행 번호를 미리 정해 머리 문구에 넣는다(publish_summary.py와 같은 규칙).
    taken = {os.path.splitext(f)[0] for f in os.listdir(share_dir)}
    n = 1
    while "%s_v%d" % (stem, n) in taken:
        n += 1
    docx = os.path.join(work_dir, "%s.docx" % name)
    rc = subprocess.call([sys.executable, "-I", os.path.join(HERE, "render_weekly_docx.py"), "--json", out,
                          "--name", name, "--title", title, "--next-monday", week, "--output", docx,
                          "--label", "v%d · 대표 검토 반영본 · %s" % (n, dt.date.today().isoformat())],
                         stdout=subprocess.DEVNULL)
    if rc != 0:
        return False, "%s: Word 변환 실패 (%s)" % (name, out)
    res = subprocess.run([sys.executable, "-I", os.path.join(HERE, "..", "daily_worklog", "publish_summary.py"),
                          "--release", "--markdown", docx, "--dest-dir", share_dir, "--stem", stem],
                         capture_output=True, text=True)
    final = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ""
    if res.returncode != 0 or not os.path.isfile(final):
        return False, "%s: 공유 드라이브 저장 실패 (%s)" % (name, res.stderr.strip())
    try:
        data = load_json(out)
    except ValueError:
        data = {}
    lines = ["%s: 발행 완료 → %s" % (name, final.replace(cfg.drive_root + "/", ""))]
    lines += ["  - 반영: %s" % c for c in (data.get("changes") or [])]
    lines += ["  - 미반영: %s" % c for c in (data.get("unapplied") or [])]
    return True, "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drive-root", required=True)
    ap.add_argument("--draft-dir", required=True)
    ap.add_argument("--share-root", required=True, help="공유 드라이브 업무일지/주간_업무중점")
    ap.add_argument("--people", required=True)
    ap.add_argument("--rnd-dir", required=True)
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--kakao-dir", default="")
    cfg = ap.parse_args()

    state_path = os.path.join(cfg.state_dir, "release_state.json")
    try:
        state = json.load(open(state_path, encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    people = cw.load_people(cfg.people)
    cutoff = dt.date.today() - dt.timedelta(weeks=LOOKBACK_WEEKS)

    for entry in sorted(os.listdir(cfg.draft_dir)):
        m = WEEK_DIR.match(entry)
        if not m or dt.date.fromisoformat(m.group(1)) < cutoff:
            continue
        week, folder = m.group(1), os.path.join(cfg.draft_dir, entry)
        for f in sorted(os.listdir(folder)):
            stem, ext = os.path.splitext(f)
            if ext.lower() not in MEMO_EXT or stem.endswith(RESULT_SUFFIX):
                continue
            memo_path = os.path.join(folder, f)
            text, digest = read_memo(memo_path)
            version = trigger_version(text)
            if version is None or state.get(memo_path) == digest:
                continue
            body = "\n".join(text.splitlines()[1:]) if text else ""
            targets = [p for p in people if p["name"] in f or p["name"] in body] or people
            log("TRIGGER %s (요청 v%d, 대상 %s)" % (memo_path, version, ",".join(p["name"] for p in targets)))
            work_dir = os.path.join(cfg.state_dir, "releases", "%s_%s" % (week, dt.datetime.now().strftime("%m%d-%H%M%S")))
            os.makedirs(work_dir, exist_ok=True)
            monday = dt.date.fromisoformat(week)
            _files, kakao = kakao_week(cfg.kakao_dir, monday - dt.timedelta(days=7),
                                       min(dt.date.today(), monday + dt.timedelta(days=6)))
            lines, ok_all = [], True
            for p in targets:
                ok, msg = revise_one(cfg, week, folder, p["name"], p["title"], text, work_dir, kakao)
                ok_all = ok_all and ok
                lines.append(msg)
                log(("SAVE " if ok else "FAIL ") + msg.splitlines()[0])
            if not ok_all:
                lines.append("\n실패한 항목은 메모를 한 번 더 저장(내용 수정)하면 다시 시도함. 작업 폴더: %s" % work_dir)
            result = write_result(memo_path, lines)
            log("RESULT %s" % result)
            # 실패해도 같은 내용으로는 다시 돌리지 않는다(반복 실패 방지). 메모를 고쳐 저장하면 재시도한다.
            state[memo_path] = digest
            with open(state_path, "w", encoding="utf-8") as fh:
                json.dump(state, fh, ensure_ascii=False, indent=1)
            if not ok_all:
                subprocess.call(["/usr/bin/osascript", "-e",
                                 'display notification "v1 발행 일부 실패: %s" with title "Agent 03 주간 정리"' % f])
    return 0


if __name__ == "__main__":
    sys.exit(main())
