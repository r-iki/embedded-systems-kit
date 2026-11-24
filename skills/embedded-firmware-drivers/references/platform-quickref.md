# Multi-Platform Embedded C/C++ Quick Reference

| Concern | ESP32 (ESP-IDF v5+) | STM32 (CubeHAL / LL) | PlatformIO / Arduino | RP2040 (Pico SDK) |
| :--- | :--- | :--- | :--- | :--- |
| **Error handling** | `esp_err_t`, `ESP_RETURN_ON_ERROR` | `HAL_StatusTypeDef` (`HAL_OK`, `HAL_TIMEOUT`) | `bool` / `int` return codes | `int` / `PICO_ERROR_TIMEOUT` |
| **Tick / timebase** | `esp_timer_get_time()` (us), `xTaskGetTickCount()` | `HAL_GetTick()` (ms), DWT `CYCCNT` (cycles) | `millis()`, `micros()` | `time_us_64()`, `get_absolute_time()` |
| **Critical section** | `portMUX_TYPE` + `taskENTER_CRITICAL(&mux)` | Save `PRIMASK`, `__disable_irq()`, restore | `noInterrupts()` / `portENTER_CRITICAL` (ESP32) | `save_and_disable_interrupts()` / `spin_lock` |
| **I2C driver** | `driver/i2c_master.h` (v5.2+ new driver) | `HAL_I2C_Mem_Read/Write` (7-bit addr `<< 1`) | `Wire.beginTransmission` / `requestFrom` | `i2c_write_timeout_us` / `i2c_read_timeout_us` |
| **SPI driver** | `driver/spi_master.h` (`spi_device_polling_transmit` / `transmit`) | `HAL_SPI_TransmitReceive_DMA` | `SPI.beginTransaction(SPISettings(...))` | `spi_write_read_blocking` + DMA channels |
| **UART driver** | `driver/uart.h` + event queue | `HAL_UARTEx_ReceiveToIdle_DMA` | `HardwareSerial` + non-blocking `available()` | `uart_set_irq_enables` + ring buffer |
| **Logging** | `ESP_LOGI(TAG, ...)` (never in ISR; use `ESP_EARLY_LOG` only for panic) | SWO ITM / RTT (SEGGER) / DMA UART | `Serial.printf` (task context only) | `printf` over USB/UART stdio |
| **Flash const data** | `static const` (mapped via flash cache; `DRAM_ATTR` if needed in ISR) | `static const` (`.rodata` in Flash) | `const` (AVR needs `PROGMEM` + `pgm_read_*`) | `static const` (XIP Flash; `__not_in_flash_func` for RAM) |

## Cross-Platform Portability Tips
- Wrap timebase queries in a single function (`uint32_t hal_millis(void)`) so timeout logic never calls platform headers directly.
- Guard C headers with `#ifdef __cplusplus extern "C" { #endif` so C drivers link seamlessly into Arduino/ESP-IDF C++ projects.
- Avoid `HAL_Delay()` inside STM32 interrupts (it polls `uwTick`, which deadlocks if the ISR priority is equal to or higher than SysTick).
- On ESP-IDF v5+, prefer the new `driver/i2c_master.h` and `esp_adc/adc_oneshot.h` APIs over legacy `driver/i2c.h` and `driver/adc.h` unless the existing project already depends on legacy drivers.
