#!/usr/bin/env python3
"""주간 정리 입력 묶음을 사람별로 만든다.

- 지난주 대표 완성본: 공유 드라이브 업무일지/주간_업무중점/<지난주 월요일>주/*_업무지시_<이름>_V<n>.pdf 중 최고 V (PDFKit로 텍스트 추출).
  PDF가 없으면 같은 폴더의 주간 정리 발행본 *_주간정리_<이름>_v<n>.docx 중 최고 v(대표 검토본)를 쓴다.
- 지난주 업무일지: 월~토 원본(daily_worklog/collect_worklogs.py 재사용)
- rnd 리포: 지난주 월요일 이후 main 커밋 목록과 바뀐 파일(모델이 리포에서 직접 읽을 목록)
- 사내 카톡 백업: 대표가 매주 넣는 내보내기 파일(.txt/.csv/.zip)에서 지난주 월~일 대화만(이행 지시 추출용)
출력: <out_dir>/<이름>.md, <out_dir>/meta.json
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import unicodedata
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "daily_worklog"))
import collect_worklogs as cw  # noqa: E402

JXA_PDF_TEXT = (
    'ObjC.import("PDFKit"); function run(a){'
    'var d=$.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(a[0]));'
    'if(!d||d.isNil()) return ""; return d.string.js}'
)
MAX_COMMITS_CHARS = 30000
MAX_KAKAO_CHARS = 120000
KAKAO_EXT = (".txt", ".csv")
# 카톡 내보내기의 날짜 머리(줄 맨 앞): '2026년 10월 19일 …', '2026. 10. 19. 오후 3:15, …', '2026-10-19 15:15:00,…'
KAKAO_DATE = re.compile(r'^[\s\-="\[]*(20\d\d)\s*(?:년|[.\-/])\s*(\d{1,2})\s*(?:월|[.\-/])\s*(\d{1,2})(?!\d)')


def pdf_text(path):
    res = subprocess.run(["/usr/bin/osascript", "-l", "JavaScript", "-e", JXA_PDF_TEXT, path],
                         capture_output=True, text=True, timeout=120)
    return res.stdout.strip() if res.returncode == 0 else ""


def latest_directive(focus_root, week_monday, name):
    folder = os.path.join(focus_root, "%s주" % week_monday.isoformat())
    if not os.path.isdir(folder):
        return None, None
    best, best_v = None, -1
    for f in os.listdir(folder):
        m = re.search(r"_업무지시_%s_V(\d+)\.pdf$" % re.escape(name), unicodedata.normalize("NFC", f))
        if m and int(m.group(1)) > best_v:
            best, best_v = f, int(m.group(1))
    if best:
        return best, pdf_text(os.path.join(folder, best))
    # 대표 검토를 거친 주간 정리 vN의 '차주 권장 업무'가 그 주의 지시다.
    for f in os.listdir(folder):
        m = re.search(r"_주간정리_%s_v(\d+)\.docx$" % re.escape(name), unicodedata.normalize("NFC", f))
        if m and int(m.group(1)) > best_v:
            best, best_v = f, int(m.group(1))
    if not best:
        return None, None
    text = cw.docx_text(os.path.join(folder, best))
    return best, "(주간 정리 발행본. 뒤쪽 '2. 차주 권장 업무 방향' 표의 각 행이 지난주 중점 항목이다)\n" + text


def rnd_commits(rnd_dir, since):
    fmt = "--format=@@ %h %ad %s"
    res = subprocess.run(
        ["git", "-C", rnd_dir, "log", "origin/main", "--since=%sT00:00:00+09:00" % since.isoformat(),
         "--date=format:%m-%d", "--name-only", fmt],
        capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        return "(rnd 커밋 목록을 읽지 못함: %s)" % res.stderr.strip()
    lines = []
    for ln in res.stdout.splitlines():
        if not ln.strip():
            continue
        if ln.startswith("@@ "):
            lines.append("- " + ln[3:])
        elif ln.endswith(".md"):
            lines.append("    - " + ln)
    text = "\n".join(lines)
    if len(text) > MAX_COMMITS_CHARS:
        text = text[:MAX_COMMITS_CHARS] + "\n…(이하 생략. git log로 직접 확인)"
    return text


def decode(raw):
    for enc in ("utf-8-sig", "utf-16", "cp949"):
        if enc == "utf-16" and not raw.startswith((b"\xff\xfe", b"\xfe\xff")):
            continue
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def kakao_sources(kakao_dir, since):
    """(표시 이름, 내용) 목록. 지난주 이전에 마지막으로 수정된 파일은 건너뛴다."""
    out = []
    for root, _dirs, files in os.walk(kakao_dir):
        for f in files:
            path = os.path.join(root, f)
            ext = os.path.splitext(f)[1].lower()
            if f.startswith(".") or dt.date.fromtimestamp(os.path.getmtime(path)) < since:
                continue
            if ext in KAKAO_EXT:
                out.append((os.path.getmtime(path), f, decode(open(path, "rb").read())))
            elif ext == ".zip":
                try:
                    with zipfile.ZipFile(path) as zf:
                        for n in zf.namelist():
                            if os.path.splitext(n)[1].lower() in KAKAO_EXT:
                                out.append((os.path.getmtime(path), "%s/%s" % (f, n), decode(zf.read(n))))
                except zipfile.BadZipFile:
                    continue
    return [(name, text) for _m, name, text in sorted(out)]


def kakao_week(kakao_dir, start, end):
    """start~end(포함) 날짜의 대화 줄만 모은다. 겹치는 백업은 같은 줄을 한 번만 남긴다."""
    if not kakao_dir or not os.path.isdir(kakao_dir):
        return [], ""
    used, seen, parts = [], set(), []
    for name, text in kakao_sources(kakao_dir, start):
        day, lines = None, []
        for ln in text.splitlines():
            m = KAKAO_DATE.match(ln)
            if m:
                try:
                    day = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                except ValueError:
                    pass
            if day is None or not (start <= day <= end) or not ln.strip():
                continue
            key = (day, ln.strip())
            if key not in seen:
                seen.add(key)
                lines.append(ln.rstrip())
        if lines:
            used.append(name)
            parts.append("### %s\n%s" % (name, "\n".join(lines)))
    text = "\n\n".join(parts)
    if len(text) > MAX_KAKAO_CHARS:
        text = text[:MAX_KAKAO_CHARS] + "\n…(이하 생략. 분량 초과)"
    return used, text


def week_logs(raw_dir, person, monday):
    parts, written, missing = [], [], []
    for i in range(6):
        day = monday + dt.timedelta(days=i)
        try:
            r = cw.collect_person(raw_dir, person, day)
        except (OSError, zipfile.BadZipFile, RuntimeError) as e:
            parts.append("### %s — 원본을 읽지 못함 (%s)" % (cw.kdate(day), e))
            continue
        if r["status"] == "작성":
            written.append(cw.kdate(day))
            files = ", ".join("%s(수정 %s)" % (f["file"], f["modified"]) for f in r["files"])
            issues = "".join("\n- 기계 점검: %s" % x for x in r["issues"])
            parts.append("### %s — %s%s\n%s" % (cw.kdate(day), files, issues, r["today"]))
        elif i < 5:
            missing.append(cw.kdate(day))
    return parts, written, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--people", required=True)
    ap.add_argument("--rnd-dir", required=True)
    ap.add_argument("--next-monday", required=True, help="차주 월요일 YYYY-MM-DD")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--kakao-dir", default="", help="사내 카톡 백업 폴더(없으면 생략)")
    args = ap.parse_args()

    next_monday = dt.date.fromisoformat(args.next_monday)
    prev_monday = next_monday - dt.timedelta(days=7)
    focus_root = os.path.join(args.raw_dir, "주간_업무중점")
    commits = rnd_commits(args.rnd_dir, prev_monday)
    rnd_head = subprocess.run(["git", "-C", args.rnd_dir, "log", "-1", "--format=%h %ad", "--date=format:%Y-%m-%d %H:%M",
                               "origin/main"], capture_output=True, text=True).stdout.strip()
    os.makedirs(args.out_dir, exist_ok=True)
    kakao_files, kakao = kakao_week(args.kakao_dir, prev_monday, next_monday - dt.timedelta(days=1))
    print("카톡 백업: %s" % (", ".join(kakao_files) or "지난주 대화 없음"))

    meta = {"prev_monday": prev_monday.isoformat(), "next_monday": next_monday.isoformat(),
            "rnd_head": rnd_head, "kakao_files": kakao_files, "people": []}
    for person in cw.load_people(args.people):
        directive_file, directive = latest_directive(focus_root, prev_monday, person["name"])
        parts, written, missing = week_logs(args.raw_dir, person, prev_monday)
        prev_fri = prev_monday + dt.timedelta(days=4)
        next_fri = next_monday + dt.timedelta(days=4)
        doc = [
            "# 주간 정리 입력 — %s %s" % (person["name"], person["title"]),
            "",
            "- 지난주: %s ~ %s" % (cw.kdate(prev_monday), cw.kdate(prev_fri)),
            "- 차주: %s ~ %s" % (cw.kdate(next_monday), cw.kdate(next_fri)),
            "- 담당: %s" % person["scope"],
            "- 업무일지 작성일: %s" % (", ".join(written) or "없음"),
            "- 업무일지 미작성(평일): %s" % (", ".join(missing) or "없음"),
            "- rnd main 최신: %s" % rnd_head,
            "",
            "## A. 지난주 대표 완성본(중점 기준) — %s" % (directive_file or "없음"),
            directive or "(지난주 완성본을 찾지 못함. 중점 대비 대조는 '미확인'으로 두고 업무일지 기준으로만 정리)",
            "",
            "## B. 지난주 업무일지 원본",
            "\n\n".join(parts) or "(지난주 업무일지 없음)",
            "",
            "## C. rnd 리포 지난주 이후 커밋과 바뀐 문서 (현재 작업 폴더가 rnd 리포다. 필요한 문서는 직접 읽는다)",
            commits or "(커밋 없음)",
            "",
            "## D. 사내 카톡 백업 — 지난주 %s ~ %s 대화 (%s)" % (
                cw.kdate(prev_monday), cw.kdate(next_monday - dt.timedelta(days=1)), ", ".join(kakao_files) or "없음"),
            kakao or "(지난주 카톡 백업 없음. 카톡 지시는 반영하지 않았다고 notes에 적는다)",
        ]
        with open(os.path.join(args.out_dir, "%s.md" % person["name"]), "w", encoding="utf-8") as fh:
            fh.write("\n".join(doc))
        meta["people"].append({"name": person["name"], "title": person["title"], "directive": directive_file,
                               "written": written, "missing": missing})
        print("%s %s: 완성본 %s, 일지 %d일, 미작성 %d일" % (
            person["name"], person["title"], directive_file or "없음", len(written), len(missing)))
    with open(os.path.join(args.out_dir, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
