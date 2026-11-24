# Arduino / Classic AVR Reference (ATmega328P, ATmega2560, ATmega32U4)

Load this reference when working with classic 8-bit AVR Arduino boards (Uno, Nano, Mega, Leonardo/Pro Micro) via PlatformIO or Arduino CLI.

## Top Hardware & Firmware Pitfalls
1. **5 V Logic vs 3.3 V Peripherals**:
   - Uno, Nano, and Mega run at **5 V I/O**. Connecting 5 V TX/MOSI/SCLK/SDA directly to a 3.3 V sensor, SD card, LoRa module, or ESP module can permanently damage the 3.3 V IC. Use a bidirectional level shifter (I2C) or resistive divider / 74AHCT/74LVC buffer (SPI/UART).
2. **Tight SRAM (2 KB on ATmega328P) & `String` Heap Fragmentation**:
   - Every string literal (`Serial.println("Hello")`) consumes SRAM unless wrapped in `F("Hello")` or stored with `PROGMEM` and read via `pgm_read_byte()` / `pgm_read_word()`.
   - Avoid Arduino `String` concatenation in `loop()`; use fixed `char buf[64]` with `snprintf()`.
3. **Hardware Timer Conflicts on ATmega328P**:
   - `Timer0`: Drives `millis()`, `micros()`, `delay()`, and PWM on `D5`/`D6`. Modifying Timer0 prescaler breaks all timing functions!
   - `Timer1`: Used by `Servo` library (disables PWM on `D9`/`D10`).
   - `Timer2`: Used by `tone()` (disables PWM on `D3`/`D11`).
4. **Pin-Specific Gotchas**:
   - `D0` (`RX`) & `D1` (`TX`) on Uno/Nano share the USB-UART programming bus — external devices attached here block sketch upload.
   - `A6` & `A7` on Arduino Nano (TQFP-32 ATmega328P) are **analog input ONLY** — `digitalRead()`/`digitalWrite()` do not work on them!
   - Pin `D10` (`SS`) must stay configured as `OUTPUT` when AVR operates as an SPI Master; if left as `INPUT` and pulled LOW, hardware silently drops SPI into Slave mode.
5. **8-Bit Atomicity**:
   - On 8-bit AVR, even a `uint16_t` or `uint32_t` shared with an ISR is **NOT atomic** (takes 2–4 instructions to read/write). Always wrap reads/writes in `<util/atomic.h>` (`ATOMIC_BLOCK(ATOMIC_RESTORESTATE)`).
6. **`SoftwareSerial` Limitations**:
   - Half-duplex, disables interrupts during byte TX/RX, unreliable above 38400 baud, and breaks timing-sensitive libraries (NeoPixel/Servo). Prefer hardware UARTs or AltSoftSerial where possible.
