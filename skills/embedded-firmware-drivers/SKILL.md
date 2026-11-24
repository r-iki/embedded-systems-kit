---
name: embedded-firmware-drivers
description: >-
  Write, refactor, and review multi-platform embedded C/C++ firmware and peripheral
  drivers (GPIO, I2C, SPI, UART, ADC, PWM, Timer, DMA, ISR) across ESP32/ESP-IDF,
  STM32 HAL/LL, PlatformIO/Arduino, and RP2040 Pico SDK. Use when implementing
  sensor/actuator drivers, HAL abstraction layers, interrupt handlers, DMA transfers,
  or lock-free ring buffers.
---

# Embedded Firmware & Peripheral Drivers

Follow this workflow when creating or refactoring C/C++ embedded drivers and peripheral code.

## Workflow

1. **Inspect target & SDK first**
   - Identify the MCU family, framework, and C/C++ standard from build files (`platformio.ini`, `CMakeLists.txt`, `sdkconfig`, `*.ioc`, `Makefile`).
   - Check existing HAL/board headers, CMSIS-SVD (`.svd`) register maps (via `query_svd.py` in `embedded-hardware-bringup`), or datasheet excerpts for pin definitions, bus handles, clock rates, and error conventions before writing code. Never invent register addresses or pin numbers.
   - Load [Platform Quick Reference](./references/platform-quickref.md) when bridging idioms across ESP-IDF, STM32 HAL/LL, PlatformIO/Arduino, or RP2040.

2. **Separate driver logic from hardware transport (HAL decoupling)**
   - Design device drivers (sensors, displays, EEPROMs, motor controllers) around an injected bus interface (`read_reg`, `write_reg`, `delay_ms`, `ctx` pointer) so the core driver compiles cleanly for unit tests and ports across MCUs.
   - Start from [driver_template.h](./templates/driver_template.h) and [driver_template.c](./templates/driver_template.c) for new C99/C11 device drivers.

3. **Apply protocol-specific reliability guardrails**
   - Read [Peripheral Protocols Reference](./references/peripheral-protocols.md) for I2C (7-bit addressing, pull-ups, stuck-bus recovery), SPI (CPOL/CPHA mode, CS timing, DMA alignment), UART (framing/overrun errors, idle-line DMA), ADC/PWM calibration, and GPIO debouncing.
   - Every bus transaction and register poll MUST include an explicit timeout and propagate a typed status enum (`*_ok`, `*_err_timeout`, `*_err_nack`, `*_err_invalid_arg`).

4. **Design safe ISRs and DMA pipelines**
   - Read [ISR & DMA Patterns](./references/isr-dma-patterns.md) before writing interrupt callbacks or DMA transfers.
   - Keep ISRs short, non-blocking, and allocation-free. Transfer streams between ISR and main/task context using [ring_buffer.h](./templates/ring_buffer.h) or RTOS task notifications.
   - Check tick wraparound safety using unsigned subtraction: `(uint32_t)(now - start) >= timeout_ms`.

5. **Verify before finishing**
   - Confirm zero compiler warnings (`-Wall -Wextra`) and check RAM/Flash delta via the `embedded-build-flash-ci` skill.
   - Verify error paths (NACK, timeout, null pointer, uninitialized handle) and ensure no `const` tables accidentally land in RAM.
