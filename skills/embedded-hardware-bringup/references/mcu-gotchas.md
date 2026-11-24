# MCU Hardware Gotchas Index

Use this quick table to spot top hazards immediately, then open the family-specific guide under `./references/mcu/` for deeper pitfalls (SDK v5 migrations, DMA/cache, flash stalls, timers).

| Family | Top 3 Hardware Gotchas | Detailed Guide |
| :--- | :--- | :--- |
| **ESP32 / S3 / C3 / C6** | 3.3 V only; strapping pins (`GPIO0/2/12/15` on ESP32, `GPIO45/46` on S3, `GPIO8/9` on C3/C6); ADC2 conflicts with Wi-Fi; internal Flash/PSRAM pins reserved | [esp32-family.md](./mcu/esp32-family.md) |
| **STM32 (F1/F4/G4/L4/H7)** | Keep `PA13`/`PA14` (SWD) & pull `BOOT0` low; enable RCC clock before register access; **H7 DTCM/D-Cache & F4 CCMRAM are NOT DMA-safe**; `FT` 5 V tolerance does not apply in ADC mode | [stm32-family.md](./mcu/stm32-family.md) |
| **RP2040 / RP2350** | 3.3 V only; Flash write pauses XIP on both cores (`flash_safe_execute` / `__not_in_flash_func`); Pico W reserves `GPIO23/24/25/29` for CYW43; ADC only on `GPIO26–29` (`40–47` on RP2350B) | [rp2040-rp2350.md](./mcu/rp2040-rp2350.md) |
| **Arduino / AVR (5 V)** | 5 V I/O damages 3.3 V sensors without level shifting; 2 KB SRAM needs `F()`/`PROGMEM`; `D0`/`D1` block USB upload; Nano `A6`/`A7` are analog-input-only; 16/32-bit ISR vars need `ATOMIC_BLOCK` | [arduino-avr.md](./mcu/arduino-avr.md) |
