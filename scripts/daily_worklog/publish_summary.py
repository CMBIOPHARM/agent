#!/usr/bin/env python3
"""요약을 docx로 저장하고 존재를 확인한다. 덮어쓰지 않는다.

- 기본(초안): <stem>_v0.docx. 이미 있으면 <stem>_v0-2, _v0-3 … (v1 이상은 대표 검토본 전용)
- --release(대표 지시 후): <stem>_v1부터 비어 있는 다음 번호. 입력은 수정된 .md 또는 .docx
확장자가 달라도(.gdoc 등) 같은 이름이면 사용 중으로 본다. 마지막 줄에 저장한 최종 경로를 출력한다.
"""
import argparse
import filecmp
import html
import os
import re
import shutil
import subprocess
import sys

CSS = """
body { font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif; font-size: 11pt; line-height: 1.5; }
h1 { font-size: 18pt; } h2 { font-size: 14pt; margin-top: 14pt; } h3 { font-size: 12pt; margin-top: 8pt; }
"""


def inline(text):
    text = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def md_to_html(md):
    """요약에 쓰는 Markdown 일부(제목, 들여쓴 글머리, 굵게, 구분선)만 HTML로 바꾼다."""
    out, depth = [], 0
    for raw in md.splitlines():
        line = raw.rstrip()
        bullet = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if bullet:
            level = min(len(bullet.group(1).replace("\t", "  ")) // 2, 3) + 1
            while depth < level:
                out.append("<ul>")
                depth += 1
            while depth > level:
                out.append("</ul>")
                depth -= 1
            out.append("<li>%s</li>" % inline(bullet.group(2)))
            continue
        while depth:
            out.append("</ul>")
            depth -= 1
        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            out.append("<h%d>%s</h%d>" % (level, inline(heading.group(2)), level))
        elif line.strip() == "---":
            out.append("<hr>")
        elif line.strip():
            out.append("<p>%s</p>" % inline(line))
    out.extend(["</ul>"] * depth)
    return "<!doctype html><html><head><meta charset='utf-8'><style>%s</style></head><body>%s</body></html>" % (
        CSS, "\n".join(out))


def taken_stems(dest_dir):
    return {os.path.splitext(f)[0] for f in os.listdir(dest_dir)}


def draft_name(dest_dir, stem):
    taken = taken_stems(dest_dir)
    name, n = "%s_v0" % stem, 2
    while name in taken:
        name = "%s_v0-%d" % (stem, n)
        n += 1
    return name + ".docx"


def release_name(dest_dir, stem):
    taken = taken_stems(dest_dir)
    n = 1
    while "%s_v%d" % (stem, n) in taken:
        n += 1
    return "%s_v%d.docx" % (stem, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", required=True, help="요약 .md (또는 --release일 때 수정본 .docx)")
    ap.add_argument("--dest-dir", required=True)
    ap.add_argument("--stem", required=True, help="예: 2026-10-16_일일요약")
    ap.add_argument("--release", action="store_true", help="대표 검토 후 v1 이상으로 저장")
    ap.add_argument("--make-dir", action="store_true", help="저장 위치(주 폴더)가 없으면 만든다")
    args = ap.parse_args()

    src = os.path.abspath(args.markdown)
    work_dir = os.path.dirname(src)
    if src.lower().endswith(".docx"):
        docx_path = src
    else:
        with open(src, encoding="utf-8") as fh:
            md = fh.read()
        if not md.lstrip().startswith("# "):
            print("요약 형식 오류: 첫 줄이 '# 날짜 일일요약'이 아님", file=sys.stderr)
            return 3
        html_path = os.path.join(work_dir, "summary.html")
        docx_path = os.path.join(work_dir, "summary.docx")
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(md_to_html(md))
        subprocess.run(["/usr/bin/textutil", "-convert", "docx", "-output", docx_path, html_path],
                       check=True, timeout=120)

    if args.make_dir:
        os.makedirs(args.dest_dir, exist_ok=True)
    if not os.path.isdir(args.dest_dir):
        print("저장 위치를 찾지 못함: %s" % args.dest_dir, file=sys.stderr)
        return 4
    pick = release_name if args.release else draft_name
    final = os.path.join(args.dest_dir, pick(args.dest_dir, args.stem))
    shutil.copyfile(docx_path, final)
    if not (os.path.isfile(final) and filecmp.cmp(docx_path, final, shallow=False)):
        print("저장 확인 실패: %s" % final, file=sys.stderr)
        return 5
    print(final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
