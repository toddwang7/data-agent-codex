# Release Notes

This repository is prepared for GitHub-first sharing.

## Before publishing

- Verify `.env.local` is not committed.
- Do not commit private raw data files.
- Keep local machine paths out of public-facing docs.
- Prefer screenshots or demo video links over bundling source data.

## Suggested first publish flow

```bash
cd "data agent-codex"
git init
git add .
git commit -m "feat: initial public prototype release v0.7.0"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

## Suggested tags

```bash
git tag v0.7.0
git push origin v0.7.0
```

## What this release is good for

- portfolio demo
- design + engineering showcase
- local-first product prototype
- configurable agent workflow example
