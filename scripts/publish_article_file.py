#!/usr/bin/env python3
"""Publish a local article file in Stephan's markdown format to WeChat MP draft box."""

import argparse
import pathlib
import subprocess
import sys
import tempfile


def extract_title_and_body(path: pathlib.Path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    title = ""
    body_lines = []
    in_body = False

    for line in lines:
        if not title and line.startswith("# "):
            title = line[2:].strip()
            continue
        if line.strip() == "## 正文":
            in_body = True
            continue
        if in_body:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()

    if not title:
        raise ValueError("Could not find article title. Expected first-level heading starting with '# '.")
    if not body:
        raise ValueError("Could not find article body. Expected content after a '## 正文' section.")

    return title, body


def main():
    parser = argparse.ArgumentParser(
        description="Publish an article file by extracting '# 标题' and the content after '## 正文'"
    )
    parser.add_argument("article_file", help="Path to the article markdown file")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--digest", default="", help="Article digest")
    parser.add_argument("--content-source-url", default="", help="Original article URL")
    parser.add_argument("--thumb-media-id", default=None, help="Specific cover image media_id")
    parser.add_argument("--font-size", default="15px")
    parser.add_argument("--line-height", default="2")
    parser.add_argument("--color", default="#333")
    parser.add_argument("--heading-size", default="22px")
    parser.add_argument("--subheading-size", default="18px")
    parser.add_argument("--dry-run", action="store_true", help="Render HTML only")
    parser.add_argument("--output-html", default="", help="Where to save rendered HTML in dry-run mode")
    args = parser.parse_args()

    article_path = pathlib.Path(args.article_file).expanduser().resolve()
    title, body = extract_title_and_body(article_path)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as tmp:
        tmp.write(body)
        tmp_path = tmp.name

    cmd = [
        sys.executable,
        str(pathlib.Path(__file__).with_name("publish.py")),
        "--title",
        title,
        "--content-file",
        tmp_path,
        "--author",
        args.author,
        "--digest",
        args.digest,
        "--content-source-url",
        args.content_source_url,
        "--font-size",
        args.font_size,
        "--line-height",
        args.line_height,
        "--color",
        args.color,
        "--heading-size",
        args.heading_size,
        "--subheading-size",
        args.subheading_size,
    ]

    if args.thumb_media_id:
        cmd.extend(["--thumb-media-id", args.thumb_media_id])
    if args.dry_run:
        cmd.append("--dry-run")
    if args.output_html:
        cmd.extend(["--output-html", args.output_html])

    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
