#!/usr/bin/env python3
# Generated from _tools/scripts/module_agentic_config_check.py by _tools/scripts/sync-module-agent-config.py; do not edit.
"""Verify generated agent configuration in one standalone ASMA module clone.

This file is copied into a materialized module as
``.github/scripts/check-agentic-config.py``. It uses only the Python standard
library and never reads the superproject, so it works in a standalone clone
(which is how CI checks a child repository out).

It verifies that every generated file recorded in
``.github/agentic-config.lock.json`` exists as a regular file with the recorded
SHA-256, and that no symlink under ``.github/`` or ``.agents/`` escapes the
repository. That second check is the hard standalone rule: a link into the
superproject dangles as soon as the child is cloned alone.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ROOT / ".github" / "agentic-config.lock.json"
SCANNED = (".github", ".agents")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if not MANIFEST.is_file():
        print(f"[ERROR] missing {MANIFEST.relative_to(ROOT)}; run the catalog sync for this module")
        return 1
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERROR] invalid {MANIFEST.relative_to(ROOT)}: {exc}")
        return 1
    if manifest.get("version") != 1:
        print(f"[ERROR] unsupported manifest version: {manifest.get('version')!r}")
        return 1

    errors: list[str] = []
    generated = manifest.get("generated")
    if not isinstance(generated, dict) or not generated:
        errors.append("manifest has no generated files")
        generated = {}

    for relative, entry in sorted(generated.items()):
        path = ROOT / relative
        if path.is_symlink():
            errors.append(f"generated file was replaced by a symlink: {relative}")
        elif not path.is_file():
            errors.append(f"generated file is missing: {relative}")
        elif not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
            errors.append(f"manifest entry is invalid: {relative}")
        elif sha256(path) != entry["sha256"]:
            errors.append(f"generated file was edited after materialization: {relative}")

    for base in SCANNED:
        directory = ROOT / base
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_symlink():
                continue
            target = path.resolve(strict=False)
            try:
                target.relative_to(ROOT)
            except ValueError:
                errors.append(f"symlink escapes the repository: {path.relative_to(ROOT)} -> {path.readlink()}")
            else:
                if not path.exists():
                    errors.append(f"broken symlink: {path.relative_to(ROOT)} -> {path.readlink()}")

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        print(f"\n{len(errors)} problem(s); regenerate from the catalog instead of editing generated files.")
        return 1

    print(f"OK - {len(generated)} generated file(s) match {MANIFEST.relative_to(ROOT)}; no escaping symlinks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
