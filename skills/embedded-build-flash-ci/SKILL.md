---
name: embedded-build-flash-ci
description: >-
  Automate embedded C/C++ firmware builds, binary Flash/RAM size analysis, flashing,
  bounded serial log capture, and static analysis (cppcheck, clang-tidy) for
  PlatformIO, ESP-IDF, CMake/ARM GCC, STM32Cube, RP2040 Pico SDK, and Arduino CLI.
  Use when building, flashing, monitoring UART output, checking binary footprint,
  or setting up firmware CI.
---

# Embedded Build, Flash, Serial Capture & CI

Use this workflow to build, analyze, flash, and verify embedded firmware reliably without hanging on interactive tools.

## Workflow

1. **Detect project ecosystem and available toolchains**
   - Run [detect_project.py](./scripts/detect_project.py) in the project root:
     ```bash
     python scripts/detect_project.py --path .
     ```
   - Review the detected framework (`platformio`, `esp-idf`, `cmake-arm`, `pico-sdk`, `arduino-cli`, `makefile`) and available CLI binaries before invoking any build command.
   - Consult [Toolchains CLI Reference](./references/toolchains-cli.md) for exact build/flash flags per ecosystem.

2. **Build firmware cleanly**
   - Run the ecosystem build command (e.g., `pio run`, `idf.py build`, `cmake --build build`).
   - Treat compiler warnings seriously (`-Wall -Wextra`). Fix all warnings in newly written code before flashing.

3. **Analyze Flash & RAM footprint**
   - Run [analyze_size.py](./scripts/analyze_size.py) on the generated `.elf` (and optionally `.map`) file:
     ```bash
     python scripts/analyze_size.py --elf path/to/firmware.elf --top 15
     ```
   - Flag sudden RAM (`.data` + `.bss`) or Flash (`.text` + `.rodata`) spikes, accidental `printf` float pulls, or oversized static buffers.

4. **Run static analysis**
   - Run [run_static_analysis.py](./scripts/run_static_analysis.py) on modified source directories:
     ```bash
     python scripts/run_static_analysis.py --path src
     ```
   - See [Static Analysis & MISRA Reference](./references/static-analysis-misra.md) for recommended compiler warning flags and `cppcheck`/`clang-tidy` suppressions.

5. **Flash and capture serial verification output (never hang)**
   - Flash the target using the detected tool (`pio run -t upload`, `idf.py -p <PORT> flash`, `openocd`, `picotool`).
   - **Never run an unbounded interactive monitor** (`pio device monitor`, `idf.py monitor`, `minicom`). Always use [serial_capture.py](./scripts/serial_capture.py) with an explicit timeout and optional stop regex:
     ```bash
     python scripts/serial_capture.py --port COM5 --baud 115200 --timeout 10 --stop-pattern "READY|Guru Meditation|HardFault"
     ```
   - Verify boot banner, expected self-test messages, and absence of watchdog/panic resets.
