# Embedded Systems Safety & Engineering Rules

Apply these rules whenever writing, reviewing, building, or debugging embedded C/C++ firmware or advising on hardware connections.

## 1. Hardware & Electrical Safety First
- **Verify logic voltage levels** (1.8 V, 3.3 V, 5 V) and pin current limits before recommending wiring or direct GPIO connections. Warn immediately on 3.3 V vs 5 V mismatches unless the datasheet explicitly confirms 5 V tolerance.
- **Check strapping, boot, and debug pins** (e.g., ESP32 GPIO0/2/12/15, STM32 BOOT0/SWDIO/SWCLK, RP2040 RUN/SWD) before assigning peripherals.

## 2. Zero Hallucination on Hardware Specs
- **Never guess register addresses, bitfields, alternate-function mappings, I2C addresses, or clock trees.** Always read the project's SDK headers, board definition, linker script, `sdkconfig`/`.ioc`, or ask the user for the relevant datasheet excerpt.
- If a datasheet value is unverified, explicitly mark it as `// TODO: verify against datasheet Table X`.

## 3. Deterministic Firmware & Memory Safety
- **Fixed-width types**: Use `<stdint.h>` (`uint8_t`, `uint16_t`, `uint32_t`, `int32_t`) and `<stdbool.h>` for hardware interfaces, protocol packets, and register math. Avoid bare `int`/`long` across boundaries.
- **No blocking in ISRs**: Never call blocking functions, dynamic allocation (`malloc`/`free`), `printf`/logging, or non-ISR RTOS APIs inside an Interrupt Service Routine. Keep ISRs minimal: clear flag, capture data or notify a task (`*FromISR`), and exit.
- **Shared state synchronization**: Mark hardware registers and ISR-shared variables `volatile`, and protect multi-byte or read-modify-write updates with atomic operations or critical sections.
- **Bounded loops and timeouts**: Every hardware polling loop and bus transaction (I2C, SPI, UART, ADC) MUST have an explicit timeout and return a typed error code. Never write unbounded `while (REG & FLAG);`.
- **Avoid runtime heap fragmentation**: Prefer static or pool allocation over `malloc`/`new` after startup in real-time loops.

## 4. Verification Discipline
- **Never hang on interactive serial monitors**: Always capture serial logs with an explicit timeout or stop condition.
- **Check footprint**: After firmware changes, verify clean compilation (ideally with `-Wall -Wextra`) and inspect Flash/RAM usage before declaring success.
