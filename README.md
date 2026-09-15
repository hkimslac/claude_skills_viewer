## How to use this script:

Copy the `list_skills.py` (and optionally `skill_summaries.json`) into `~/.claude/scripts/` and run the python script.


Below example will print the concise list of currently installed skills: the skill name (in gold) followed by a summary of 10 words or less. The name is what you type after `invoke skill`.

`e.g. python3 list_skills.py`

Below example will print the expanded list: the full description from each SKILL.md plus the install path of the skill.

`e.g. python3 list_skills.py --full`

Below example will print the list without any ANSI colors, for piping into a file or a terminal that does not render them. Setting the environment variable `NO_COLOR=1` or `LIST_SKILLS_COLOR=0` does the same.

`e.g. python3 list_skills.py --no-color`

Below example will provide the list of currently installed skills and put a feature upon startup of claude code to list all the installed skills in the machine. The startup splash uses the concise view.

`e.g. python3 list_skills.py --install `


Below example will export the list of installed skills, so that we can replicate the skill tree in another machine or environment. The script will generate another shell script called skills-install.sh. 

`e.g. python3 list_skills.py --export skills-install.sh`

Below example will import the list of to-be-installed skills.

`e.g. python3 list_skills.py --import skills-install.sh (this needs Node/npx package in your CLI environment)`


Some things to keep in mind before using the script:
- The short summaries come from `~/.claude/scripts/skill_summaries.json`, a plain
  `{"skill-name": "summary"}` map you can edit by hand. A skill that is not in that file
  gets an automatic summary instead: the first sentence of its SKILL.md description, with
  lead-ins like "Use when..." stripped, cut to 10 words. The file is optional; if it is
  missing every skill is auto-summarized.
- The startup splash is static text. Claude Code gives hooks no expandable widget, so
  there is no hot-key to unfold the full descriptions in place. Use `--full` instead, or
  type `! python3 ~/.claude/scripts/list_skills.py --full` at the Claude Code prompt to
  get the expanded list inside the session.
- Import is idempotent. It checks what's already on disk and skips those, so re-running
  it is safe and cheap. I verified this: importing on Machine A skipped all nine with no
  network calls.
- Nothing is silently dropped. A skill with no lock entry (one you copied in by hand, or
  one that came from a plugin) can't be reinstalled via npx, so the export lists it in a
  comment block with its path so you know to copy it manually. Tested with a throwaway
  skill, then removed it.
- The exported file is also directly runnable (bash skills-install.sh) if you'd rather
  not use --import; it passes bash -n syntax checking.
- Only global skills are exported. Project-level .claude/skills/ are intentionally
  excluded since those belong with their repository, not your personal setup.
- Failures are reported, not hidden. If a skill fails to install on Machine B (repo
  removed, network down), --import continues with the rest, then lists the failures and
  exits non-zero.

Contact Author:
hkim@slac.stanford.edu
