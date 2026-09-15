#!/usr/bin/env bash
# Claude Code skill set exported by list_skills.py.
# Re-create it on another machine with:
#   python3 list_skills.py --import <this file>
# or run this file directly (requires node/npx). Then register the splash:
#   python3 list_skills.py --install
set -u

SKILLS=(
  imbad0202/academic-research-skills@academic-paper
  imbad0202/academic-research-skills@academic-paper-reviewer
  vercel-labs/skills@find-skills
  lyndonkl/claude@grant-proposal-assistant
  bahayonghang/academic-writing-skills@latex-paper-en
  bahayonghang/academic-writing-skills@paper-audit
  ailabs-393/ai-labs-claude-skills@research-paper-writer
  aminblg/simpleenglish@simple-english
  riekelt/technical-writer@technical-writing
)

for s in "${SKILLS[@]}"; do
  echo "==> $s"
  npx -y skills add "$s" -g -y || echo "!! failed: $s" >&2
done
