#!/usr/bin/env python3
"""Collect verifiable facts about a project directory for writing a promo storyboard.

    python scan_project.py /path/to/project > facts.json

Prints JSON: identity (name, description, homepage), README outline, languages,
size, dependencies, CLI/install hints, git history, and candidate visual assets
(screenshots, logos) with pixel sizes. Everything is read-only.
"""
import json, os, re, subprocess, sys, struct
from collections import Counter
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", "dist", "build", ".next", "out",
             "target", ".idea", ".vscode", "vendor", "coverage", ".cache", ".tox", "site-packages", ".turbo"}
LANG = {".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
        ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".java": "Java", ".kt": "Kotlin", ".swift": "Swift",
        ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".cs": "C#", ".php": "PHP",
        ".vue": "Vue", ".svelte": "Svelte", ".dart": "Dart", ".scala": "Scala", ".ex": "Elixir", ".exs": "Elixir",
        ".lua": "Lua", ".sh": "Shell", ".zig": "Zig", ".css": "CSS", ".scss": "CSS", ".html": "HTML", ".sql": "SQL"}
IMG = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def img_size(p):
    try:
        with open(p, "rb") as f:
            head = f.read(32)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", head[16:24])
            if head[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    m, = struct.unpack(">H", f.read(2)); ln, = struct.unpack(">H", f.read(2))
                    if 0xFFC0 <= m <= 0xFFCF and m not in (0xFFC4, 0xFFC8, 0xFFCC):
                        f.read(1); h, w = struct.unpack(">HH", f.read(4)); return (w, h)
                    f.seek(ln - 2, 1)
            if head[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", head[6:10])
            if p.suffix.lower() == ".svg":
                txt = p.read_text(errors="ignore")[:2000]
                vb = re.search(r'viewBox="[\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+([\d.]+)"', txt)
                if vb: return (int(float(vb.group(1))), int(float(vb.group(2))))
    except Exception:
        pass
    return None


def read(p, limit=200_000):
    try: return p.read_text(errors="ignore")[:limit]
    except Exception: return ""


def git(root, *args):
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


def main(root):
    root = Path(root).resolve()
    facts = {"path": str(root), "name": root.name}
    langs, files, loc = Counter(), 0, 0
    images, tests = [], 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in fns:
            p = Path(dp) / fn; ext = p.suffix.lower(); files += 1
            if ext in LANG:
                n = read(p).count("\n"); langs[LANG[ext]] += n; loc += n
                if re.search(r"(^test_|_test\.|\.test\.|\.spec\.)", fn): tests += 1
            if ext in IMG and not re.search(r"(^|/)fonts?/", str(p.relative_to(root)).lower()):
                rel = str(p.relative_to(root)); size = img_size(p)
                low = rel.lower()
                kind = "logo" if re.search(r"logo|icon|brand|mark", low) else \
                       "screenshot" if re.search(r"screen|shot|demo|preview|hero|banner|ui", low) else "image"
                if size and size[0] >= 600 and kind == "image": kind = "maybe-screenshot"
                images.append({"path": rel, "size": size, "kind": kind, "bytes": p.stat().st_size})
    total = sum(langs.values()) or 1
    facts["languages"] = [{"name": k, "lines": v, "share": round(v / total, 3)} for k, v in langs.most_common(6)]
    facts["files"] = files; facts["lines_of_code"] = loc; facts["test_files"] = tests
    images.sort(key=lambda i: ({"logo": 0, "screenshot": 1, "maybe-screenshot": 2}.get(i["kind"], 3), -(i["bytes"])))
    facts["images"] = images[:25]

    # Manifests
    pj = root / "package.json"
    if pj.exists():
        try:
            d = json.loads(read(pj))
            facts.update({k: d[k] for k in ("description", "homepage", "license", "keywords") if d.get(k)})
            facts["name"] = d.get("name", facts["name"]); facts["version"] = d.get("version")
            facts["dependencies"] = len(d.get("dependencies", {})); facts["dev_dependencies"] = len(d.get("devDependencies", {}))
            facts["scripts"] = list(d.get("scripts", {}).keys())[:12]
            if d.get("bin"): facts["cli"] = list(d["bin"]) if isinstance(d["bin"], dict) else [facts["name"]]
            facts["install"] = f"npm install {facts['name']}"
            if isinstance(d.get("repository"), dict): facts["repository"] = d["repository"].get("url")
        except Exception: pass
    pp = root / "pyproject.toml"
    if pp.exists():
        txt = read(pp)
        for key in ("name", "description", "version", "license"):
            m = re.search(rf'^{key}\s*=\s*"([^"]+)"', txt, re.M)
            if m: facts[key] = m.group(1)
        deps = re.search(r"dependencies\s*=\s*\[(.*?)\]", txt, re.S)
        if deps: facts["dependencies"] = len(re.findall(r'"[^"]+"', deps.group(1)))
        scripts = re.search(r"\[project\.scripts\](.*?)(\n\[|\Z)", txt, re.S)
        if scripts: facts["cli"] = re.findall(r"^(\S+)\s*=", scripts.group(1), re.M)
        facts["install"] = f"pip install {facts.get('name', root.name)}"
    for mf, label in (("Cargo.toml", "cargo"), ("go.mod", "go")):
        if (root / mf).exists():
            txt = read(root / mf)
            m = re.search(r'^name\s*=\s*"([^"]+)"', txt, re.M) or re.search(r"^module\s+(\S+)", txt, re.M)
            if m: facts["name"] = [p for p in m.group(1).split("/") if not re.fullmatch(r"v\d+", p)][-1]
            d = re.search(r'^description\s*=\s*"([^"]+)"', txt, re.M)
            if d: facts["description"] = d.group(1)
            facts["install"] = f"cargo install {facts['name']}" if label == "cargo" else f"go install {m.group(1) if m else ''}@latest"

    # README outline: headings + first paragraph + code blocks that look like install/usage commands
    readme = next((p for p in root.iterdir() if p.is_file() and p.name.lower().startswith("readme")), None)
    if readme:
        txt = read(readme, 60_000)
        facts["readme_file"] = readme.name
        facts["readme_headings"] = re.findall(r"^#{1,3}\s+(.+)$", txt, re.M)[:30]
        body = re.sub(r"<[^>]+>|!\[[^\]]*\]\([^)]*\)|\[!\[.*?\]\(.*?\)\]\(.*?\)", "", txt)
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip() and not p.strip().startswith(("#", "```", "|", "-", "*", ">"))]
        facts["readme_intro"] = " ".join(paras[:2])[:800]
        cmds = re.findall(r"^\s*\$?\s*((?:npm|npx|pnpm|yarn|pip|pipx|uv|brew|cargo|go|docker|curl)\s[^\n]{2,80})$", txt, re.M)
        facts["readme_commands"] = list(dict.fromkeys(c.strip() for c in cmds))[:10]
        facts["readme_images"] = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", txt)[:10]

    # Git history
    if (root / ".git").exists():
        facts["git"] = {
            "commits": int(git(root, "rev-list", "--count", "HEAD") or 0),
            "contributors": len(set(git(root, "log", "--format=%ae").splitlines())),
            "first_commit": git(root, "log", "--reverse", "--format=%ad", "--date=short").split("\n")[0],
            "last_commit": git(root, "log", "-1", "--format=%ad", "--date=short"),
            "remote": git(root, "remote", "get-url", "origin"),
        }
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
