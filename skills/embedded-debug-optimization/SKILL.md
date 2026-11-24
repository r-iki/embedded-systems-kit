---
name: embedded-debug-optimization
description: >-
  Diagnose embedded C/C++ crashes, ARM Cortex-M HardFaults, ESP32 Guru Meditation
  panics, watchdog resets, stack overflows, memory leaks, and Flash/RAM or latency
  bottlenecks. Use when decoding backtraces/dumps, inspecting linker maps,
  profiling stack/RAM usage, or running non-interactive GDB/OpenOCD commands.
---

# Embedded Debugging & Resource Optimization

Follow this systematic triage workflow for firmware crashes, watchdog resets, and Flash/RAM/timing optimization.

## Workflow

1. **Capture exact failure evidence**
   - Obtain the full crash dump, reset reason (`esp_reset_reason()`, STM32 `RCC->CSR` flags), register dump (`PC`, `LR`, `SP`, `CFSR`, `HFSR`, `EXCVADDR`), and the exact matching `.elf` binary built from the same commit.
   - If live hardware is connected, capture logs safely using `serial_capture.py` (never hang on an interactive monitor).

2. **Decode crash addresses to source lines**
   - Run [decode_crash.py](./scripts/decode_crash.py) against the crash log and `.elf` file:
     ```bash
     python scripts/decode_crash.py --elf path/to/firmware.elf --log crash.txt
     ```
   - Alternatively pass raw hex addresses via `--addrs 0x400d1234 0x08004abc`.
   - Consult [Fault Triage Reference](./references/fault-triage.md) to classify the root cause (null/unaligned pointer, stack overflow, bus fault, cache-disabled flash access in ISR, watchdog starvation).

3. **Inspect target state via non-interactive debugger (if SWD/JTAG attached)**
   - Consult [GDB & OpenOCD Cheat Sheet](./references/gdb-openocd-cheatsheet.md) for `--batch` GDB commands that dump `CFSR`/`HFSR`, task backtraces, and memory without entering an interactive prompt.

4. **Optimize Flash, RAM, stack, and timing**
   - Read [Memory & Footprint Optimization](./references/memory-optimization.md) for linker section analysis (`.text`, `.rodata`, `.data`, `.bss`), compiler `-fstack-usage` inspection, eliminating accidental `printf` float/heap bloat, and measuring ISR/loop latency with DWT `CYCCNT` or `esp_timer_get_time()`.
   - Re-measure before and after with `analyze_size.py` so every optimization is verified quantitatively.

5. **Verify fix under stress**
   - Enable runtime guards (`configCHECK_FOR_STACK_OVERFLOW = 2`, `uxTaskGetStackHighWaterMark()`, brownout/watchdog logging) and confirm zero resets across repeated exercise cycles.
