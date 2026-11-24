# Peripheral Protocols Reference

## I2C
- **Addressing**: Always store and document the **7-bit address** (`0x08`..`0x77`). Note that STM32 HAL (`HAL_I2C_Master_Transmit`) expects `addr_7bit << 1`, whereas ESP-IDF, Arduino `Wire`, and Pico SDK take the unshifted 7-bit address.
- **Pull-ups**: Open-drain lines require external pull-ups (typically 4.7 kOhm at 100 kHz, 2.2 kOhm at 400 kHz on 3.3 V; adjust for bus capacitance). Internal MCU pull-ups (30-50 kOhm) are too weak for reliable fast-mode I2C.
- **Repeated START**: Use atomic `write_read` transactions for register reads so another master or sensor state machine cannot split the register-pointer write from the read.
- **Stuck-bus recovery**: If `SDA` is held low after an interrupted reset, temporarily configure `SCL`/`SDA` as open-drain GPIO, toggle `SCL` up to 9 pulses until `SDA` releases, generate a STOP condition, then re-initialize the I2C peripheral.
- **Multi-byte endianness**: Explicitly reconstruct values from raw byte arrays (`((uint16_t)buf[0] << 8) | buf[1]`) instead of casting `uint8_t*` to a struct.

## SPI
- **Mode & Bit Order**: Verify `CPOL` (clock idle polarity) and `CPHA` (sample edge) against the datasheet timing diagram (Modes 0..3) plus MSB/LSB-first order and max `SCLK` frequency.
- **Chip Select (`CS`)**: Manage `CS` atomically around the full transaction. Respect setup (`t_SU`), hold (`t_HD`), and inter-frame high time (`t_CSH`). Never share an SPI bus across tasks or ISRs without bus locking.
- **Half-duplex / Dummy bytes**: Send defined dummy bytes (`0x00` or `0xFF`, check datasheet) during read phases and verify whether the first received byte is status or garbage.
- **DMA**: Place TX/RX buffers in DMA-capable memory (not stack, not CCMRAM on STM32F4, use `MALLOC_CAP_DMA` or static DRAM on ESP32) and handle cache clean/invalidate on Cortex-M7 / ESP32-S3 PSRAM.

## UART
- **Framing & Overrun**: Always clear overrun (`ORE`), framing (`FE`), and noise (`NE`) flags in the error handler; on STM32 an uncleared `ORE` stalls subsequent RX interrupts.
- **Variable-length packets**: Prefer **DMA circular buffer + IDLE line interrupt** (STM32) or **UART hardware FIFO + event queue** (ESP-IDF) over byte-by-byte blocking reads.
- **RS-485 / Half-duplex**: Wait for Transmission Complete (`TC`), not just Transmit Buffer Empty (`TXE`), before de-asserting the `DE` driver-enable pin.

## GPIO, ADC, PWM & Timers
- **Input debouncing**: Never debounce buttons with `delay()` inside an ISR. Sample periodically (5-20 ms timer tick) using a shift-register or integrator counter.
- **Unused/output pins**: Set explicit pull-up/pull-down on floating inputs; set the initial output latch level before switching a pin to output mode to prevent startup glitches.
- **ADC**: Account for input impedance (increase sampling time for high-impedance dividers), reference voltage drift, and ESP32 ADC nonlinearity (use `esp_adc/adc_cali.h` rather than raw counts).
- **PWM / Timers**: Enable preload/shadow registers so duty-cycle updates take effect cleanly on the next period boundary without runt pulses.
