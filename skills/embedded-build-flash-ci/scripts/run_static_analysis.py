#!/usr/bin/env python3
"""Run cppcheck and/or clang-tidy with embedded C/C++ presets."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run_cppcheck(target: Path, std: str, dry_run: bool) -> int:
    exe = shutil.which("cppcheck")
    if not exe:
        print("[cppcheck] not installed on PATH; skipping.", file=sys.stderr)
        return 127
    cmd = [
        exe,
        f"--std={std}",
        "--enable=warning,style,performance,portability",
        "--inconclusive",
        "--inline-suppr",
        "--suppress=missingIncludeSystem",
        "--error-exitcode=1",
        str(target),
    ]
    print("Running:", " ".join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd, check=False).returncode


def run_clang_tidy(target: Path, compile_db: Path | None, dry_run: bool) -> int:
    exe = shutil.which("clang-tidy")
    if not exe:
        print("[clang-tidy] not installed on PATH; skipping.", file=sys.stderr)
        return 127
    sources = sorted(
        str(p)
        for p in (target.rglob("*") if target.is_dir() else [target])
        if p.suffix.lower() in {".c", ".cc", ".cpp", ".cxx"}
    )
    if not sources:
        print(f"[clang-tidy] no C/C++ source files found under {target}")
        return 0

    checks = "bugprone-*,clang-analyzer-*,cert-err34-c,cert-int09-c"
    cmd = [exe, f"-checks={checks}"]
    if compile_db and compile_db.exists():
        cmd.extend(["-p", str(compile_db.parent if compile_db.is_file() else compile_db)])
    cmd.extend(sources)
    print("Running:", " ".join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run embedded C/C++ static analysis (cppcheck / clang-tidy).")
    parser.add_argument("--path", default="src", help="Source directory or file to analyze (default: src)")
    parser.add_argument("--tool", choices=["auto", "cppcheck", "clang-tidy"], default="auto", help="Analyzer to run")
    parser.add_argument("--std", default="c11", help="C/C++ standard for cppcheck (default: c11)")
    parser.add_argument("--compile-db", help="Path to build dir or compile_commands.json for clang-tidy")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing analyzers")
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"Error: target path not found: {target}", file=sys.stderr)
        return 2

    compile_db = Path(args.compile_db) if args.compile_db else None
    exit_codes: list[int] = []

    if args.tool in ("auto", "cppcheck"):
        rc = run_cppcheck(target, args.std, args.dry_run)
        if rc != 127 or args.tool == "cppcheck":
            exit_codes.append(rc)

    if args.tool in ("auto", "clang-tidy"):
        rc = run_clang_tidy(target, compile_db, args.dry_run)
        if rc != 127 or args.tool == "clang-tidy":
            exit_codes.append(rc)

    if not exit_codes:
        print("Neither cppcheck nor clang-tidy is installed. Install at least one to run static analysis.", file=sys.stderr)
        return 127

    return max(exit_codes)


if __name__ == "__main__":
    raise SystemExit(main())
