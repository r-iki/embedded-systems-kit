#!/usr/bin/env python3
"""Extract and decode ESP32 or ARM Cortex-M crash addresses using addr2line."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ADDR2LINE_TOOLS = [
    "xtensa-esp32-elf-addr2line",
    "xtensa-esp32s3-elf-addr2line",
    "riscv32-esp-elf-addr2line",
    "arm-none-eabi-addr2line",
    "llvm-symbolizer",
    "addr2line",
]

ESP_BACKTRACE_RE = re.compile(r"Backtrace:\s*(.+)")
ESP_PAIR_RE = re.compile(r"(0x4[0-9a-fA-F]{7}):0x[0-9a-fA-F]{8}")
REG_ADDR_RE = re.compile(r"\b(?:PC|LR|MEPC|RA)\s*[:=]\s*(0x[0-9a-fA-F]{6,8})\b", re.IGNORECASE)
EXCVADDR_RE = re.compile(r"\bEXCVADDR\s*[:=]\s*(0x[0-9a-fA-F]{8})\b", re.IGNORECASE)
GURU_REASON_RE = re.compile(r"Guru Meditation Error:.*?\(([^)]+)\)")
CFSR_RE = re.compile(r"\bCFSR\s*[:=]\s*(0x[0-9a-fA-F]{1,8})\b", re.IGNORECASE)


def extract_crash_info(text: str) -> dict[str, object]:
    addresses: list[str] = []
    seen: set[str] = set()

    def add_addr(addr: str) -> None:
        norm = addr.lower()
        if norm not in seen:
            seen.add(norm)
            addresses.append(addr)

    for match in REG_ADDR_RE.finditer(text):
        add_addr(match.group(1))

    for bt_line in ESP_BACKTRACE_RE.findall(text):
        for pair in ESP_PAIR_RE.findall(bt_line):
            add_addr(pair)

    reason_match = GURU_REASON_RE.search(text)
    excv_match = EXCVADDR_RE.search(text)
    cfsr_match = CFSR_RE.search(text)

    hints: list[str] = []
    if reason_match:
        reason = reason_match.group(1)
        hints.append(f"ESP32 panic reason: {reason}")
        if "Cache disabled" in reason:
            hints.append("Likely ISR or callback missing IRAM_ATTR or reading Flash const data during Flash write.")
    if excv_match:
        excv_val = int(excv_match.group(1), 16)
        if excv_val < 0x1000:
            hints.append(f"EXCVADDR={excv_match.group(1)} is near zero -> likely NULL pointer dereference.")
        elif excv_val == 0xA5A5A5A5:
            hints.append("EXCVADDR=0xA5A5A5A5 -> FreeRTOS stack/heap fill pattern (uninitialized pointer or use-after-free).")
    if cfsr_match:
        cfsr_val = int(cfsr_match.group(1), 16)
        flags = []
        if cfsr_val & (1 << 0):
            flags.append("IACCVIOL")
        if cfsr_val & (1 << 1):
            flags.append("DACCVIOL")
        if cfsr_val & (1 << 9):
            flags.append("PRECISERR (check BFAR)")
        if cfsr_val & (1 << 10):
            flags.append("IMPRECISERR")
        if cfsr_val & (1 << 12):
            flags.append("STKERR (stack overflow during exception entry)")
        if cfsr_val & (1 << 16):
            flags.append("UNDEFINSTR")
        if cfsr_val & (1 << 17):
            flags.append("INVSTATE")
        if cfsr_val & (1 << 24):
            flags.append("UNALIGNED")
        if cfsr_val & (1 << 25):
            flags.append("DIVBYZERO")
        if flags:
            hints.append(f"Cortex-M CFSR ({cfsr_match.group(1)}) flags: {', '.join(flags)}")

    return {
        "addresses": addresses,
        "hints": hints,
    }


def resolve_addresses(elf: Path, addresses: list[str], tool: str | None) -> tuple[list[dict[str, str]], str | None]:
    exe = shutil.which(tool) if tool else None
    if not exe and tool and Path(tool).is_file():
        exe = tool
    if not exe:
        for cand in ADDR2LINE_TOOLS:
            found = shutil.which(cand)
            if found:
                exe = found
                break
    if not exe:
        return [], "No addr2line binary found on PATH (pass --addr2line <path>)."

    cmd = [exe, "-pfiaC", "-e", str(elf), *addresses]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        return [], f"{exe} failed: {res.stderr.strip()}"

    frames = [{"raw": line.strip()} for line in res.stdout.splitlines() if line.strip()]
    return frames, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse and decode embedded crash dumps via addr2line.")
    parser.add_argument("--elf", help="Path to matching firmware .elf file")
    parser.add_argument("--log", help="Path to text file containing crash log / serial dump")
    parser.add_argument("--addrs", nargs="*", default=[], help="Explicit hex addresses (e.g., 0x400d1234)")
    parser.add_argument("--addr2line", help="Explicit addr2line executable name or path")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    info: dict[str, object] = {"addresses": [], "hints": []}
    if args.log:
        log_path = Path(args.log)
        if not log_path.is_file():
            print(f"Error: log file not found: {log_path}", file=sys.stderr)
            return 2
        info = extract_crash_info(log_path.read_text(errors="ignore"))

    addresses = list(info["addresses"])  # type: ignore[arg-type]
    for addr in args.addrs:
        if addr not in addresses:
            addresses.append(addr)
    info["addresses"] = addresses

    frames: list[dict[str, str]] = []
    warning: str | None = None
    if args.elf and addresses:
        elf_path = Path(args.elf)
        if not elf_path.is_file():
            print(f"Error: ELF file not found: {elf_path}", file=sys.stderr)
            return 2
        frames, warning = resolve_addresses(elf_path, addresses, args.addr2line)

    payload = {
        "addresses": addresses,
        "hints": info["hints"],
        "decoded_frames": frames,
        "warning": warning,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Extracted addresses ({len(addresses)}): {', '.join(addresses) if addresses else 'none'}")
    if info["hints"]:
        print("\nTriage hints:")
        for h in info["hints"]:  # type: ignore[union-attr]
            print(f"  - {h}")
    if frames:
        print("\nDecoded frames:")
        for f in frames:
            print(f"  {f['raw']}")
    if warning:
        print(f"\nNote: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
