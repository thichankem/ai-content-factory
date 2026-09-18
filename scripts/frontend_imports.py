#!/usr/bin/env python3
"""Static import/export checker for the Next.js frontend.

`tsc` is the right tool for this job, but it needs Node.js. On a machine
without Node the frontend cannot be typechecked at all, and a refactor that
moves modules around (as the studio's data layer did) breaks in a narrow,
findable way: an import points at a file that no longer exists, or asks for a
name the target no longer exports. Both are detectable by reading the files,
which is what this script does.

It checks, for every ``.ts``/``.tsx`` file under ``frontend/src``:

1. every import path resolves to a real module (``.ts``, ``.tsx``, or
   ``index.ts``/``index.tsx``);
2. every *named* import exists as an export of the resolved module;
3. every default import has a default export.

Names re-exported through a barrel (``export * from``) cannot be resolved
without a type checker, so those are skipped rather than guessed at. Type-only
imports are checked the same way as value imports because the name still has to
exist.

Usage::

    python scripts/frontend_imports.py            # report problems
    python scripts/frontend_imports.py --quiet    # exit status only

Exit status is 0 when nothing is wrong, 1 otherwise, so it can gate CI.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FRONTEND_SRC = Path("frontend/src")
EXTENSIONS = (".ts", ".tsx")

# `import ... from "path"` and `export ... from "path"`.
_IMPORT_RE = re.compile(
    r"^\s*(?:import|export)\s+(?P<clause>[^;]*?)\s*from\s*[\"'](?P<path>[^\"']+)[\"']",
    re.MULTILINE | re.DOTALL,
)
# Bare `import "path"` side-effect imports.
_SIDE_EFFECT_RE = re.compile(r"^\s*import\s+[\"'](?P<path>[^\"']+)[\"']", re.MULTILINE)

# `export function foo`, `export const foo`, `export class foo`, `export interface
# foo`, `export type foo`, `export enum foo`, `export let foo`.
_EXPORT_DECL_RE = re.compile(
    r"^\s*export\s+(?:declare\s+)?(?:async\s+)?"
    r"(?:function|const|let|var|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
# `export { a, b as c }`
_EXPORT_LIST_RE = re.compile(r"^\s*export\s*\{([^}]*)\}", re.MULTILINE)
# `export * from "..."` — makes named exports unresolvable.
_EXPORT_STAR_RE = re.compile(r"^\s*export\s*\*\s*from", re.MULTILINE)
# `export default`
_EXPORT_DEFAULT_RE = re.compile(r"^\s*export\s+default\b", re.MULTILINE)


def resolve(specifier: str, importer: Path) -> Path | None:
    """Resolve an import specifier to a file, or None if it does not exist."""
    if specifier.startswith("@/"):
        base = FRONTEND_SRC / specifier[2:]
    elif specifier.startswith("."):
        base = (importer.parent / specifier).resolve()
    else:
        return None  # a package: not ours to check

    candidates = [base.with_suffix(ext) for ext in EXTENSIONS]
    candidates += [base / f"index{ext}" for ext in EXTENSIONS]
    # An explicit extension already given (e.g. "./x.ts") lands here.
    candidates.append(base)

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def exported_names(path: Path) -> tuple[set[str], bool, bool]:
    """Return (named exports, has_default, has_star_reexport) for a module."""
    text = path.read_text(encoding="utf-8", errors="replace")

    names = set(_EXPORT_DECL_RE.findall(text))
    for group in _EXPORT_LIST_RE.findall(text):
        for part in group.split(","):
            part = part.strip()
            if not part:
                continue
            # `a as b` exports `b`; a bare `a` exports `a`. `type a` exports `a`.
            part = re.sub(r"^type\s+", "", part)
            if " as " in part:
                names.add(part.split(" as ")[-1].strip())
            else:
                names.add(part)

    return names, bool(_EXPORT_DEFAULT_RE.search(text)), bool(_EXPORT_STAR_RE.search(text))


def named_imports(clause: str) -> list[str]:
    """Extract the names in the `{ ... }` part of an import clause."""
    match = re.search(r"\{(.*)\}", clause, re.DOTALL)
    if not match:
        return []
    found = []
    for part in match.group(1).split(","):
        part = part.strip()
        if not part:
            continue
        part = re.sub(r"^type\s+", "", part)
        # `a as b` imports `a` from the source module.
        name = part.split(" as ")[0].strip()
        if name:
            found.append(name)
    return found


def has_default_import(clause: str) -> bool:
    """True when the clause imports a default binding (not `import * as ns`)."""
    head = clause.split(",", 1)[0]
    if "{" in head or "*" in head:
        return False
    return bool(re.search(r"[A-Za-z_$][\w$]*", head))


def iter_sources() -> list[Path]:
    return sorted(
        path
        for path in FRONTEND_SRC.rglob("*")
        if path.suffix in EXTENSIONS and path.is_file()
    )


def check() -> list[str]:
    problems: list[str] = []
    export_cache: dict[Path, tuple[set[str], bool, bool]] = {}

    for source in iter_sources():
        text = source.read_text(encoding="utf-8", errors="replace")
        rel = source.as_posix()

        specs = [(m.group("clause"), m.group("path")) for m in _IMPORT_RE.finditer(text)]
        specs += [("", m.group("path")) for m in _SIDE_EFFECT_RE.finditer(text)]

        for clause, specifier in specs:
            target = resolve(specifier, source)
            if target is None:
                if specifier.startswith(("@/", ".")):
                    problems.append(f"{rel}: unresolved import -> {specifier}")
                continue

            if target not in export_cache:
                export_cache[target] = exported_names(target)
            names, has_default, has_star = export_cache[target]

            if clause and has_default_import(clause) and not has_default and not has_star:
                problems.append(
                    f"{rel}: default import from {specifier} but it has no default export"
                )

            if has_star:
                continue  # a barrel: cannot resolve names without a type checker

            for name in named_imports(clause):
                if name not in names:
                    problems.append(
                        f"{rel}: '{name}' is not exported by {specifier} "
                        f"({target.as_posix()})"
                    )

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="exit status only")
    args = parser.parse_args()

    if not FRONTEND_SRC.is_dir():
        print(f"error: {FRONTEND_SRC} not found; run from the repository root")
        return 2

    problems = check()
    if not args.quiet:
        total = len(iter_sources())
        if problems:
            print(f"Frontend import check: {len(problems)} problem(s) in {total} files\n")
            for problem in problems:
                print(f"  {problem}")
        else:
            print(f"Frontend import check: clean ({total} files)")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
