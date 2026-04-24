#!/usr/bin/env python3
"""Render markdown/plain text to WeChat-friendly HTML and publish to draft box."""

import argparse
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request


DEFAULT_STYLE = {
    "font_size": "15px",
    "line_height": "2",
    "color": "#333",
    "heading_size": "22px",
    "subheading_size": "18px",
}


def json_exit(payload, code=0):
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(code)


def api_get_json(url: str):
    with urllib.request.urlopen(url, timeout=20) as resp:
        return json.loads(resp.read())


def api_post_json(url: str, payload: dict):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_access_token(appid: str, secret: str) -> str:
    query = urllib.parse.urlencode(
        {"grant_type": "client_credential", "appid": appid, "secret": secret}
    )
    url = f"https://api.weixin.qq.com/cgi-bin/token?{query}"
    resp = api_get_json(url)
    if "access_token" in resp:
        return resp["access_token"]

    code = resp.get("errcode", "unknown")
    msg = resp.get("errmsg", "")
    hint = ""
    if code == 40164:
        ip = re.search(r"invalid ip (\S+)", msg)
        ip_str = ip.group(1) if ip else "unknown"
        hint = f"Add IP {ip_str} to 微信公众平台 -> 设置与开发 -> 基本配置 -> IP白名单"
    elif code == 40001:
        hint = "Check that WECHAT_MP_APPID and WECHAT_MP_SECRET are correct"
    json_exit({"success": False, "errcode": code, "errmsg": msg, "hint": hint}, 1)


def get_latest_thumb_media_id(token: str) -> str:
    url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={token}"
    resp = api_post_json(url, {"type": "image", "offset": 0, "count": 1})
    items = resp.get("item", [])
    if not items:
        json_exit(
            {
                "success": False,
                "errcode": -1,
                "errmsg": "No images found in the permanent material library",
                "hint": "Upload at least one image in 微信公众平台 -> 素材库",
            },
            1,
        )
    return items[0]["media_id"]


def apply_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r'<code style="background:#f6f8fa;border-radius:4px;padding:2px 6px;font-family:Menlo,Consolas,monospace;font-size:13px;">\1</code>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def is_table_separator(line: str) -> bool:
    return bool(re.match(r"^\|?[\s:-]+(\|[\s:-]+)+\|?$", line.strip()))


def render_paragraph(block_lines):
    content = "<br/>".join(apply_inline(line.strip()) for line in block_lines if line.strip())
    return f'<p style="margin:14px 0;text-align:justify;">{content}</p>'


def render_heading(level: int, text: str, style):
    size = style["heading_size"] if level == 1 else style["subheading_size"]
    weight = "700" if level == 1 else "600"
    return (
        f'<h{level} style="font-size:{size};font-weight:{weight};margin:28px 0 14px;line-height:1.5;">'
        f"{apply_inline(text.strip())}</h{level}>"
    )


def render_list(items, ordered=False):
    tag = "ol" if ordered else "ul"
    style = (
        "padding-left:1.4em;margin:14px 0;"
        + ("list-style-type:decimal;" if ordered else "list-style-type:disc;")
    )
    rows = "".join(
        f'<li style="margin:8px 0;">{apply_inline(item)}</li>' for item in items
    )
    return f'<{tag} style="{style}">{rows}</{tag}>'


def render_blockquote(block_lines):
    body = "<br/>".join(apply_inline(re.sub(r"^>\s?", "", line)) for line in block_lines)
    return (
        '<blockquote style="margin:16px 0;padding:10px 14px;border-left:4px solid #d0d7de;'
        'background:#f6f8fa;color:#57606a;">'
        f"{body}</blockquote>"
    )


def render_code_block(code_lines):
    body = html.escape("\n".join(code_lines))
    return (
        '<section style="background:#f6f8fa;border-radius:6px;padding:14px 16px;margin:16px 0;'
        'font-family:Menlo,Consolas,monospace;font-size:13px;line-height:1.6;white-space:pre-wrap;'
        'word-break:break-all;overflow-x:auto;">'
        f"{body}</section>"
    )


def render_table(block_lines):
    header = [apply_inline(cell.strip()) for cell in block_lines[0].strip("|").split("|")]
    rows = []
    for line in block_lines[2:]:
        cells = [apply_inline(cell.strip()) for cell in line.strip("|").split("|")]
        rows.append(cells)
    parts = [
        '<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;">',
        "<thead><tr>",
    ]
    for cell in header:
        parts.append(
            '<th style="background:#f5f5f5;padding:10px 12px;border:1px solid #e0e0e0;text-align:left;">'
            f"{cell}</th>"
        )
    parts.append("</tr></thead><tbody>")
    for row in rows:
        parts.append("<tr>")
        for cell in row:
            parts.append(
                f'<td style="padding:10px 12px;border:1px solid #e0e0e0;">{cell}</td>'
            )
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def markdown_to_html(text: str, style):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    parts = [
        f'<section style="font-size:{style["font_size"]};line-height:{style["line_height"]};'
        f'color:{style["color"]};padding:10px 0;">'
    ]

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i].rstrip("\n"))
                i += 1
            if i < len(lines):
                i += 1
            parts.append(render_code_block(code_lines))
            continue

        if stripped.startswith(">"):
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip())
                i += 1
            parts.append(render_blockquote(block))
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading_match:
            level = min(len(heading_match.group(1)), 2)
            parts.append(render_heading(level, heading_match.group(2), style))
            i += 1
            continue

        if "|" in stripped and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            block = [lines[i].strip(), lines[i + 1].strip()]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            parts.append(render_table(block))
            continue

        ordered = re.match(r"^\d+[\.\)]\s+.+$", stripped)
        unordered = re.match(r"^[-*]\s+.+$", stripped)
        if ordered or unordered:
            items = []
            ordered_mode = bool(ordered)
            while i < len(lines):
                candidate = lines[i].strip()
                pattern = r"^\d+[\.\)]\s+(.+)$" if ordered_mode else r"^[-*]\s+(.+)$"
                m = re.match(pattern, candidate)
                if not m:
                    break
                items.append(m.group(1))
                i += 1
            parts.append(render_list(items, ordered=ordered_mode))
            continue

        block = [line]
        i += 1
        while i < len(lines) and lines[i].strip():
            next_line = lines[i].strip()
            if (
                next_line.startswith("```")
                or next_line.startswith(">")
                or re.match(r"^(#{1,3})\s+.+$", next_line)
                or (i + 1 < len(lines) and "|" in next_line and is_table_separator(lines[i + 1]))
                or re.match(r"^\d+[\.\)]\s+.+$", next_line)
                or re.match(r"^[-*]\s+.+$", next_line)
            ):
                break
            block.append(lines[i])
            i += 1
        parts.append(render_paragraph(block))

    parts.append("</section>")
    return "\n".join(parts)


def publish_draft(token: str, title: str, author: str, html_content: str, thumb_media_id: str, digest: str = "", content_source_url: str = ""):
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    payload = {
        "articles": [
            {
                "title": title,
                "author": author,
                "digest": digest,
                "content": html_content,
                "content_source_url": content_source_url,
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }
        ]
    }
    resp = api_post_json(url, payload)
    if "media_id" in resp:
        return resp
    code = resp.get("errcode", "unknown")
    msg = resp.get("errmsg", "")
    hint = ""
    if code == 40164:
        ip = re.search(r"invalid ip (\S+)", msg)
        ip_str = ip.group(1) if ip else "unknown"
        hint = f"Add IP {ip_str} to 微信公众平台 -> 设置与开发 -> 基本配置 -> IP白名单"
    return {"success": False, "errcode": code, "errmsg": msg, "hint": hint}


def read_content(args):
    if args.content_from_stdin:
        return sys.stdin.read()
    if args.content_file:
        with open(args.content_file, "r", encoding="utf-8") as f:
            return f.read()
    json_exit(
        {
            "success": False,
            "errcode": -1,
            "errmsg": "No content provided",
            "hint": "Use --content-file or --content-from-stdin",
        },
        1,
    )


def main():
    parser = argparse.ArgumentParser(description="Publish article to WeChat MP draft box")
    parser.add_argument("--title", required=True, help="Article title")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--digest", default="", help="Article digest")
    parser.add_argument("--content-source-url", default="", help="Original article URL")
    parser.add_argument("--content-file", help="Path to markdown/text content")
    parser.add_argument("--content-from-stdin", action="store_true", help="Read content from stdin")
    parser.add_argument("--thumb-media-id", default=None, help="Cover image media_id")
    parser.add_argument("--font-size", default=DEFAULT_STYLE["font_size"])
    parser.add_argument("--line-height", default=DEFAULT_STYLE["line_height"])
    parser.add_argument("--color", default=DEFAULT_STYLE["color"])
    parser.add_argument("--heading-size", default=DEFAULT_STYLE["heading_size"])
    parser.add_argument("--subheading-size", default=DEFAULT_STYLE["subheading_size"])
    parser.add_argument("--dry-run", action="store_true", help="Render HTML only, do not publish")
    parser.add_argument("--output-html", help="Write rendered HTML to a file")
    args = parser.parse_args()

    content = read_content(args)
    style = {
        "font_size": args.font_size,
        "line_height": args.line_height,
        "color": args.color,
        "heading_size": args.heading_size,
        "subheading_size": args.subheading_size,
    }
    html_content = markdown_to_html(content, style)

    if args.output_html:
        with open(args.output_html, "w", encoding="utf-8") as f:
            f.write(html_content)

    if args.dry_run:
        json_exit(
            {
                "success": True,
                "mode": "dry-run",
                "html_file": args.output_html or "",
                "html_length": len(html_content),
                "message": "Rendered WeChat HTML successfully",
            }
        )

    appid = os.environ.get("WECHAT_MP_APPID")
    secret = os.environ.get("WECHAT_MP_SECRET")
    if not appid or not secret:
        json_exit(
            {
                "success": False,
                "errcode": -1,
                "errmsg": "Missing credentials",
                "hint": "Set WECHAT_MP_APPID and WECHAT_MP_SECRET first",
            },
            1,
        )

    token = get_access_token(appid, secret)
    thumb_media_id = args.thumb_media_id or get_latest_thumb_media_id(token)
    resp = publish_draft(
        token=token,
        title=args.title,
        author=args.author,
        html_content=html_content,
        thumb_media_id=thumb_media_id,
        digest=args.digest,
        content_source_url=args.content_source_url,
    )

    if "media_id" in resp:
        json_exit(
            {
                "success": True,
                "media_id": resp["media_id"],
                "message": "Draft published successfully",
            }
        )

    json_exit(resp, 1)


if __name__ == "__main__":
    main()
