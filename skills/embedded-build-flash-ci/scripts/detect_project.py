#!/usr/bin/env python3
"""Detect embedded firmware build system, MCU hints, and installed CLI toolchains."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

TOOL_CANDIDATES = [
    "pio",
    "platformio",
    "idf.py",
    "esptool.py",
    "esptool",
    "cmake",
    "ninja",
    "make",
    "arm-none-eabi-gcc",
    "arm-none-eabi-size",
    "arm-none-eabi-addr2line",
    "arm-none-eabi-gdb",
    "xtensa-esp32-elf-addr2line",
    "xtensa-esp32s3-elf-addr2line",
    "riscv32-esp-elf-addr2line",
    "openocd",
    "st-flash",
    "STM32_Programmer_CLI",
    "picotool",
    "arduino-cli",
    "cppcheck",
    "clang-tidy",
]


def detect_ecosystems(root: Path) -> list[dict[str, object]]:
    detected: list[dict[str, object]] = []

    if (root / "platformio.ini").is_file():
        envs = []
        for line in (root / "platformio.ini").read_text(errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("[env:") and stripped.endswith("]"):
                envs.append(stripped[5:-1])
        detected.append({
            "ecosystem": "platformio",
            "evidence": "platformio.ini",
            "environments": envs,
            "build_cmd": "pio run",
            "flash_cmd": "pio run -t upload",
        })

    cmake_file = root / "CMakeLists.txt"
    cmake_text = cmake_file.read_text(errors="ignore") if cmake_file.is_file() else ""

    if (root / "sdkconfig").is_file() or (root / "sdkconfig.defaults").is_file() or "IDF_PATH" in cmake_text or "project.cmake" in cmake_text:
        detected.append({
            "ecosystem": "esp-idf",
            "evidence": "sdkconfig / CMakeLists.txt (IDF_PATH)",
            "build_cmd": "idf.py build",
            "flash_cmd": "idf.py -p <PORT> flash",
        })

    if "pico_sdk_import.cmake" in cmake_text or (root / "pico_sdk_import.cmake").is_file():
        detected.append({
            "ecosystem": "pico-sdk",
            "evidence": "pico_sdk_import.cmake",
            "build_cmd": "cmake -B build && cmake --build build",
            "flash_cmd": "picotool load -f -x build/<app>.uf2",
        })

    ioc_files = sorted(p.name for p in root.glob("*.ioc"))
    if ioc_files or (cmake_file.is_file() and ("arm-none-eabi" in cmake_text or "STM32" in cmake_text)):
        detected.append({
            "ecosystem": "stm32-cmake-or-cube",
            "evidence": ", ".join(ioc_files) if ioc_files else "CMakeLists.txt (STM32/ARM)",
            "build_cmd": "cmake -B build && cmake --build build" if cmake_file.is_file() else "make -j",
            "flash_cmd": "openocd -f interface/stlink.cfg -f target/<target>.cfg -c \"program <elf> verify reset exit\"",
        })

    ino_files = sorted(p.name for p in root.glob("*.ino"))
    if ino_files:
        detected.append({
            "ecosystem": "arduino",
            "evidence": ", ".join(ino_files[:5]),
            "build_cmd": "arduino-cli compile --fqbn <FQBN> .",
            "flash_cmd": "arduino-cli upload -p <PORT> --fqbn <FQBN> .",
        })

    if not detected and cmake_file.is_file():
        detected.append({
            "ecosystem": "cmake-generic",
            "evidence": "CMakeLists.txt",
            "build_cmd": "cmake -B build && cmake --build build",
            "flash_cmd": "see project README / CMake targets",
        })

    if not detected and ((root / "Makefile").is_file() or (root / "makefile").is_file()):
        detected.append({
            "ecosystem": "makefile",
            "evidence": "Makefile",
            "build_cmd": "make -j",
            "flash_cmd": "make flash",
        })

    return detected


def find_elf_artifacts(root: Path) -> list[str]:
    candidates: list[str] = []
    for folder in (".pio/build", "build", "Debug", "Release"):
        base = root / folder
        if base.is_dir():
            for elf in base.rglob("*.elf"):
                candidates.append(str(elf.relative_to(root)))
                if len(candidates) >= 10:
                    return candidates
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect embedded firmware project type and installed tools.")
    parser.add_argument("--path", default=".", help="Path to firmware project root (default: .)")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        parser.error(f"Directory does not exist: {root}")

    ecosystems = detect_ecosystems(root)
    tools = {name: shutil.which(name) for name in TOOL_CANDIDATES if shutil.which(name)}
    elfs = find_elf_artifacts(root)

    payload = {
        "project_root": str(root),
        "ecosystems": ecosystems,
        "installed_tools": tools,
        "existing_elf_files": elfs,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Project root: {root}")
    if ecosystems:
        print("\nDetected ecosystems:")
        for item in ecosystems:
            print(f"  - {item['ecosystem']} (evidence: {item['evidence']})")
            if item.get("environments"):
                print(f"    envs: {', '.join(item['environments'])}")
            print(f"    build: {item['build_cmd']}")
            print(f"    flash: {item['flash_cmd']}")
    else:
        print("\nDetected ecosystems: none (check subdirectory or project layout)")

    print(f"\nInstalled embedded tools ({len(tools)} found):")
    for name, loc in sorted(tools.items()):
        print(f"  - {name}: {loc}")

    if elfs:
        print("\nExisting ELF artifacts:")
        for elf in elfs:
            print(f"  - {elf}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
