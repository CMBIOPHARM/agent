#!/usr/bin/env python3
"""직원 업무일지 원본(Drive 마운트, 읽기 전용)에서 지정일 기록을 뽑아 요약용 묶음을 만든다.

출력: <out_dir>/bundle.md (요약 입력), <out_dir>/checks.json (기계 점검 결과)
원본 파일은 읽기만 한다. docx는 macOS textutil, hwpx는 zip 안의 section*.xml에서 텍스트를 뽑는다.
"""
import argparse
import datetime as dt
import errno
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile

WEEKDAYS = "월화수목금토일"
LOOKBACK_DAYS = 7
MAX_SECTION_CHARS = 12000


def kdate(d):
    return "%s(%s)" % (d.isoformat(), WEEKDAYS[d.weekday()])


def mtime_str(path):
    return dt.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")


def squeeze(text):
    lines = [ln.rstrip() for ln in text.replace("\r", "").split("\n")]
    out, blank = [], False
    for ln in lines:
        if ln.strip():
            out.append(ln.strip())
            blank = False
        elif not blank and out:
            out.append("")
            blank = True
    return "\n".join(out).strip()


def read_bytes(path, tries=6, wait=10):
    """Drive 파일을 읽는다. 아직 내려받지 않은 파일은 launchd에서 EDEADLK(Resource deadlock avoided)가
    나므로 Drive가 내려받을 때까지 잠시 기다렸다 다시 읽는다."""
    for i in range(tries):
        try:
            with open(path, "rb") as fh:
                return fh.read()
        except OSError as e:
            if e.errno not in (errno.EDEADLK, errno.EAGAIN, errno.ETIMEDOUT) or i == tries - 1:
                raise
            time.sleep(wait)


def docx_text(path):
    read_bytes(path)  # 내려받기 먼저(위 참고)
    res = subprocess.run(
        ["/usr/bin/textutil", "-convert", "txt", "-stdout", path],
        capture_output=True, text=True, timeout=120,
    )
    if res.returncode != 0:
        raise RuntimeError("textutil 실패: %s" % res.stderr.strip())
    return squeeze(res.stdout)


def hwpx_paragraphs(path):
    paras = []
    with zipfile.ZipFile(io.BytesIO(read_bytes(path))) as zf:
        sections = sorted(n for n in zf.namelist() if re.match(r"Contents/section\d+\.xml$", n))
        for name in sections:
            xml = zf.read(name).decode("utf-8", "replace")
            for p in re.findall(r"<hp:p\b.*?</hp:p>", xml, re.S):
                t = "".join(re.findall(r"<hp:t\b[^>]*>(.*?)</hp:t>", p, re.S))
                t = re.sub(r"<[^>]+>", "", t)
                t = t.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").strip()
                if t:
                    paras.append(t)
    return paras


HWPX_HEADER = re.compile(r"금일자\s*\(\s*(\d{1,2})\s*/\s*(\d{1,2})\s*\)")


def hwpx_sections(paths, name):
    """누적 hwpx들에서 '금일자(M/D)' 머리말 단위로 자른다. 반환: {(m, d): [section_text, ...]}
    머리말이 앞 문단 끝에 붙어 있으면(예: '…보완배현민 이사 금일자(10/16)') 이름 위치에서 나눈다."""
    found = {}
    for path in paths:
        current, buf = None, []
        for para in hwpx_paragraphs(path):
            m = HWPX_HEADER.search(para)
            if m:
                cut = para.rfind(name, 0, m.start())
                cut = m.start() if cut < 0 else cut
                if para[:cut].strip() and current:
                    buf.append(para[:cut].strip())
                if current:
                    found.setdefault(current, []).append("\n".join(buf))
                current, buf = (int(m.group(1)), int(m.group(2))), [para[cut:].strip()]
            elif current:
                buf.append(para)
        if current:
            found.setdefault(current, []).append("\n".join(buf))
    return found


def docx_entry(folder, name, day):
    yymmdd = day.strftime("%y%m%d")
    files = sorted(
        f for f in os.listdir(folder)
        if f.lower().endswith(".docx") and yymmdd in f and not f.startswith("~$")
    )
    if not files:
        return None
    entries = []
    for f in files:
        path = os.path.join(folder, f)
        entries.append({"file": f, "modified": mtime_str(path), "text": docx_text(path)})
    return entries


def check_docx_weekday(text, day):
    """'작성일자 2026 년 10 월 15 일 (목요일)' 줄의 날짜·요일을 검산한다."""
    issues = []
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*\(?\s*([월화수목금토일])", text)
    if not m:
        return issues
    try:
        written = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return ["작성일자가 유효한 날짜가 아님: %s" % m.group(0)]
    if written != day:
        issues.append("작성일자 %s가 파일명 날짜 %s와 다름" % (kdate(written), kdate(day)))
    if WEEKDAYS[written.weekday()] != m.group(4):
        issues.append("작성일자 요일 오기: %s(%s)로 적혀 있으나 실제 %s" % (written.isoformat(), m.group(4), kdate(written)))
    return issues


def load_people(path):
    people = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 5:
                raise SystemExit("대상자 등록부 형식 오류: %r" % line)
            people.append(dict(zip(["name", "title", "folder", "format", "scope"], cols[:5])))
    return people


def collect_person(raw_dir, person, day):
    folder = os.path.join(raw_dir, person["folder"])
    result = {"name": person["name"], "title": person["title"], "status": "미작성",
              "files": [], "issues": [], "today": "", "previous": "", "previous_date": ""}
    if not os.path.isdir(folder):
        result["status"] = "폴더 없음"
        result["issues"].append("원본 폴더를 찾지 못함: %s" % folder)
        return result

    if person["format"] == "docx":
        entries = docx_entry(folder, person["name"], day)
        if entries:
            result["status"] = "작성"
            result["files"] = [{"file": e["file"], "modified": e["modified"]} for e in entries]
            result["today"] = "\n\n".join(e["text"] for e in entries)
            for e in entries:
                result["issues"].extend(check_docx_weekday(e["text"], day))
            if len(entries) > 1:
                result["issues"].append("같은 날짜 파일 %d개: %s" % (len(entries), ", ".join(e["file"] for e in entries)))
        for back in range(1, LOOKBACK_DAYS + 1):
            prev_day = day - dt.timedelta(days=back)
            prev = docx_entry(folder, person["name"], prev_day)
            if prev:
                result["previous_date"] = kdate(prev_day)
                result["previous"] = prev[-1]["text"]
                break

    elif person["format"] == "hwpx":
        paths = sorted(
            (os.path.join(folder, f) for f in os.listdir(folder)
             if f.lower().endswith(".hwpx") and not f.startswith("~$")),
            key=os.path.getmtime,
        )
        result["files"] = [{"file": os.path.basename(p), "modified": mtime_str(p)} for p in paths[-2:]]
        sections = hwpx_sections(paths[-2:], person["name"]) if paths else {}
        todays = sections.get((day.month, day.day), [])
        if todays:
            result["status"] = "작성"
            if len(todays) > 1:
                result["issues"].append(
                    "%s자 보고가 %d번 기재됨(초안 중복 가능). 마지막 기재본을 기준으로 하고 앞 기재본과 다른 점을 확인할 것"
                    % (kdate(day), len(todays)))
                result["today"] = "\n\n".join(
                    "[기재본 %d/%d]\n%s" % (i + 1, len(todays), t) for i, t in enumerate(todays))
            else:
                result["today"] = todays[0]
        for back in range(1, LOOKBACK_DAYS + 1):
            prev_day = day - dt.timedelta(days=back)
            prev = sections.get((prev_day.month, prev_day.day))
            if prev:
                result["previous_date"] = kdate(prev_day)
                result["previous"] = prev[-1]
                break
    else:
        result["status"] = "형식 미지원"
        result["issues"].append("등록부 format 값이 docx/hwpx가 아님: %s" % person["format"])

    if len(result["today"]) > MAX_SECTION_CHARS:
        result["today"] = result["today"][:MAX_SECTION_CHARS] + "\n…(이하 생략, 원본 확인)"
        result["issues"].append("기록이 길어 %d자 이후를 생략함" % MAX_SECTION_CHARS)
    if len(result["previous"]) > MAX_SECTION_CHARS // 2:
        result["previous"] = result["previous"][: MAX_SECTION_CHARS // 2] + "\n…(이하 생략)"
    return result


def render_bundle(day, people, results):
    out = ["# 업무일지 원본 묶음 — %s" % kdate(day), ""]
    for person, r in zip(people, results):
        out.append("## %s %s — %s" % (r["name"], r["title"], r["status"]))
        out.append("- 담당: %s" % person["scope"])
        for f in r["files"]:
            out.append("- 읽은 파일: %s (수정 %s KST)" % (f["file"], f["modified"]))
        for issue in r["issues"]:
            out.append("- 기계 점검: %s" % issue)
        out.append("")
        out.append("### 오늘 기록")
        out.append(r["today"] or "(오늘자 기록 없음)")
        out.append("")
        out.append("### 직전 기록 %s" % (r["previous_date"] or "(최근 %d일 내 없음)" % LOOKBACK_DAYS))
        out.append(r["previous"] or "(없음)")
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--people", required=True)
    ap.add_argument("--date", help="YYYY-MM-DD, 기본값 오늘")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    day = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    if not os.path.isdir(args.raw_dir):
        print("원본 폴더를 찾지 못함: %s" % args.raw_dir, file=sys.stderr)
        return 2
    people = load_people(args.people)
    results = [collect_person(args.raw_dir, p, day) for p in people]

    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "bundle.md"), "w", encoding="utf-8") as fh:
        fh.write(render_bundle(day, people, results))
    checks = {
        "date": day.isoformat(),
        "label": kdate(day),
        "people": [{k: r[k] for k in ("name", "title", "status", "files", "issues", "previous_date")} for r in results],
    }
    with open(os.path.join(args.out_dir, "checks.json"), "w", encoding="utf-8") as fh:
        json.dump(checks, fh, ensure_ascii=False, indent=2)
    for r in results:
        print("%s %s: %s, 파일 %d개, 점검 %d건" % (r["name"], r["title"], r["status"], len(r["files"]), len(r["issues"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
