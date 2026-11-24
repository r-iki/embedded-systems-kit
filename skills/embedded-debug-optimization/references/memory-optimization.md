# Embedded Memory, Stack & Timing Optimization

## Flash & RAM Section Anatomy
- **Flash usage** = `.text` (code) + `.rodata` (constants/strings) + `.data` (initial values copied to RAM at startup).
- **RAM usage** = `.data` (initialized globals) + `.bss` (zero-initialized globals) + heap + stacks.

## High-Impact Footprint Optimizations
1. **Enable dead-code stripping**: Compile with `-ffunction-sections -fdata-sections` and link with `-Wl,--gc-sections`.
2. **Eliminate hidden `printf` bloat**:
   - On ARM newlib, switch to `--specs=nano.specs` and avoid `-u _printf_float` unless floating-point formatting is strictly needed (saves ~10-25 KB Flash). Format fixed-point integers (`val / 100`, `abs(val % 100)`) instead.
3. **Move constants out of RAM**:
   - Declare lookup tables, pin configs, and format strings `static const` (and `PROGMEM` on Harvard AVR MCUs).
4. **Shrink structs via field ordering (avoid blind `__packed`)**:
   - Order struct members from largest alignment to smallest (`uint64_t` -> `uint32_t` -> `uint16_t` -> `uint8_t`) to eliminate padding without incurring slow/fault-prone unaligned accesses.
5. **Size stacks with evidence**:
   - Compile with `-fstack-usage` to inspect worst-case frame size per function.
   - Move large temporary buffers (e.g., `uint8_t frame[512]`) out of task stacks into `static` module storage (if single-owner) or dedicated pools.
6. **Avoid accidental C++ overhead**:
   - Use `-fno-exceptions -fno-rtti` on bare-metal/RTOS C++ targets; avoid `std::iostream` and heavy `std::function` captures.

## Latency & Jitter Measurement
- **ARM Cortex-M3/M4/M7/M33**: Use the DWT cycle counter (`DWT->CYCCNT` after enabling `CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk` and `DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk`) for single-cycle accuracy.
- **ESP32**: Use `esp_timer_get_time()` (1 us resolution) or `esp_cpu_get_cycle_count()`.
- **Hardware GPIO toggle**: Toggle an unused debug pin high at ISR/function entry and low at exit to measure true jitter and interrupt latency on a logic analyzer or oscilloscope with near-zero overhead.
