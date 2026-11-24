# Embedded Systems Kit (`embedded-systems-kit`)

A modular multi-skill AI agent plugin for **multi-platform C/C++ embedded systems development** (ESP32 / ESP-IDF, STM32 / ARM Cortex-M, PlatformIO / Arduino, RP2040 / Pico SDK).

Built natively for **Antigravity Plugins** and fully portable with the open **Agent Skills (`SKILL.md`)** specification (Claude Code, Cursor, Codex, etc.).

---

## Included Components

| Type | Name | Purpose |
| :--- | :--- | :--- |
| **Rule** | `rules/AGENTS.md` | Always-on electrical safety, zero-hallucination register/pinout, ISR safety, and deterministic memory guardrails |
| **Agent** | `agents/firmware-reviewer.md` | Read-only firmware auditor for ISR safety, concurrency, timeouts, stack/RAM hazards, and bitwise bugs |
| **Skill 1** | `embedded-firmware-drivers` | HAL-agnostic C/C++ driver design, GPIO/I2C/SPI/UART/DMA/ISR patterns, lock-free ring buffers, and platform idioms |
| **Skill 2** | `embedded-build-flash-ci` | Auto-detecting build systems (PlatformIO, ESP-IDF, CMake/ARM, Pico), Flash/RAM size analysis, non-hanging serial capture, and static analysis |
| **Skill 3** | `embedded-debug-optimization` | Cortex-M HardFault & ESP32 Guru Meditation triage, `addr2line` crash decoding, linker map optimization, and non-interactive GDB/OpenOCD |
| **Skill 4** | `embedded-rtos-lowpower` | FreeRTOS static allocation & task architecture, deterministic table-driven FSMs, sleep modes, and battery power budget calculator |
| **Skill 5** | `embedded-hardware-bringup` | Staged board bring-up runbook, datasheet extraction guide, MCU hardware gotchas, and automated pin conflict validator |

---

## Helper Scripts (Python 3, Cross-Platform)

All helper scripts are standard-library-first (optional `pyserial` only for live serial capture) and runnable from Windows PowerShell, Linux, or macOS:

- `skills/embedded-build-flash-ci/scripts/detect_project.py` — Detects embedded framework/build system and installed toolchains.
- `skills/embedded-build-flash-ci/scripts/analyze_size.py` — Breaks down `.elf`/`.map` Flash & RAM usage and highlights largest symbols.
- `skills/embedded-build-flash-ci/scripts/serial_capture.py` — Non-interactive serial capture with hard timeout, stop regex, and crash detection.
- `skills/embedded-build-flash-ci/scripts/run_static_analysis.py` — Runs `cppcheck` / `clang-tidy` with embedded C/C++ presets.
- `skills/embedded-debug-optimization/scripts/decode_crash.py` — Decodes ESP32 backtraces and ARM Cortex-M PC/LR dumps via `addr2line`.
- `skills/embedded-rtos-lowpower/scripts/power_budget_calc.py` — Calculates average current draw and battery life from multi-state duty cycles.
- `skills/embedded-hardware-bringup/scripts/check_pin_conflicts.py` — Checks a JSON pin map for duplicates, ESP32/S3/C3/C6 strapping/flash/PSRAM/ADC2+WiFi conflicts, STM32 SWD/JTAG/BOOT0/5V-ADC conflicts, RP2040/RP2350 Pico W & ADC rules, AVR analog-only pins, and logic-voltage mismatches.
- `skills/embedded-hardware-bringup/scripts/query_svd.py` — Queries exact register addresses & bitfield masks from CMSIS-SVD (`.svd`) XML files and extracts pinmaps directly from STM32CubeMX (`.ioc`) project files.

### Per-MCU Family References (Loaded On-Demand)
Under `skills/embedded-hardware-bringup/references/mcu/`:
- `esp32-family.md` (ESP32, S3, C3, C6 + ESP-IDF v5 migrations)
- `stm32-family.md` (F1, F4, G4, L4, H7 + DMA/D-Cache/DTCM & CubeMX safety)
- `rp2040-rp2350.md` (Pico / Pico 2 + XIP flash stalls, dual-core sync, PIO)
- `arduino-avr.md` (ATmega328P/2560/32U4 + 5 V level shifting, PROGMEM, timer conflicts)

---

## Installation

### Antigravity (Global — Available in All Projects)
Copy this folder to your Antigravity global plugins directory:
- **Windows:** `C:\Users\<USER>\.gemini\config\plugins\embedded-systems-kit`
- **macOS / Linux:** `~/.gemini/config/plugins/embedded-systems-kit`

### Antigravity (Workspace-Only)
Copy into `.agents/plugins/embedded-systems-kit` at the root of your firmware repository.

### Portable Agent Skills (Claude Code / Cursor / Codex / Antigravity)
Install directly from GitHub with the open Agent Skills CLI:

```bash
npx skills add r-iki/embedded-systems-kit
```

Or copy the subdirectories inside `skills/` directly into your tool's skills folder (e.g., `.agents/skills/`, `.claude/skills/`, or `.cursor/skills/`), and optionally copy `rules/AGENTS.md` into your project's `AGENTS.md` / `CLAUDE.md`.

---

## Validation & Self-Test

Run the built-in validator and unit test suite:

```bash
python tests/validate_plugin.py
```

This checks `plugin.json` schema compliance, every `SKILL.md` frontmatter and relative link, all Python helper scripts, and C/C++ template syntax (when `gcc` or `clang` is installed).
