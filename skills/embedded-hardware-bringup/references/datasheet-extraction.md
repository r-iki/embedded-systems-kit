# Datasheet Extraction Guide for Firmware Engineers

When reading an IC or sensor datasheet to write a driver or review a schematic, extract these 7 items verbatim into a compact spec block before writing code:

1. **Supply & Logic Levels**
   - Operating `V_DD` / `V_DDIO` min/typ/max
   - Input high/low thresholds (`V_IH`, `V_IL`) and whether I/O pins are 5 V tolerant
   - Quiescent / shutdown / active peak current

2. **Power-On & Reset Sequence**
   - Power-up ramp requirements & wait time before first bus transaction (`t_POR` / `t_START`)
   - Reset pin polarity (`RESET_N` active-low vs active-high) and minimum pulse width

3. **Communication Bus Contract**
   - **I2C**: 7-bit address (and how `ADDR`/`SA0` pins modify LSBs), max SCL rate (100 kHz / 400 kHz / 1 MHz), clock stretching support, auto-increment bit (e.g., MSB bit 7 on some ST sensors)
   - **SPI**: Supported mode (`CPOL`, `CPHA`), read/write bit convention (bit 7 = 1 for read?), dummy byte count, max `SCLK`, `CS` setup/hold times
   - **UART**: Default baud, parity/stop bits, frame delimiter, CRC polynomial

4. **Identity / Smoke-Test Register**
   - `WHO_AM_I` / `CHIP_ID` / `PART_ID` register address and exact expected reset value

5. **Control & Status Registers**
   - Exact register addresses, bit positions, reset defaults, and read/write/write-1-to-clear (`W1C`) semantics
   - Note reserved bits that must be preserved via read-modify-write (`REG = (REG & ~MASK) | VAL`)

6. **Data Format & Scaling**
   - Byte order (big-endian vs little-endian), bit width (12/14/16/24-bit), left/right alignment, two's complement sign extension, and exact LSB-to-physical-unit conversion formula (prefer integer/fixed-point arithmetic where practical)

7. **Interrupt & Ready Signals**
   - `DRDY`/`INT` polarity (active-high vs active-low), output type (push-pull vs open-drain needing pull-up), latched vs pulsed behavior, and which register read clears the interrupt
