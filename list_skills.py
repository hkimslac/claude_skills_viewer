#!/usr/bin/env python3
"""List installed Claude Code skills, optionally as a SessionStart splash.

Portable: Python 3.8+, standard library only, no third-party packages.

Usage
  python3 list_skills.py              # plain table on the terminal
  python3 list_skills.py --hook       # JSON for a Claude Code SessionStart hook
  python3 list_skills.py --install    # register the hook in ~/.claude/settings.json
  python3 list_skills.py --uninstall  # remove the hook again
  python3 list_skills.py --json       # machine-readable skill list
  python3 list_skills.py --export [FILE]   # write an install script for this machine's skills
  python3 list_skills.py --import FILE     # install skills from an exported script

Skill locations scanned
  ~/.claude/skills/<name>/SKILL.md         user (global) skills
  ~/.agents/skills/<name>/SKILL.md         `npx skills` store (deduped against above)
  <project>/.claude/skills/<name>/SKILL.md project skills (from hook cwd or $PWD)

Moving to another machine
  Machine A:  python3 list_skills.py --export skills-install.sh
  Machine B:  python3 list_skills.py --import skills-install.sh   # needs node/npx
              python3 list_skills.py --install
The export reads install sources from ~/.agents/.skill-lock.json, which the
`npx skills` CLI maintains. Skills that were copied in by hand (no lock entry)
are listed as comments in the export so nothing is silently dropped.
The hook is written with the absolute path of wherever this file lives.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HOOK_TAG = "list_skills.py"
DESC_WIDTH = 72


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #

def parse_frontmatter(skill_md: Path) -> dict:
    """Return name/description from a SKILL.md YAML frontmatter block."""
    meta = {"name": skill_md.parent.name, "description": ""}
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return meta
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return meta
    block_key = None
    for line in m.group(1).splitlines():
        if block_key and (line.startswith((" ", "\t")) or not line.strip()):
            meta[block_key] = (meta[block_key] + " " + line.strip()).strip()
            continue
        block_key = None
        kv = re.match(r"^(name|description):\s*(.*)$", line.strip())
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip().strip('"').strip("'")
        if val in ("|", ">", "|-", ">-"):
            meta[key] = ""
            block_key = key
        elif val:
            meta[key] = val
    return meta


def scan_dir(root: Path, source: str, seen: set) -> list:
    found = []
    if not root.is_dir():
        return found
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            key = str(skill_md.resolve())
        except OSError:
            key = str(skill_md)
        if key in seen:
            continue
        seen.add(key)
        info = parse_frontmatter(skill_md)
        info["source"] = source
        info["path"] = str(entry)
        found.append(info)
    return found


def discover_skills(project_dir: Path | None) -> list:
    home = Path.home()
    seen: set = set()
    skills = []
    skills += scan_dir(home / ".claude" / "skills", "user", seen)
    skills += scan_dir(home / ".agents" / "skills", "user", seen)
    if project_dir:
        skills += scan_dir(project_dir / ".claude" / "skills", "project", seen)
    return skills


def read_hook_stdin() -> dict:
    """SessionStart hooks receive JSON on stdin; tolerate a TTY or empty input."""
    if sys.stdin is None or sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError):
        return {}


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def shorten(text: str, width: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def render_plain(skills: list, project_dir: Path | None) -> str:
    if not skills:
        return "No Claude Code skills installed."
    name_w = max(len(s["name"]) for s in skills)
    lines = [f"Installed skills ({len(skills)})"]
    for source in ("user", "project"):
        group = [s for s in skills if s["source"] == source]
        if not group:
            continue
        label = "global" if source == "user" else f"project: {project_dir}"
        lines.append(f"  [{label}]")
        for s in group:
            lines.append(f"    /{s['name']:<{name_w}}  {shorten(s['description'], DESC_WIDTH)}")
    return "\n".join(lines)


def render_hook(skills: list, project_dir: Path | None) -> dict:
    return {"systemMessage": render_plain(skills, project_dir), "suppressOutput": True}


# --------------------------------------------------------------------------- #
# Hook install / uninstall
# --------------------------------------------------------------------------- #

def settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path} is not a JSON object; refusing to modify it.")
    return data


def save_settings(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def hook_command() -> str:
    script = Path(__file__).resolve()
    interpreter = "python" if os.name == "nt" else "python3"
    return f'{interpreter} "{script}" --hook'


def strip_our_hooks(entries: list) -> list:
    kept = []
    for entry in entries:
        hooks = [h for h in entry.get("hooks", []) if HOOK_TAG not in str(h.get("command", ""))]
        if hooks:
            entry = dict(entry, hooks=hooks)
            kept.append(entry)
    return kept


def install_hook() -> None:
    path = settings_path()
    data = load_settings(path)
    hooks = data.setdefault("hooks", {})
    entries = strip_our_hooks(hooks.get("SessionStart", []))
    entries.append({
        "matcher": "startup|resume",
        "hooks": [{
            "type": "command",
            "command": hook_command(),
            "timeout": 10,
            "statusMessage": "Listing installed skills…",
        }],
    })
    hooks["SessionStart"] = entries
    save_settings(path, data)
    print(f"Installed SessionStart hook in {path}:\n  {hook_command()}")
    print("Restart Claude Code (or open /hooks once) for it to take effect.")


def uninstall_hook() -> None:
    path = settings_path()
    data = load_settings(path)
    hooks = data.get("hooks", {})
    if "SessionStart" in hooks:
        entries = strip_our_hooks(hooks["SessionStart"])
        if entries:
            hooks["SessionStart"] = entries
        else:
            del hooks["SessionStart"]
        if not hooks:
            del data["hooks"]
        save_settings(path, data)
    print(f"Removed {HOOK_TAG} hook from {path} (if present).")


# --------------------------------------------------------------------------- #
# Export / import of the skill set
# --------------------------------------------------------------------------- #

def lock_path() -> Path:
    return Path.home() / ".agents" / ".skill-lock.json"


def load_lock() -> dict:
    """Return {skill_name: lock_entry} from the `npx skills` lock file, or {}."""
    path = lock_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    skills = data.get("skills", {}) if isinstance(data, dict) else {}
    return skills if isinstance(skills, dict) else {}


def package_spec(name: str, entry: dict) -> str | None:
    """Build the owner/repo@skill spec that `npx skills add` accepts."""
    source = entry.get("source")
    if entry.get("sourceType") != "github" or not source:
        return None
    return f"{source}@{name}"


def build_export(skills: list) -> str:
    lock = load_lock()
    specs, manual = [], []
    for s in skills:
        if s["source"] != "user":
            continue
        spec = package_spec(s["name"], lock.get(s["name"], {}))
        (specs if spec else manual).append(spec or s)

    lines = [
        "#!/usr/bin/env bash",
        "# Claude Code skill set exported by list_skills.py.",
        "# Re-create it on another machine with:",
        "#   python3 list_skills.py --import <this file>",
        "# or run this file directly (requires node/npx). Then register the splash:",
        "#   python3 list_skills.py --install",
        "set -u",
        "",
        "SKILLS=(",
    ]
    lines += [f"  {spec}" for spec in specs]
    lines += [
        ")",
        "",
        "for s in \"${SKILLS[@]}\"; do",
        "  echo \"==> $s\"",
        "  npx -y skills add \"$s\" -g -y || echo \"!! failed: $s\" >&2",
        "done",
    ]
    if manual:
        lines += ["", "# Not exportable: no `npx skills` lock entry (installed by hand or via a plugin)."]
        lines += ["# Copy these directories yourself if you want them on the target machine:"]
        lines += [f"#   {s['name']}  ({s['path']})" for s in manual]
    return "\n".join(lines) + "\n"


def parse_export(text: str) -> list:
    """Pull the owner/repo@skill specs back out of an exported script."""
    m = re.search(r"^SKILLS=\(\n(.*?)^\)", text, re.DOTALL | re.MULTILINE)
    if not m:
        return []
    specs = []
    for line in m.group(1).splitlines():
        line = line.split("#", 1)[0].strip().strip('"').strip("'")
        if line:
            specs.append(line)
    return specs


def import_skills(script: Path) -> int:
    import shutil
    import subprocess

    specs = parse_export(script.read_text(encoding="utf-8"))
    if not specs:
        print(f"No SKILLS=( ... ) block found in {script}", file=sys.stderr)
        return 1
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        print("npx not found on PATH; install Node.js first (https://nodejs.org).", file=sys.stderr)
        return 1

    already = {s["name"] for s in discover_skills(None)}
    failures = []
    for spec in specs:
        name = spec.rsplit("@", 1)[-1]
        if name in already:
            print(f"--  {spec}  (already installed, skipped)")
            continue
        print(f"==> {spec}")
        rc = subprocess.call([npx, "-y", "skills", "add", spec, "-g", "-y"])
        if rc != 0:
            failures.append(spec)
    if failures:
        print("\nFailed to install:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    print(f"\nDone. {len(specs)} skill(s) processed.")
    return 0


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--hook", action="store_true", help="emit SessionStart hook JSON")
    mode.add_argument("--json", action="store_true", help="emit the raw skill list as JSON")
    mode.add_argument("--install", action="store_true", help="register this script as a SessionStart hook")
    mode.add_argument("--uninstall", action="store_true", help="remove the SessionStart hook")
    mode.add_argument("--export", nargs="?", const="-", metavar="FILE",
                      help="write an install script for this machine's skills (default: stdout)")
    mode.add_argument("--import", dest="import_file", type=Path, metavar="FILE",
                      help="install skills listed in an exported script")
    ap.add_argument("--project", type=Path, help="project directory to scan for .claude/skills")
    args = ap.parse_args(argv)

    if args.install:
        install_hook()
        return 0
    if args.uninstall:
        uninstall_hook()
        return 0
    if args.import_file:
        return import_skills(args.import_file)
    if args.export:
        text = build_export(discover_skills(None))
        if args.export == "-":
            sys.stdout.write(text)
        else:
            out = Path(args.export)
            out.write_text(text, encoding="utf-8")
            try:
                out.chmod(out.stat().st_mode | 0o111)
            except OSError:
                pass
            n = len(parse_export(text))
            print(f"Wrote {out} ({n} skill(s)). On the target machine run:\n"
                  f"  python3 list_skills.py --import {out.name}")
        return 0

    project_dir = args.project
    if project_dir is None and args.hook:
        cwd = read_hook_stdin().get("cwd")
        project_dir = Path(cwd) if cwd else None
    if project_dir is None:
        project_dir = Path.cwd()

    skills = discover_skills(project_dir)

    if args.hook:
        print(json.dumps(render_hook(skills, project_dir), ensure_ascii=False))
    elif args.json:
        print(json.dumps(skills, indent=2, ensure_ascii=False))
    else:
        print(render_plain(skills, project_dir))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # a broken splash must never block Claude Code startup
        if "--hook" in sys.argv:
            print(json.dumps({"systemMessage": f"list_skills.py failed: {exc}"}))
            sys.exit(0)
        raise
