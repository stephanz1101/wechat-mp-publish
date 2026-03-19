#!/usr/bin/env python3
"""WeChat MP Draft Publisher — publish articles to 微信公众号草稿箱."""

import argparse
import json
import os
import re
import sys
import urllib.request


def get_access_token(appid: str, secret: str) -> str:
    url = (
        f"https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={appid}&secret={secret}"
    )
    resp = json.loads(urllib.request.urlopen(url, timeout=15).read())
    if "access_token" not in resp:
        code = resp.get("errcode", "unknown")
        msg = resp.get("errmsg", "")
        hint = ""
        if code == 40164:
            ip = re.search(r"invalid ip (\S+)", msg)
            ip_str = ip.group(1) if ip else "unknown"
            hint = f"Add IP {ip_str} to your whitelist at 设置与开发 → 基本配置 → IP白名单"
        elif code == 40001:
            hint = "Check that WECHAT_MP_APPID and WECHAT_MP_SECRET are correct"
        print(json.dumps({"success": False, "errcode": code, "errmsg": msg, "hint": hint}, ensure_ascii=False))
        sys.exit(1)
    return resp["access_token"]


def get_latest_thumb(token: str) -> str:
    url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={token}"
    data = json.dumps({"type": "image", "offset": 0, "count": 1}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    items = resp.get("item", [])
    if not items:
        print(json.dumps({"success": False, "errcode": -1, "errmsg": "No images in material library", "hint": "Upload at least one image to your 素材库 first"}, ensure_ascii=False))
        sys.exit(1)
    return items[0]["media_id"]


def _inline_fmt(text: str) -> str:
    """Apply bold and inline code formatting."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(
        r"`([^`]+)`",
        r'<code style="background:#f6f8fa;border-radius:3px;padding:2px 6px;font-family:Menlo,Consolas,monospace;font-size:13px;color:#24292e;">\1</code>',
        text,
    )
    return text


def markdown_to_html(text: str, font_size="15px", line_height="2", color="#333", heading_size="20px") -> str:
    lines = text.strip().split("\n")
    html_parts = [f'<section style="font-size:{font_size};line-height:{line_height};color:{color};padding:10px;">']

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # Fenced code block (``` ... ```)
        if line.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i].rstrip())
                i += 1
            if i < len(lines):
                i += 1  # skip closing ```
            code_html = "\n".join(code_lines).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(
                f'<section style="background:#f6f8fa;border-radius:6px;padding:14px 16px;margin:12px 0;'
                f'font-family:Menlo,Consolas,monospace;font-size:13px;line-height:1.6;'
                f'color:#24292e;overflow-x:auto;white-space:pre-wrap;word-break:break-all;">'
                f'{code_html}</section>'
            )
            continue

        # Markdown table
        if "|" in line and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
            table_lines = [line]
            i += 1
            # skip separator row
            i += 1
            while i < len(lines) and "|" in lines[i].strip() and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            # Build HTML table
            header_cells = [c.strip() for c in table_lines[0].strip("|").split("|")]
            html_parts.append(
                '<table style="width:100%;border-collapse:collapse;margin:15px 0;font-size:14px;">'
            )
            html_parts.append("<thead><tr>")
            for cell in header_cells:
                cell = _inline_fmt(cell)
                html_parts.append(
                    f'<th style="background:#f5f5f5;padding:10px 12px;border:1px solid #e0e0e0;text-align:left;font-weight:bold;">{cell}</th>'
                )
            html_parts.append("</tr></thead><tbody>")
            for row_line in table_lines[1:]:
                cells = [c.strip() for c in row_line.strip("|").split("|")]
                html_parts.append("<tr>")
                for cell in cells:
                    cell = _inline_fmt(cell)
                    html_parts.append(
                        f'<td style="padding:10px 12px;border:1px solid #e0e0e0;">{cell}</td>'
                    )
                html_parts.append("</tr>")
            html_parts.append("</tbody></table>")
            continue

        # Inline formatting (bold + code)
        line = _inline_fmt(line)

        # Section heading: short line, no period, often a noun phrase
        if len(line) < 30 and not line.endswith(("。", "，", "、", ".", ",")) and not re.match(r"^\d+[\.\、]", line):
            html_parts.append(
                f'<p style="font-size:{heading_size};font-weight:bold;margin-top:30px;margin-bottom:15px;">{line}</p>'
            )
            i += 1
            continue

        # Numbered bold item: "1. Title" or "**1. Title**"
        m = re.match(r"^(\d+)[\.\、]\s*(.+)", line)
        if m:
            html_parts.append(f"<p><strong>{m.group(1)}. {m.group(2)}</strong></p>")
            i += 1
            # Collect following paragraph lines
            para_lines = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^\d+[\.\、]", lines[i].strip()) and not lines[i].strip().startswith("```"):
                para_lines.append(_inline_fmt(lines[i].strip()))
                i += 1
            if para_lines:
                html_parts.append(f'<p>{"<br/>".join(para_lines)}</p>')
            continue

        # Regular paragraph — collect consecutive non-empty lines
        para_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("```"):
            para_lines.append(_inline_fmt(lines[i].strip()))
            i += 1
        html_parts.append(f'<p>{"<br/>".join(para_lines)}</p>')

    html_parts.append("</section>")
    return "\n\n".join(html_parts)


def publish_draft(token: str, title: str, author: str, html_content: str, thumb_media_id: str):
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    data = {
        "articles": [{
            "title": title,
            "author": author,
            "content": html_content,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }]
    }
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())

    if "media_id" in resp:
        print(json.dumps({"success": True, "media_id": resp["media_id"], "message": "Draft published successfully"}, ensure_ascii=False))
    else:
        code = resp.get("errcode", "unknown")
        msg = resp.get("errmsg", "")
        print(json.dumps({"success": False, "errcode": code, "errmsg": msg, "hint": ""}, ensure_ascii=False))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Publish article to WeChat MP draft box")
    parser.add_argument("--title", required=True, help="Article title")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--content-file", help="Path to content file (plain text / markdown)")
    parser.add_argument("--content-from-stdin", action="store_true", help="Read content from stdin")
    parser.add_argument("--font-size", default="15px")
    parser.add_argument("--line-height", default="2")
    parser.add_argument("--color", default="#333")
    parser.add_argument("--heading-size", default="20px")
    parser.add_argument("--thumb-media-id", default=None, help="Cover image media_id (default: latest from library)")
    args = parser.parse_args()

    appid = os.environ.get("WECHAT_MP_APPID")
    secret = os.environ.get("WECHAT_MP_SECRET")
    if not appid or not secret:
        print(json.dumps({
            "success": False,
            "errcode": -1,
            "errmsg": "Missing credentials",
            "hint": "Set WECHAT_MP_APPID and WECHAT_MP_SECRET environment variables"
        }, ensure_ascii=False))
        sys.exit(1)

    # Read content
    if args.content_from_stdin:
        content = sys.stdin.read()
    elif args.content_file:
        with open(args.content_file, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        print(json.dumps({"success": False, "errcode": -1, "errmsg": "No content provided", "hint": "Use --content-file or --content-from-stdin"}, ensure_ascii=False))
        sys.exit(1)

    # Convert to HTML
    html = markdown_to_html(content, args.font_size, args.line_height, args.color, args.heading_size)

    # Get token
    token = get_access_token(appid, secret)

    # Get cover image
    thumb = args.thumb_media_id or get_latest_thumb(token)

    # Publish
    publish_draft(token, args.title, args.author, html, thumb)


if __name__ == "__main__":
    main()
