#!/usr/bin/env python3
"""Bounded, non-interactive serial log capture for AI agents (never hangs)."""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

DEFAULT_CRASH_REGEX = r"(Guru Meditation Error|HardFault|assert failed|panic|Backtrace:|Task watchdog got triggered)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture serial output with a strict timeout and optional stop regex.")
    parser.add_argument("--port", help="Serial port (e.g., COM5, /dev/ttyUSB0, /dev/cu.usbserial-0001)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--timeout", type=float, default=10.0, help="Hard capture duration in seconds (default: 10)")
    parser.add_argument("--max-lines", type=int, default=500, help="Maximum lines to capture (default: 500)")
    parser.add_argument("--stop-pattern", help="Regex pattern that stops capture early once matched")
    parser.add_argument("--list-ports", action="store_true", help="List available serial ports and exit")
    parser.add_argument("--out", help="Optional file path to save captured log")
    parser.add_argument("--dry-run", action="store_true", help="Validate arguments and pyserial availability without opening port")
    args = parser.parse_args()

    try:
        import serial  # type: ignore
        from serial.tools import list_ports  # type: ignore
    except ImportError:
        if args.dry_run:
            print("Dry-run OK (note: pyserial is not installed; install with `pip install pyserial`).")
            return 0
        print("Error: pyserial is required. Install with: pip install pyserial", file=sys.stderr)
        return 2

    if args.list_ports:
        ports = list(list_ports.comports())
        if not ports:
            print("No serial ports detected.")
        for p in ports:
            print(f"{p.device}\t{p.description}\t{p.hwid}")
        return 0

    if not args.port:
        parser.error("--port is required unless --list-ports is used")

    if args.dry_run:
        print(f"Dry-run OK: would capture {args.port} @ {args.baud} baud for {args.timeout}s (max {args.max_lines} lines).")
        return 0

    stop_re = re.compile(args.stop_pattern) if args.stop_pattern else None
    crash_re = re.compile(DEFAULT_CRASH_REGEX, re.IGNORECASE)

    lines: list[str] = []
    matched_stop = False
    crash_detected = False
    deadline = time.monotonic() + args.timeout

    with serial.Serial(args.port, args.baud, timeout=0.25) as ser:
        while time.monotonic() < deadline and len(lines) < args.max_lines:
            raw = ser.readline()
            if not raw:
                continue
            text = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            lines.append(text)
            print(text)
            if crash_re.search(text):
                crash_detected = True
            if stop_re and stop_re.search(text):
                matched_stop = True
                break

    if args.out:
        Path(args.out).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    print(
        f"\n[serial_capture] lines={len(lines)} matched_stop={matched_stop} crash_detected={crash_detected}",
        file=sys.stderr,
    )
    return 3 if crash_detected else 0


if __name__ == "__main__":
    raise SystemExit(main())
