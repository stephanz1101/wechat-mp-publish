# WeChat MP Publish Skill

Upload finished article HTML into the WeChat Official Account draft box through the MP API.

This repository is the publishing half of the workflow. It should be paired with `wechat-layout-html` when the user cares about stable 公众号排版 instead of generic Markdown rendering.

## Install

### Codex

Clone this repository into your Codex skills directory:

```bash
git clone https://github.com/stephanz1101/wechat-mp-publish.git ~/.codex/skills/wechat-mp-publish
```

If the directory already exists, update it with:

```bash
cd ~/.codex/skills/wechat-mp-publish && git pull
```

### Required Companion Skill

For house-style WeChat layout, also install:

```bash
git clone https://github.com/stephanz1101/wechat-layout-html.git ~/.codex/skills/wechat-layout-html
```

## Recommended Workflow

1. Use `wechat-layout-html` to turn Markdown or article drafts into final WeChat-safe HTML.
2. Use `wechat-mp-publish` to upload that HTML into the WeChat draft box.

Do not treat this repository's bundled Markdown renderer as the primary layout engine when strict 公众号排版 is required.

## Agent Prompt Examples

Use prompts like these after installation:

```text
Use wechat-mp-publish to upload this finished HTML article to my WeChat Official Account draft box.
```

```text
把这篇文章发到微信公众号草稿箱。
```

```text
先按微信公众号排版规则生成最终 HTML，再上传到公众号草稿箱。
```

```text
Re-layout this Markdown with wechat-layout-html first, then send the final HTML to my WeChat MP draft box.
```

## Environment Variables

The publish script expects:

- `WECHAT_MP_APPID`
- `WECHAT_MP_SECRET`

If the MP API returns `errcode: 40164`, add the reported IP to:

- 微信公众平台 -> 设置与开发 -> 基本配置 -> IP白名单

## Files

```text
wechat-mp-publish/
├── agents/
│   └── openai.yaml
├── SKILL.md
├── README.md
└── scripts/
    ├── publish.py
    └── publish_article_file.py
```

## Notes

- use this repo for draft upload
- use `wechat-layout-html` for layout
- use both together for production-grade WeChat publishing
