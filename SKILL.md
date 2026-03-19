---
name: wechat-mp-publish
description: Publish articles to WeChat Official Account (微信公众号) draft box. Use this skill whenever the user wants to publish, post, or send an article to their WeChat public account, create a WeChat MP draft, push content to 公众号, or mentions 微信公众号发布/草稿箱. Also trigger when the user has finished writing an article and wants to publish it to WeChat, even if they just say "发到公众号" or "推送到草稿箱".
---

# WeChat MP Publish

Publish articles to a WeChat Official Account draft box via the MP API.

## Prerequisites

The user needs two environment variables set:
- `WECHAT_MP_APPID` — the AppID from 微信公众平台 → 设置与开发 → 基本配置
- `WECHAT_MP_SECRET` — the AppSecret from the same page

If either is missing, tell the user where to find them and help them set the env vars.

The user's current IP must be in the 公众号 IP whitelist. If you get an `errcode: 40164` response, extract the IP from the error message and tell the user to add it at: 设置与开发 → 基本配置 → IP白名单.

## Workflow

### 1. Gather article content

You need at minimum:
- **title** — the article headline
- **content** — the article body (plain text or markdown; you'll convert it to HTML)
- **author** — defaults to the account name if not provided

The content often comes from the current conversation — the user may have just finished writing or editing an article with you. Look for it in context before asking.

### 2. Convert content to WeChat-compatible HTML

WeChat MP has specific HTML requirements. Use the bundled `scripts/publish.py` which handles the conversion. The default styling is:

```
font-size: 15px
line-height: 2
color: #333
```

The user can customize styling by providing overrides. Supported options:
- `font_size` — e.g., "16px", "14px"
- `line_height` — e.g., "1.8", "2.5"
- `color` — e.g., "#555", "#222"
- `heading_size` — size for section headings, e.g., "20px"

The script converts markdown-like content to HTML:
- Paragraphs become `<p>` tags
- Lines starting with `**N.` become bold numbered items
- Section headings (lines that are short and look like titles) become styled headings
- `**text**` becomes `<strong>text</strong>`
- Line breaks within logical blocks become `<br/>`

### 3. Select cover image

By default, fetch the most recent image from the account's material library. The script handles this automatically — it calls `batchget_material` and picks the first image's `media_id`.

### 4. Publish to draft box

The script calls the draft API (`/cgi-bin/draft/add`) and returns the `media_id` of the created draft. Tell the user the draft is ready and they can find it in 微信公众平台 → 草稿箱.

## Usage

Run the bundled script:

```bash
python3 <skill-path>/scripts/publish.py \
  --title "文章标题" \
  --author "作者名" \
  --content-file /path/to/content.txt \
  [--font-size 15px] \
  [--line-height 2] \
  [--color "#333"] \
  [--heading-size 20px] \
  [--thumb-media-id MEDIA_ID]
```

Or pass content via stdin:

```bash
echo "文章内容" | python3 <skill-path>/scripts/publish.py \
  --title "文章标题" \
  --author "作者名" \
  --content-from-stdin
```

The script reads `WECHAT_MP_APPID` and `WECHAT_MP_SECRET` from environment variables.

### Output

On success, the script prints JSON:
```json
{"success": true, "media_id": "...", "message": "Draft published successfully"}
```

On failure, it prints the error with guidance:
```json
{"success": false, "errcode": 40164, "errmsg": "invalid ip ...", "hint": "Add IP x.x.x.x to your whitelist at 设置与开发 → 基本配置 → IP白名单"}
```

## Typical flow

1. Write the article content to a temp file
2. Run the publish script with title, author, and content
3. Report the result to the user
4. If IP whitelist error, guide the user to add the IP and retry
