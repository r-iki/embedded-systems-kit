# Embedded Fault & Crash Triage Reference

## ARM Cortex-M HardFault Triage
Inspect these System Control Block (SCB) registers (`0xE000ED28`..`0xE000ED3C`):
- **`HFSR` (`0xE000ED2C`)**:
  - Bit 30 (`FORCED`): A configurable fault (MemManage, BusFault, UsageFault) escalated to HardFault -> inspect `CFSR`.
  - Bit 1 (`VECTTBL`): Bus fault on vector table read during exception entry.
- **`CFSR` (`0xE000ED28`)** splits into:
  - **MMFSR `[7:0]`**: `IACCVIOL` (fetch from XN region), `DACCVIOL` (data access violation / MPU), `MMARVALID` (fault address valid in `MMFAR` `0xE000ED34`).
  - **BFSR `[15:8]`**: `PRECISERR` (precise data bus error -> address in `BFAR` `0xE000ED38`), `IMPRECISERR` (buffered write fault -> temporarily disable write buffering via `ACTLR.DISDEFWBUF` to localize), `STKERR` (stacking failed -> **stack overflow**!).
  - **UFSR `[31:16]`**: `UNDEFINSTR` (corrupted function pointer / Thumb bit 0 missing), `INVSTATE` (invalid EPSR.T bit), `UNALIGNED` (unaligned access when `UNALIGN_TRP` set), `DIVBYZERO` (when `DIV_0_TRP` set).
- **Stacked exception frame** (pointed to by `MSP` or `PSP` depending on bit 2 of `EXC_RETURN` in `LR`):
  `[R0, R1, R2, R3, R12, LR, PC, xPSR]` at offsets `+0..+28`. Always resolve both `PC` and `LR` via `addr2line`.

## ESP32 / ESP-IDF Guru Meditation & Reset Triage
- **`LoadProhibited` / `StoreProhibited`**: Check `EXCVADDR`. Values `0x00000000`..`0x00000FFF` usually indicate a `NULL` pointer dereference with a struct field offset. Values like `0xA5A5A5A5` indicate use-after-free or uninitialized FreeRTOS stack fill pattern.
- **`Cache disabled but cached memory region accessed`**: An ISR (or function called from it) ran during SPI Flash write/erase without `IRAM_ATTR`, or read a `const` table stored in Flash instead of `DRAM_ATTR`.
- **`InstrFetchProhibited`**: Jump through corrupted/null function pointer or stack corruption overwriting return address.
- **Task Watchdog (`TWDT`)**: A task hogged a CPU core without yielding (`vTaskDelay` / blocking on queue/notify) for `CONFIG_ESP_TASK_WDT_TIMEOUT_S`. Check tight polling loops or high-priority tasks starving `IDLE0`/`IDLE1`.
- **Interrupt Watchdog (`IWDT`)**: Interrupts were disabled too long (`portENTER_CRITICAL`) or an ISR stalled/looped.
- **Brownout detector triggered**: Power supply voltage sag during Wi-Fi/BLE TX burst (check USB cable, 3.3 V regulator current rating >= 500 mA, bulk capacitance 100-470 uF near module).

## Stack Overflow Signatures
- Sudden corruption of adjacent globals or FreeRTOS TCBs right before a crash.
- `SP` value outside the task's allocated stack range or `MSP` below `_estack - _Min_Stack_Size`.
- Enable `configCHECK_FOR_STACK_OVERFLOW 2` and print `uxTaskGetStackHighWaterMark()` during peak load.
