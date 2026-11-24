#!/usr/bin/env python3
"""Analyze embedded firmware Flash & RAM usage from an ELF binary or GNU size/nm output."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SIZE_TOOLS = [
    "arm-none-eabi-size",
    "xtensa-esp32-elf-size",
    "xtensa-esp32s3-elf-size",
    "riscv32-esp-elf-size",
    "avr-size",
    "llvm-size",
    "size",
]

NM_TOOLS = [
    "arm-none-eabi-nm",
    "xtensa-esp32-elf-nm",
    "xtensa-esp32s3-elf-nm",
    "riscv32-esp-elf-nm",
    "avr-nm",
    "llvm-nm",
    "nm",
]


def find_tool(candidates: list[str], preferred: str | None = None) -> str | None:
    if preferred:
        return shutil.which(preferred) or (preferred if Path(preferred).is_file() else None)
    for name in candidates:
        found = shutil.which(name)
        if found:
            return found
    return None


def parse_berkeley_size(output: str) -> dict[str, int] | None:
    for line in output.splitlines():
        match = re.match(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+[0-9a-fA-F]+\s+(.+)$", line)
        if match:
            text_sz = int(match.group(1))
            data_sz = int(match.group(2))
            bss_sz = int(match.group(3))
            return {
                "text_bytes": text_sz,
                "data_bytes": data_sz,
                "bss_bytes": bss_sz,
                "flash_bytes": text_sz + data_sz,
                "ram_bytes": data_sz + bss_sz,
            }
    return None


def parse_nm_symbols(output: str, top_n: int) -> list[dict[str, object]]:
    symbols: list[dict[str, object]] = []
    for line in output.splitlines():
        # Format from `nm --size-sort -S -C`: <addr> <size_hex> <type> <name>
        match = re.match(r"^\s*[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s+([A-Za-z?])\s+(.+)$", line)
        if not match:
            continue
        size_bytes = int(match.group(1), 16)
        sym_type = match.group(2)
        sym_name = match.group(3).strip()
        region = "ram" if sym_type in ("b", "B", "d", "D", "g", "G", "s", "S") else "flash"
        symbols.append({
            "name": sym_name,
            "size_bytes": size_bytes,
            "type": sym_type,
            "region": region,
        })
    symbols.sort(key=lambda item: int(item["size_bytes"]), reverse=True)
    return symbols[:top_n]


def parse_map_file(map_path: Path, top_n: int) -> list[dict[str, object]]:
    """Fallback parser for GNU ld .map files when binutils are unavailable."""
    entries: list[dict[str, object]] = []
    pattern = re.compile(r"^\s*(\.[a-zA-Z0-9_.\-$]+)\s+0x[0-9a-fA-F]+\s+0x([0-9a-fA-F]+)\s+(.+)$")
    for line in map_path.read_text(errors="ignore").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        section, size_hex, source = match.group(1), match.group(2), match.group(3).strip()
        size_bytes = int(size_hex, 16)
        if size_bytes == 0:
            continue
        region = "ram" if section.startswith((".bss", ".data", ".noinit")) else "flash"
        entries.append({
            "name": f"{section} ({source})",
            "size_bytes": size_bytes,
            "type": section.split(".")[1] if "." in section[1:] else section,
            "region": region,
        })
    entries.sort(key=lambda item: int(item["size_bytes"]), reverse=True)
    return entries[:top_n]


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Flash and RAM usage of an embedded ELF or map file.")
    parser.add_argument("--elf", help="Path to firmware .elf file")
    parser.add_argument("--map", help="Optional GNU ld .map file for symbol/section breakdown")
    parser.add_argument("--size-tool", help="Explicit path/name of `size` binary")
    parser.add_argument("--nm-tool", help="Explicit path/name of `nm` binary")
    parser.add_argument("--flash-limit", type=int, help="Optional MCU Flash limit in bytes for percent calculation")
    parser.add_argument("--ram-limit", type=int, help="Optional MCU RAM limit in bytes for percent calculation")
    parser.add_argument("--top", type=int, default=15, help="Number of largest symbols to display (default: 15)")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    if not args.elf and not args.map:
        parser.error("Provide --elf and/or --map")

    summary: dict[str, int] | None = None
    top_symbols: list[dict[str, object]] = []
    warnings: list[str] = []

    if args.elf:
        elf_path = Path(args.elf)
        if not elf_path.is_file():
            print(f"Error: ELF file not found: {elf_path}", file=sys.stderr)
            return 2

        size_tool = find_tool(SIZE_TOOLS, args.size_tool)
        if size_tool:
            res = subprocess.run([size_tool, str(elf_path)], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                summary = parse_berkeley_size(res.stdout)
            else:
                warnings.append(f"{size_tool} failed: {res.stderr.strip()}")
        else:
            warnings.append("No `size` binary found on PATH (install arm-none-eabi-size / esp-idf / binutils).")

        nm_tool = find_tool(NM_TOOLS, args.nm_tool)
        if nm_tool:
            res = subprocess.run([nm_tool, "--size-sort", "-S", "-C", str(elf_path)], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                top_symbols = parse_nm_symbols(res.stdout, args.top)
            else:
                warnings.append(f"{nm_tool} failed: {res.stderr.strip()}")
        else:
            warnings.append("No `nm` binary found on PATH; pass --map for symbol breakdown.")

    if args.map and not top_symbols:
        map_path = Path(args.map)
        if not map_path.is_file():
            print(f"Error: Map file not found: {map_path}", file=sys.stderr)
            return 2
        top_symbols = parse_map_file(map_path, args.top)

    result: dict[str, object] = {
        "summary": summary,
        "top_symbols": top_symbols,
        "warnings": warnings,
    }
    if summary and args.flash_limit:
        result["flash_percent"] = round(summary["flash_bytes"] * 100.0 / args.flash_limit, 2)
    if summary and args.ram_limit:
        result["ram_percent"] = round(summary["ram_bytes"] * 100.0 / args.ram_limit, 2)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    if summary:
        print("=== Firmware Footprint ===")
        flash_pct = f" ({result['flash_percent']}%)" if "flash_percent" in result else ""
        ram_pct = f" ({result['ram_percent']}%)" if "ram_percent" in result else ""
        print(f"  Flash (.text + .data): {summary['flash_bytes']:,} bytes{flash_pct}")
        print(f"  RAM   (.data + .bss) : {summary['ram_bytes']:,} bytes{ram_pct}")
        print(f"    .text: {summary['text_bytes']:,} | .data: {summary['data_bytes']:,} | .bss: {summary['bss_bytes']:,}")

    if top_symbols:
        print(f"\n=== Top {len(top_symbols)} Symbols / Sections ===")
        for sym in top_symbols:
            print(f"  {int(sym['size_bytes']):>9,} B  [{sym['region']:<5}] ({sym['type']}) {sym['name']}")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
