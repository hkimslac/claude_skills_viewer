## How to use this script:

Copy the `list_skills.py` into `~/.claude/scripts/` and run the python script.


Below example will provide the list of currently installed skills and put a feature upon startup of claude code to list all the installed skills in the machine.

e.g. python3 list_skills.py --install 


Below example will export the list of installed skills, so that we can replicate the skill tree in another machine or environment. The script will generate another shell script called skills-install.sh. 

e.g. python3 list_skills.py --export skills-install.sh

Below example will import the list of to-be-installed skills.

e.g. python3 list_skills.py --import skills-install.sh (this needs Node/npx package in your CLI environment)


Some things to keep in mind before using the script:
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
