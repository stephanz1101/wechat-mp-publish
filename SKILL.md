---
name: wechat-mp-publish
description: 发送文章到微信公众号草稿箱。Use when the user wants to upload an article to 微信公众号, create a 公众号 draft, 发到公众号, 推送到草稿箱, or publish finished content into the WeChat Official Account draft box.
---

# WeChat MP Publish

Publish an article to the WeChat Official Account draft box via the MP API.

## When to use

Use this skill when:

- the user says `发到公众号`
- the user wants a `微信公众号草稿`
- the user has finished writing and wants the article uploaded to the MP draft box
- the user wants to preview the rendered WeChat HTML before uploading

## Prerequisites

This workflow expects these environment variables:

- `WECHAT_MP_APPID`
- `WECHAT_MP_SECRET`

If either is missing, tell the user to get them from:

- 微信公众平台 -> 设置与开发 -> 基本配置

If the API returns `errcode: 40164`, extract the IP from the error and tell the user to add it to:

- 微信公众平台 -> 设置与开发 -> 基本配置 -> IP白名单

## Default workflow

1. Find the article content from the current conversation or an existing markdown/text file.
2. Decide the title.
3. If the input is Markdown or an article draft, first generate final WeChat-safe HTML with `wechat-layout-html`.
4. Upload the final HTML to the draft box.
5. Report the result clearly.

## Layout-first rule

When the user asks to `排版并上传`, `重新排版上传`, `按微信公众号排版规则发草稿箱`, or gives a Markdown article and wants a draft:

- Do not use this skill's built-in Markdown renderer as the final layout engine.
- Do use `wechat-layout-html` first, with the locked blue div-only style.
- Then upload the generated HTML content through the WeChat API.
- If the input is already final WeChat-safe HTML, upload it directly.

The bundled renderer in `publish.py` is only a fallback for simple drafts. It is not the house-style renderer.

## Script fallback

For simple content without the house style requirement, run the bundled publish script in one of two modes:
   - `--dry-run` to render WeChat-friendly HTML locally first
   - normal mode to upload into the draft box

If the article already follows your standard local format with:

- `# 标题`
- `## 正文`

prefer the bundled shortcut script `publish_article_file.py`.

## Recommended usage

### Dry run first

```bash
python3 <skill-path>/scripts/publish.py \
  --title "文章标题" \
  --content-file /path/to/article.md \
  --dry-run \
  --output-html /tmp/wechat-preview.html
```

### Upload to draft box

```bash
python3 <skill-path>/scripts/publish.py \
  --title "文章标题" \
  --author "作者名" \
  --content-file /path/to/article.md
```

### Upload directly from an article file

```bash
python3 <skill-path>/scripts/publish_article_file.py \
  /path/to/article.md
```

This script automatically:

- extracts the first `# 标题`
- extracts everything after `## 正文`
- sends the result through `publish.py`

### Dry run directly from an article file

```bash
python3 <skill-path>/scripts/publish_article_file.py \
  /path/to/article.md \
  --dry-run \
  --output-html /tmp/wechat-preview.html
```

### Read content from stdin

```bash
cat /path/to/article.md | python3 <skill-path>/scripts/publish.py \
  --title "文章标题" \
  --author "作者名" \
  --content-from-stdin
```

## Supported options

- `--title` article title
- `--author` author name
- `--content-file` article file path
- `--content-from-stdin` read content from stdin
- `--thumb-media-id` use a specific cover image media id
- `--font-size`
- `--line-height`
- `--color`
- `--heading-size`
- `--subheading-size`
- `--dry-run` render HTML only, do not call WeChat API
- `--output-html` write rendered HTML to a file

`publish_article_file.py` accepts the same styling and publishing options, while deriving title and body automatically from the article file.

If `--thumb-media-id` is omitted, the script fetches the latest image from the account's material library.

## Output behavior

On success, the script prints JSON such as:

```json
{"success": true, "media_id": "...", "message": "Draft published successfully"}
```

On dry run, it prints JSON such as:

```json
{"success": true, "mode": "dry-run", "html_file": "/tmp/wechat-preview.html"}
```

On failure, it prints structured JSON with `errcode`, `errmsg`, and a `hint` when possible.

## Notes

- Prefer markdown files with clear headings and paragraphs.
- For deep articles, keep headings explicit instead of relying on accidental short lines.
- If the user wants to use a custom cover later, extend this skill rather than manually editing the script each time.
