# Staged Hardware Bring-Up Runbook

Bring up new hardware incrementally so every failure isolates to one subsystem.

## Stage 0: Unpowered Inspection
- Visual check: solder bridges, reversed diodes/LEDs/electrolytics, pin-1 IC alignment, missing decoupling caps.
- Multimeter continuity/resistance check across every power rail to `GND` (a dead short < 10 Ohm means DO NOT apply power).

## Stage 1: Current-Limited Power-Up
- Set bench supply current limit conservatively (e.g., 100-200 mA for an MCU logic board without motors/heaters).
- Apply power and immediately monitor current draw and thermal hotspots.
- Measure all power rails (`VBUS`, `5V`, `3V3`, `1V8`, `VDDA`/`VREF+`) with a multimeter (ripple check with scope if available).
- Confirm `NRST` / `EN` sits high at logic `VDD` after power-on reset RC delay.

## Stage 2: Debug Interface & Bootloader Handshake
- **STM32 / Cortex-M**: Connect `SWDIO`, `SWCLK`, `GND`, `VREF` (and `NRST` if low-power/misconfigured pins block attach). Read core ID via OpenOCD or `STM32_Programmer_CLI`.
- **ESP32**: Confirm UART `TX/RX` crossover, `GND`, and boot strapping (`GPIO0` low during reset for ROM bootloader). Run `esptool.py chip_id`.
- **RP2040**: Hold `BOOTSEL` while pulsing `RUN` low -> verify USB mass-storage device enumerates, or attach SWD probe.

## Stage 3: Minimal Proof-of-Life Firmware
- Flash a stripped-down firmware that ONLY initializes clocks, toggles one LED at 1 Hz (verifies clock tree/PLL multiplier is not off by 2x/8x!), and prints a banner over UART/RTT.
- If the blink rate is wrong, fix HSE crystal value / PLL config before touching any communication bus.

## Stage 4: Peripheral & Sensor Smoke Tests (One Bus at a Time)
- **I2C**: Run a 7-bit address scan (`0x08`..`0x77`). If nothing ACKs: check `SDA`/`SCL` pull-up voltage, swapped lines, `ADDR` strap pin, and sensor `ENABLE`/`RESET` pins.
- **SPI**: Read the IC's `WHO_AM_I` / JEDEC ID register at a conservative clock (<= 1 MHz) first, then verify `CS`, `MOSI`, `MISO`, `SCLK` polarity on a logic analyzer before raising frequency.
- **Analog / ADC**: Measure known DC reference voltage (e.g., `GND`, `VREF/2`) before trusting sensor conversions.

## Stage 5: High-Power / Actuator Bring-Up
- Enable motor drivers, relays, MOSFET loads, and radio TX bursts last, monitoring rail droop on an oscilloscope to confirm bulk capacitance prevents MCU brownout resets.
