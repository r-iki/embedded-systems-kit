---
name: embedded-hardware-bringup
description: >-
  Guide first-time PCB/board bring-up, extract register maps and electrical specs
  from datasheets or CMSIS-SVD (.svd) / STM32CubeMX (.ioc) files, review
  schematics/pinouts, and validate MCU pin assignments for strapping, boot, ADC,
  debug, and voltage-level conflicts. Use when bringing up new hardware, assigning
  MCU pins, reading IC datasheets, inspecting MCU registers, or debugging initial
  board power/clock/bus connectivity.
---

# Embedded Hardware Bring-Up & Datasheet Integration

Use this workflow when bringing up a new board, reviewing a pinout/schematic, or translating an IC datasheet / CMSIS-SVD file into verified firmware configuration.

## Workflow

1. **Load ONLY the relevant MCU family reference (progressive disclosure)**
   - Quick cross-MCU index: [MCU Hardware Gotchas](./references/mcu-gotchas.md)
   - Load the specific family guide matching the user's target chip:
     - [ESP32 Family (ESP32, S3, C3, C6)](./references/mcu/esp32-family.md)
     - [STM32 Family (F1, F4, G4, L4, H7)](./references/mcu/stm32-family.md)
     - [RP2040 & RP2350 (Pico / Pico 2)](./references/mcu/rp2040-rp2350.md)
     - [Arduino / Classic AVR (ATmega328P/2560/32U4)](./references/mcu/arduino-avr.md)

2. **Query exact registers or `.ioc` pinouts instead of guessing**
   - When a CMSIS-SVD (`.svd`) file is available in the project or SDK, inspect exact base addresses, register offsets, and bitfield masks with [query_svd.py](./scripts/query_svd.py):
     ```bash
     python scripts/query_svd.py --svd path/to/chip.svd --peripheral I2C1 --register CR1
     ```
   - For STM32CubeMX projects, extract configured pins directly from `.ioc` and export to a pinmap JSON:
     ```bash
     python scripts/query_svd.py --ioc project.ioc --export-pinmap pinmap.json
     ```

3. **Validate electrical & pinout safety before powering or writing code**
   - Document pin assignments using [pinmap_template.json](./templates/pinmap_template.json) (or export from `.ioc` above).
   - Run [check_pin_conflicts.py](./scripts/check_pin_conflicts.py) to catch duplicate pins, ESP32/S3/C3/C6 strapping/flash/PSRAM/ADC2+WiFi hazards, STM32 SWD/JTAG/BOOT0/5V-ADC conflicts, RP2040/RP2350 ADC & Pico W conflicts, AVR analog-only pins, and voltage mismatches:
     ```bash
     python scripts/check_pin_conflicts.py --pinmap pinmap.json
     ```

4. **Extract verified specifications from IC datasheets**
   - Follow [Datasheet Extraction Guide](./references/datasheet-extraction.md) to capture supply/logic voltages, power-on reset timing, bus contracts (I2C/SPI/UART), `WHO_AM_I` register, bitfields, data scaling, and interrupt polarity.

5. **Execute staged board bring-up (never enable everything at once)**
   - Follow [Board Bring-Up Runbook](./references/bringup-runbook.md) and track progress in [bringup_checklist.md](./templates/bringup_checklist.md):
     1. Unpowered short check -> Current-limited power-up -> Verify every rail (`5V`, `3V3`, `1V8`, `VDDA`)
     2. Verify reset line & clock/oscillator startup
     3. Connect SWD/JTAG or USB-UART bootloader and read MCU chip ID
     4. Flash minimal blink + UART hello world (proves toolchain, clock tree, and console)
     5. Run bus discovery (I2C scan, SPI `WHO_AM_I` read) one peripheral at a time
     6. Validate actuators/high-power stages last with current limit enabled
