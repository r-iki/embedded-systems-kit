# ESP32 Family Engineering Reference (ESP32, S3, C3, C6)

Load this reference when designing firmware or hardware around Espressif ESP32-series MCUs with ESP-IDF v5+ or PlatformIO/Arduino.

## Variant Comparison & Silicon Traps

| Feature / Trap | ESP32 (Classic) | ESP32-S3 | ESP32-C3 (RISC-V) | ESP32-C6 (RISC-V) |
| :--- | :--- | :--- | :--- | :--- |
| **CPU** | Dual Xtensa LX6 | Dual Xtensa LX7 (SIMD) | Single RV32IMC | Single HP + LP RV32IMAC |
| **Strapping pins** | `GPIO0, 2, 12, 15` | `GPIO0, 3, 45, 46` | `GPIO2, 8, 9` | `GPIO4, 5, 8, 9, 15` |
| **Internal Flash / PSRAM reserved** | `GPIO6–11` (always reserved); `GPIO16–17` if PSRAM | `GPIO26–32` (SPI Flash); `GPIO33–37` if Octal Flash/PSRAM | `GPIO12–17` (SPI Flash on modules) | `GPIO24–30` (internal SPI Flash) |
| **Input-only (no output, no pull)** | `GPIO34, 35, 36, 39` | None | None | None |
| **Native USB Serial/JTAG** | None (external UART bridge) | `GPIO19 (D-), GPIO20 (D+)` | `GPIO18 (D-), GPIO19 (D+)` | `GPIO12 (D-), GPIO13 (D+)` |
| **ADC + Wi-Fi conflict** | `ADC2` unusable while Wi-Fi active (`ADC1 = GPIO32–39`) | `ADC2` (`GPIO11–20`) conflicts with Wi-Fi (`ADC1 = GPIO1–10`) | `ADC2` (`GPIO5`) conflicts (`ADC1 = GPIO0–4`) | `ADC1 = GPIO0–6` (no ADC2) |
| **5 V tolerance** | **No (3.3 V max)** | **No (3.3 V max)** | **No (3.3 V max)** | **No (3.3 V max)** |

## Critical Boot & Strapping Pitfalls
- **ESP32 `GPIO12` (MTDI)**: Pull-up at boot switches internal flash VDD to 1.8 V -> endless boot loop on 3.3 V flash modules unless VDD_SDIO eFuse is burned.
- **ESP32-S3 `GPIO45`**: Controls VDD_SPI voltage (similar to classic GPIO12); avoid external pull-ups. `GPIO46` is input-only strapping during boot.
- **ESP32-C3 / C6 `GPIO8` & `GPIO9`**: `GPIO9` pulled LOW enters ROM download mode; `GPIO8` must be HIGH during download boot.

## ESP-IDF v5+ Breaking API Migrations (Avoid Legacy APIs)
- **I2C**: Use `driver/i2c_master.h` (`i2c_new_master_bus`, `i2c_master_bus_add_device`, `i2c_master_transmit_receive`) — do **not** mix with legacy `driver/i2c.h` in the same binary (runtime abort).
- **ADC**: Use `esp_adc/adc_oneshot.h` or `esp_adc/adc_continuous.h` + `esp_adc/adc_cali.h` instead of legacy `driver/adc.h`.
- **LED / PWM / RMT / PCNT**: Use new `driver/rmt_tx.h`, `driver/pulse_cnt.h`, `driver/gptimer.h` instead of legacy `driver/timer.h` / `driver/rmt.h`.
- **Task stack units**: In ESP-IDF FreeRTOS, `xTaskCreate(..., usStackDepth, ...)` takes **bytes** (not 32-bit words like upstream STM32 FreeRTOS!).

## Memory, IRAM, PSRAM & Flash Safety
- **Flash cache disable crash**: Writing NVS/SPIFFS/LittleFS/OTA pauses Flash cache. Any ISR registered with `ESP_INTR_FLAG_IRAM` and every function/const table it touches MUST be marked `IRAM_ATTR` / `DRAM_ATTR`.
- **DMA memory**: Allocate SPI/I2S/LCD DMA buffers with `heap_caps_malloc(len, MALLOC_CAP_DMA)` (or static internal DRAM), never on task stack or unaligned PSRAM without cache sync.
- **Brownout during Wi-Fi/BLE TX**: Peak TX bursts draw 300–500 mA. Ensure 3.3 V regulator is rated >= 600 mA with >= 100 uF bulk decoupling near the module.
